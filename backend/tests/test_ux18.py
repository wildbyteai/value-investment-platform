"""UX18 review regressions: all writes use original disposable test fixtures."""
import copy
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from app.models.company import Company, Security
from app.models.judgment import JudgmentRevision, JudgmentSlot
from app.models.runtime import ItemRevision, ResearchRun
from app.models.intake import InformationItem, SourceRegistry
from app.domains.companies.scoring_service import config, resolve_template, apply_patches, score_company
from app.domains.strategy.strategy_service import gates
from app.domains.news.item_history import observe
from app.domains.platform.transactions import canonical, digest
from app.domains.companies.decision_service import human_override
from test_remediation import prepared, headers, Session
from test_real_data import real_mode


def author_body(ids,revision):
    now=datetime.now(timezone.utc)
    return {'company_id':ids['company'],'dimension':'business_model','rubric_ref':'business-model-v1',
        'criterion':'repeat_demand','grade':2,'confidence':'0.8','reason':'原创夹具支持这一项，不能冒充真实投资判断',
        'period_start':now.date().isoformat(),'period_end':(now+timedelta(days=30)).date().isoformat(),
        'effective_from':(now-timedelta(minutes=1)).isoformat(),'valid_until':(now+timedelta(days=30)).isoformat(),
        'evidence':[{'source_revision_id':revision.id,'hash':revision.content_hash,'start':0,'end':6,'quote':'原创测试文本','relation':'supports'}]}


def test_author_create_read_score_run_immutable_and_idempotent(real_mode):
    c,ws,_,ids=real_mode
    with Session() as db:body=author_body(ids,db.get(ItemRevision,ids['revision']))
    h={**headers(ws),'Idempotency-Key':'ux18-author-create'}
    r=c.post('/api/judgments',headers=h,json=body);assert r.status_code==201,r.text
    one=r.json();assert c.post('/api/judgments',headers=h,json=body).json()['id']==one['id']
    row=c.get('/api/judgments',headers=headers(ws)).json()[0]
    assert row['effective']['rubric_ref']=='business-model-v1' and row['effective']['period_start']==body['period_start']
    score=c.get('/api/companies/'+ids['company']+'/score',headers=headers(ws)).json()
    assert score['dimensions']['business_model']['criteria'][0]['grade']==2
    assert score['dimensions']['business_model']['score'] is None # one criterion is not full coverage
    assert score['dimensions']['business_model']['criteria'][0]['status']=='valid'
    assert '有原文定位的商业模式、治理、成长判断' not in score['missing_data']
    old=c.post('/api/research/runs',headers={**headers(ws),'Idempotency-Key':'ux18-before-replace'}).json()
    replace=c.post('/api/judgments/'+one['slot_key']+'/override',headers={**headers(ws),'If-Match-Generation':'1'},json={'value':{'grade':1,'reason':'更新的原创测试判断'}})
    assert replace.status_code==200
    current=c.get('/api/companies/'+ids['company']+'/score',headers=headers(ws)).json()
    assert current['dimensions']['business_model']['criteria'][0]['grade']==1
    saved=c.get('/api/research/runs/'+old['id'],headers=headers(ws)).json()
    assert saved['manifest_hash']==old['manifest_hash'] and saved['result']==old['result']
    assert c.post('/api/judgments',headers={**h,'Idempotency-Key':'ux18-duplicate'},json=body).status_code==409
    assert c.post('/api/judgments',headers=h,json={**body,'grade':3}).status_code==409


def test_author_rejects_empty_forged_expired_wrong_scope_and_permission(real_mode):
    c,ws,other,ids=real_mode
    with Session() as db:body=author_body(ids,db.get(ItemRevision,ids['revision']))
    h={**headers(ws),'Idempotency-Key':'ux18-author-invalid'}
    for key,value in [('grade',''),('grade',False),('grade',5),('rubric_ref','unknown'),('criterion','other'),('reason','  '),('confidence','NaN')]:
        assert c.post('/api/judgments',headers=h,json={**body,key:value}).status_code==422
    for change in [{'hash':'wrong'},{'quote':'不在原文'},{'end':99},{'source_revision_id':'absent'},{'relation':'contradicts'}]:
        assert c.post('/api/judgments',headers=h,json={**body,'evidence':[{**body['evidence'][0],**change}]}).status_code==422
    expired={**body,'valid_until':(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()}
    assert c.post('/api/judgments',headers=h,json=expired).status_code==422
    assert c.post('/api/judgments',headers={**headers(ws,'viewer@demo'),'Idempotency-Key':'denied'},json=body).status_code==403
    assert c.post('/api/judgments',headers={**headers(other),'Idempotency-Key':'wrong-workspace'},json=body).status_code==404
    with Session() as db:
        source=db.get(SourceRegistry,ids['source']);policy=json.loads(source.policy_json);policy['revoked']=True;source.policy_json=canonical(policy);db.commit()
    assert c.post('/api/judgments',headers=h,json=body).status_code==404


def test_rubric_and_period_identity_and_expiry(prepared):
    _,ws,_=prepared
    with Session() as db:
        company=db.get(Company,'00000000-0000-4000-8000-000000000001')
        slot=db.scalar(select(JudgmentSlot).where(JudgmentSlot.kind=='rubric',JudgmentSlot.dimension=='business_model'))
        rev=db.get(JudgmentRevision,slot.effective_revision_id);v=json.loads(rev.value_json)
        v['rubric_ref']='different-rubric';rev.value_json=canonical(v);db.flush()
        score=score_company(db,company,ws)
        assert len(score['dimensions']['business_model']['evidence_ids'])==4
        v['rubric_ref']='business-model-v1';v['period_end']='2026-01-01';rev.value_json=canonical(v);db.flush()
        assert len(score_company(db,company,ws)['dimensions']['business_model']['evidence_ids'])==4
        v['period_end']='2026-12-31';rev.value_json=canonical(v);rev.valid_until=datetime.now(timezone.utc)-timedelta(seconds=1);db.flush()
        assert len(score_company(db,company,ws)['dimensions']['business_model']['evidence_ids'])==4
        db.rollback()


def test_release_no_resurrection_list_score_history_and_expired_auto(prepared):
    c,ws,_=prepared
    with Session() as db:
        slot=db.scalar(select(JudgmentSlot).where(JudgmentSlot.kind=='impact'))
        key=slot.slot_key;gen=slot.generation
        old=db.get(JudgmentRevision,slot.effective_revision_id);old.valid_until=datetime.now(timezone.utc)-timedelta(seconds=1)
        human_override(db,key,{'magnitude':'-0.2'},gen,ws);db.commit()
        released,_,_=human_override(db,key,{},gen+1,ws,release=True);db.commit()
        assert slot.effective_revision_id is None and released.decision=='released'
    row=next(s for s in c.get('/api/judgments',headers=headers(ws)).json() if s['slot_key']==key)
    assert row['effective'] is None and row['status']=='pending_review'


def test_history_metadata_consistent_and_legacy_unknown(real_mode):
    c,ws,_,ids=real_mode
    with Session() as db:
        item=db.get(InformationItem,ids['item']);old=item.current_revision_id
        item.title='后续新标题';item.summary_text='后续摘要';item.body_url='https://example.com/new';item.publication_json=canonical({'date':'2026-10-06'})
        item.reading_metadata_json=canonical({'data_mode':'real_public','license':'new-license'})
        observe(db,item,{'readable_text':'后来原文'});db.commit()
    r=c.get('/api/intake/items/'+ids['item']+'?revision_id='+old,headers=headers(ws)).json()
    assert r['title']=='原创边界测试文' and r['summary_text']=='原创测试文本'
    assert r['original_text']=='原创测试文本，不是实际财报' and r['publication']['date']=='2026-10-01'
    assert r['body_access']['url'] is None and r['reference_access']==[]
    with Session() as db:
        item=db.get(InformationItem,ids['item']);legacy=ItemRevision(item_id=item.id,content_hash=digest({'readable_text':'旧版'}),payload_json=canonical({'readable_text':'旧版'}));db.add(legacy);db.commit();legacy_id=legacy.id
    r=c.get('/api/intake/items/'+ids['item']+'?revision_id='+legacy_id,headers=headers(ws)).json()
    assert r['metadata_state']=='unavailable' and r['publication']=={} and r['body_access']['url'] is None


def test_template_registered_duplicate_replacement_origins(prepared):
    _,ws,_=prepared
    with Session() as db:
        company=db.get(Company,'00000000-0000-4000-8000-000000000001');base=resolve_template(company)
    import pytest
    for patches in [[{'dimension':'x_unregistered','weight':'0','baseline':base['baselines']['business_model']}],
                    [{'dimension':'business_model','weight':'.25'},{'dimension':'business_model','weight':'.25'}],
                    [{'dimension':'business_model','disabled':True}],
                    [{'dimension':'governance','disabled':True,'weight':'0'}]]:
        with pytest.raises(ValueError):apply_patches(base,patches,'test')
    changed=apply_patches(base,[{'dimension':'business_model','event_policy':{'enabled':False}}],'test')
    assert changed['dimension_policies']['business_model']['event_policy']=={'enabled':False}
    assert changed['field_origins']['business_model']['event_policy.enabled']=='test'
    assert changed['field_origins']['business_model']['weight']==base['field_origins']['business_model']['weight']


def test_watchlist_identity_scope_and_cancel_idempotence(prepared):
    c,ws,other=prepared
    with Session() as db: securities=db.scalars(select(Security).where(Security.company_id=='00000000-0000-4000-8000-000000000001')).all();ids=[s.id for s in securities]
    h=headers(ws)
    for sid in ids:assert c.post('/api/me/watchlist/'+sid,headers=h).status_code==200
    assert {w['security_id'] for w in c.get('/api/me/watchlist',headers=h).json()}==set(ids)
    assert c.get('/api/me/watchlist',headers=headers(other)).json()==[]
    assert c.get('/api/me/watchlist',headers=headers(ws,'viewer@demo')).json()==[]
    for _ in range(2):assert c.delete('/api/me/watchlist/'+ids[0],headers=h).json()['watching'] is False
    assert len(c.get('/api/me/watchlist',headers=h).json())==len(ids)-1


def test_strategy_preserves_rules_and_binds_simulation(prepared):
    c,ws,_=prepared;h=headers(ws,'strat@demo')
    assert c.post('/api/strategy/publish',headers=h,json={'quality_threshold':'70'}).status_code==409
    preview=c.post('/api/strategy/simulate',headers=h,json={'quality_threshold':'70'}).json()
    body={'quality_threshold':'70','simulation_token':preview['simulation_token'],'expected_version':None}
    assert c.post('/api/strategy/publish',headers=h,json={**body,'quality_threshold':'71'}).status_code==409
    assert c.post('/api/strategy/publish',headers=h,json=body).status_code==200
    from app.models.strategy import StrategyVersion
    with Session() as db:
        current=db.scalar(select(StrategyVersion));rules=json.loads(current.rules_json);rules['retain']['all'][0]['value']='62';current.rules_json=canonical(rules);db.commit()
    preview=c.post('/api/strategy/simulate',headers=h,json={'quality_threshold':'75','expected_version':1}).json()
    assert preview['rules']['retain']['all'][0]['value']=='62'
    with Session() as db:
        slot=db.scalar(select(JudgmentSlot).where(JudgmentSlot.kind=='impact'));human_override(db,slot.slot_key,{'magnitude':'0.12'},slot.generation,ws);db.commit()
    publish={'quality_threshold':'75','expected_version':1,'simulation_token':preview['simulation_token']}
    assert c.post('/api/strategy/publish',headers=h,json=publish).status_code==409
    fresh=c.post('/api/strategy/simulate',headers=h,json={'quality_threshold':'75','expected_version':1}).json()
    assert c.post('/api/strategy/publish',headers=h,json={**publish,'simulation_token':fresh['simulation_token']}).status_code==200
    assert c.post('/api/strategy/publish',headers=h,json={**publish,'simulation_token':fresh['simulation_token']}).status_code==409


def gate_inputs():
    c={'quality_exact':'75','coverage_exact':'1','industry_key':'manufacturing','financial_valid':True,
       'dimensions':{d:{'score':'75','baseline_age_days':10} for d in config('strategy-standard-v1.json')['quality_gates']['required_dimensions']},
       'metrics':{'roe_ttm':'.15','cfo_profit_3y':'1','net_debt_ebitda':'1'},'hard_risks':[]}
    s={'valuation_exact':'75','market':'CN_A','common_equity':True,'price_final':True,'price_lag_sessions':0,'approved_inputs':True,'security_id':'a'}
    return c,s


def test_quality_gates_risk_scope_suspend_and_numeric_and():
    rules=config('strategy-standard-v1.json');c,s=gate_inputs()
    assert gates(rules,c,s)['passes'] is True
    c['quality_exact']='60';c['metrics']['roe_ttm']=None
    assert gates(rules,c,s)['passes'] is False # quality gates ready; numeric AND false precedes missing optional value
    c['dimensions']['business_model']['score']=None
    assert gates(rules,c,s)['passes'] is None
    c['hard_risks']=[{'confirmed':True,'risk_code':'confirmed_debt_default','target_kind':'company'}]
    assert gates(rules,c,s)['status']=='risk_excluded'
    c['hard_risks']=[{'confirmed':True,'risk_code':'delisting_decision','target_kind':'security','target_id':'h'}]
    assert gates(rules,c,s)['passes'] is None
    s['suspended']=True;assert gates(rules,c,s)['status']=='suspended'
    c,s=gate_inputs();s['market']='OTHER';assert gates(rules,c,s)['status']=='not_applicable'
    c,s=gate_inputs();c['dimensions']['business_model']['baseline_age_days']=180
    assert gates(rules,c,s)['passes'] is None


def test_system_admin_ops_and_full_access(prepared):
    # 系统管理员为全权限（用户 2026-10-09 决定，ADR 0014）：运维与研究资料都可读；其他角色的边界不变。
    c,ws,_=prepared;h=headers(ws,'admin@demo')
    assert c.get('/api/worker/tasks',headers=h).status_code==200
    assert c.get('/api/worker/sources',headers=h).status_code==200
    assert c.get('/api/intake/items',headers=h).status_code==200
    assert c.get('/api/worker/tasks',headers=headers(ws)).status_code==403
    assert c.post('/api/strategy/simulate',headers=headers(ws),json={'quality_threshold':'70'}).status_code==403


def test_quality_complete_policy_and_baseline_freshness_contract(prepared):
    import pytest
    with Session() as db:base=resolve_template(db.get(Company,'00000000-0000-4000-8000-000000000001'))
    for patch in [{'dimension':'business_model','quality_policy':{}},
                  {'dimension':'business_model','quality_policy':{'evidence_requirement':'accessible_original','freshness':{'kind':'report_obligation'}}},
                  {'dimension':'business_model','event_policy':{'enabled':True}},
                  {'dimension':'business_model','event_policy':{'enabled':False,'half_life_days':90}}]:
        with pytest.raises(ValueError):apply_patches(base,[patch],'test')


def test_score_stage_partial_when_company_ready_but_security_unknown(real_mode):
    c,ws,_,ids=real_mode
    with Session() as db:body=author_body(ids,db.get(ItemRevision,ids['revision']))
    for index,criterion in enumerate(('repeat_demand','pricing_power','competitive_barrier','concentration')):
        r=c.post('/api/judgments',headers={**headers(ws),'Idempotency-Key':'stage-criterion-'+str(index)},json={**body,'criterion':criterion})
        assert r.status_code==201,r.text
    patches=[{'dimension':d,'weight':'1' if d=='business_model' else '0'} for d in config('scoring-standard-v1.json')['dimension_weights']]
    assert c.post('/api/templates/'+ids['company']+'/publish',headers=headers(ws,'strat@demo'),json={'patches':patches}).status_code==200
    score=c.get('/api/companies/'+ids['company']+'/score',headers=headers(ws)).json()
    assert score['quality_score'] is not None and score['securities'][0]['valuation_score'] is None
    run=c.post('/api/research/runs',headers={**headers(ws),'Idempotency-Key':'stage-partial-security'}).json()
    assert next(s for s in run['result']['stages'] if s['stage']=='score')['status']=='partial'


def test_release_worker_revalidates_fixed_cutoff_and_creates_new_revision(prepared):
    from app.models.audit import Outbox
    from app.domains.platform.worker_service import claim,complete
    _,ws,_=prepared
    with Session() as db:
        slot=db.scalar(select(JudgmentSlot).where(JudgmentSlot.kind=='impact'))
        original=slot.effective_revision_id
        human_override(db,slot.slot_key,{'magnitude':'-0.2'},slot.generation,ws);db.flush()
        human_override(db,slot.slot_key,{},slot.generation,ws,release=True);db.commit()
        assert slot.effective_revision_id is None
        event=db.scalar(select(Outbox).where(Outbox.event_type=='judgment.released',Outbox.aggregate_id==slot.id))
        token=claim(db,'ux18-release',event.id,ws);db.commit();assert complete(db,token)=='completed';db.commit()
        assert slot.effective_revision_id and slot.effective_revision_id!=original
        assert db.get(JudgmentRevision,slot.effective_revision_id).author_type=='auto'
        assert complete(db,token)=='already_completed'


def test_release_worker_does_not_accept_expired_proposal(prepared):
    from app.models.audit import Outbox
    from app.domains.platform.worker_service import claim,complete
    _,ws,_=prepared
    with Session() as db:
        slot=db.scalar(select(JudgmentSlot).where(JudgmentSlot.kind=='impact'))
        original=db.get(JudgmentRevision,slot.effective_revision_id);original.valid_until=datetime.now(timezone.utc)-timedelta(seconds=1)
        human_override(db,slot.slot_key,{'magnitude':'-0.2'},slot.generation,ws);db.flush()
        human_override(db,slot.slot_key,{},slot.generation,ws,release=True);db.commit()
        event=db.scalar(select(Outbox).where(Outbox.event_type=='judgment.released',Outbox.aggregate_id==slot.id))
        token=claim(db,'ux18-release',event.id,ws);db.commit();assert complete(db,token)=='completed';db.commit()
        assert slot.effective_revision_id is None
