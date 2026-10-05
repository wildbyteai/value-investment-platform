"""Real PG regressions for the defects found at 30bb51b."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from sqlalchemy.orm import sessionmaker
from app.db import Base,engine
import app.models
from app.main import app
from scripts_seed import seed
from services_companies import seed_companies,link_items
from app.models.identity import Workspace
from app.models.audit import AuditLog,Outbox
from app.models.judgment import JudgmentSlot,JudgmentRevision
from app.models.runtime import WorkEffect,ItemRevision,ItemObservation
from app.models.company import Company,Security
from app.services.transactions import workspace
from app.services.intake_service import import_fixture
from app.services.decision_service import auto_decide,human_override
from app.services.worker_service import claim,complete
from app.services.state_machine import Eval,GOLDEN,apply_session
from app.services.scoring_service import score_company,score_security,resolve_template,apply_patches
from app.services.item_history import observe
Session=sessionmaker(bind=engine)

@pytest.fixture()
def prepared():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine);seed()
    with Session() as db:
        seed_companies(db);import_fixture(db);link_items(db);auto_decide(db);db.commit();ws=workspace(db)
        isolated=db.scalar(select(Workspace.id).where(Workspace.name=='隔离测试组织'))
    with TestClient(app) as client: yield client,ws,isolated
    Base.metadata.drop_all(engine)

def headers(ws,role='research@demo'): return {'X-Vip-Login':role,'X-Vip-Workspace':ws}
def state(): return SimpleNamespace(status='OUT',pending_count=0,last_confirmed='OUT',last_session=None,last_ordinal=-1)

def test_golden_exact_sessions_and_last_confirmed():
    s=state();changes=[]
    for e in GOLDEN:
        records,_=apply_session(s,e);changes.extend((e.session,r['reason']) for r in records)
        if e.session=='s3': assert s.last_confirmed=='IN' and s.pending_count==0
        if e.session=='s4': assert s.status=='IN' and not records
    assert changes==[('s2','ENTER'),('s3','MISSING_DATA'),('s6','EXIT'),('s8','ENTER'),('s9','RISK')]

def test_provisional_gap_and_late_session():
    s=state();apply_session(s,Eval('s1',True,True,ordinal=1,final=False));assert s.last_session is None
    apply_session(s,Eval('s1',True,True,ordinal=1));assert s.pending_count==1
    apply_session(s,Eval('s3',True,True,ordinal=3,previous_session='s2'));assert s.pending_count==1
    _,result=apply_session(s,Eval('s2',True,True,ordinal=2));assert result=='superseded'
    apply_session(s,Eval('s4',True,True,ordinal=4,previous_session='s3'));assert s.status=='IN'
    apply_session(s,Eval('s5',False,False,ordinal=5,previous_session='s4'));assert s.last_confirmed=='IN'
    apply_session(s,Eval('s6',True,False,ordinal=6,previous_session='s5'));assert s.status=='EXIT_PENDING'

def test_two_person_cas_atomic_and_idempotent(prepared):
    _,ws,_=prepared
    with Session() as db:
        slot=db.scalar(select(JudgmentSlot).where(JudgmentSlot.kind=='impact'));key,gen,id=slot.slot_key,slot.generation,slot.id
        original=db.get(JudgmentRevision,slot.effective_revision_id).value_json
    def compete(value):
        with Session() as db:
            rev,status,current=human_override(db,key,{'magnitude':value},gen,ws,'research-user');db.commit();return status
    with ThreadPoolExecutor(2) as pool: assert sorted(pool.map(compete,['-0.2','0.1']))==['conflict','ok']
    with Session() as db:
        slot=db.get(JudgmentSlot,id);assert slot.generation==gen+1
        assert db.scalar(select(func.count(JudgmentRevision.id)).where(JudgmentRevision.slot_id==id))==2
        assert db.scalar(select(JudgmentRevision.value_json).where(JudgmentRevision.slot_id==id,JudgmentRevision.author_type=='auto'))==original
        for cls,field in [(AuditLog,AuditLog.action),(Outbox,Outbox.event_type)]:
            assert db.scalar(select(func.count(cls.id)).where(field=='judgment.overridden'))==1
        generation=slot.generation
        rev,status,newgen=human_override(db,key,{'magnitude':'-0.1'},generation,ws,'u','same-request');db.commit()
        rev2,status2,gen2=human_override(db,key,{'magnitude':'-0.1'},generation,ws,'u','same-request')
        assert rev.id==rev2.id and newgen==gen2
        assert human_override(db,key,{'magnitude':'0.9'},generation,ws,'u','same-request')[1]=='conflict'

def test_worker_recovery_fencing_and_lost_ack(prepared):
    _,ws,_=prepared
    with Session() as db:
        row=Outbox(workspace_id=ws,aggregate_type='research',aggregate_id='test',event_type='research.updated');db.add(row);db.commit();id=row.id
    def compete(owner):
        with Session() as db:
            token=claim(db,owner,id,ws);db.commit();return token
    with ThreadPoolExecutor(2) as pool: tokens=list(pool.map(compete,['w1','w2']))
    assert sum(t is not None for t in tokens)==1;old=next(t for t in tokens if t)
    with Session() as db:
        row=db.get(Outbox,id);row.lease_until=datetime.now(timezone.utc)-timedelta(seconds=1);db.commit()
        new=claim(db,'replacement',id,ws);db.commit();assert new['fence']>old['fence']
        assert complete(db,old)=='stale_fence';db.rollback()
        assert complete(db,new)=='completed';db.commit()
        assert complete(db,new)=='already_completed';db.commit()
        assert db.scalar(select(func.count(WorkEffect.id)).where(WorkEffect.id==id))==1

def test_financial_valuation_and_override_recalculation(prepared):
    _,ws,_=prepared
    with Session() as db:
        company=db.get(Company,'00000000-0000-4000-8000-000000000001');before=score_company(db,company,ws)
        assert before['coverage_exact']=='1.000000000000' and before['metrics']['roe_ttm']=='0.150000000000'
        assert before['metrics']['cfo_profit_3y']=='1.303030303030'
        values={s.market:score_security(db,s,ws) for s in db.scalars(select(Security).where(Security.company_id==company.id))}
        assert values['CN_A']['pe_exact']=='12.000000000000' and values['HK']['pe_exact']=='14.500000000000'
        assert values['CN_A']['valuation_exact']=='86.666666666667' and values['HK']['valuation_exact']=='70.000000000000'
        slot=db.scalar(select(JudgmentSlot).where(JudgmentSlot.kind=='rubric',JudgmentSlot.dimension=='governance'))
        criterion=json.loads(db.get(JudgmentRevision,slot.effective_revision_id).value_json)['criterion']
        human_override(db,slot.slot_key,{'criterion':criterion,'grade':1},slot.generation,ws);db.commit()
        after=score_company(db,company,ws)
        assert after['dimensions']['governance']['baseline']=='58.333333333333' and after['quality_score']<before['quality_score']
        impact=db.scalar(select(JudgmentSlot).join(JudgmentRevision,JudgmentRevision.id==JudgmentSlot.effective_revision_id)
                         .where(JudgmentSlot.kind=='impact',JudgmentSlot.company_id==company.id,
                                JudgmentRevision.value_json.contains('甲-订单-2026Q3')))
        human_override(db,impact.slot_key,{'magnitude':'-0.2'},impact.generation,ws);db.commit()
        updated=score_company(db,company,ws)
        events=updated['dimensions']['business_model']['events']
        assert len([e for e in events if e['fact_id']=='甲-订单-2026Q3'])==1
        assert next(e for e in events if e['fact_id']=='甲-订单-2026Q3')['contribution'].startswith('-')
        assert updated['quality_score']<after['quality_score']

def test_custom_dimension_and_baseline_only(prepared):
    _,ws,_=prepared
    with Session() as db:
        company=db.get(Company,'00000000-0000-4000-8000-000000000001');other=db.get(Company,'00000000-0000-4000-8000-000000000002')
        from pathlib import Path
        patches=json.loads(Path('../examples/v03-template-custom.json').read_text())['patches']
        custom=apply_patches(resolve_template(other),patches,'custom-test')
        assert score_company(db,company,ws,template=custom)['dimensions']['x_customer_retention']['baseline']=='75.000000000000'
        template=apply_patches(resolve_template(company),[{'dimension':'business_model','event_policy':{'enabled':False}}],'baseline-only')
        assert score_company(db,company,ws,template=template)['dimensions']['business_model']['event_contribution']=='0.000000000000'

def test_history_and_workspace_isolation(prepared):
    c,ws,isolated=prepared
    assert c.get('/api/intake/items',headers=headers(isolated)).json()==[]
    assert c.get('/api/judgments',headers=headers(isolated)).json()==[]
    with Session() as db:
        company=db.get(Company,'00000000-0000-4000-8000-000000000001');earlier=datetime(2026,9,29,tzinfo=timezone.utc)
        result=score_company(db,company,ws,earlier,earlier);assert result['quality_score'] is None and result['input_refs']==[]
        from app.models.intake import InformationItem
        item=db.scalar(select(InformationItem));observe(db,item,{'text':'A'});db.flush();observe(db,item,{'text':'B'});db.flush();observe(db,item,{'text':'A'});db.commit()
        assert db.scalar(select(func.count(ItemRevision.id)).where(ItemRevision.item_id==item.id))==3
        assert db.scalar(select(func.count(ItemObservation.id)).where(ItemObservation.item_id==item.id))==4

def test_publish_permissions_immutable_versions_and_golden_replay(prepared):
    c,ws,_=prepared
    assert c.post('/api/strategy/publish',headers=headers(ws),json={'quality_threshold':'75'}).status_code==403
    h=headers(ws,'strat@demo');preview=c.post('/api/strategy/simulate',headers=h,json={'quality_threshold':'70'})
    assert preview.status_code==200 and len(preview.json()['results'])==3
    one=c.post('/api/strategy/publish',headers=h,json={'quality_threshold':'70'}).json()
    two=c.post('/api/strategy/publish',headers=h,json={'quality_threshold':'75','expected_version':one['version']}).json()
    assert two['version']==one['version']+1
    with Session() as db:
        from app.models.strategy import StrategyVersion
        assert json.loads(db.get(StrategyVersion,one['id']).rules_json)['enter']['all'][0]['value']=='70'
    r=c.post('/api/strategy/run-golden',headers=h);assert r.status_code==200
    assert [(t['session'],t['reason']) for t in r.json()['transitions']][0]==('s2','ENTER')
    assert c.post('/api/strategy/run-golden',headers=h).json()['transitions']==[]


def test_release_preserves_revision_history(prepared):
    _,ws,_=prepared
    with Session() as db:
        slot=db.scalar(select(JudgmentSlot).where(JudgmentSlot.kind=='impact'));old=slot.effective_revision_id
        r,status,gen=human_override(db,slot.slot_key,{'magnitude':'-0.2'},slot.generation,ws);db.commit()
        assert json.loads(r.value_json)['direction']=='negative'
        released,status,gen=human_override(db,slot.slot_key,{},gen,ws,release=True);db.commit()
        assert slot.effective_revision_id==old
        assert db.get(JudgmentRevision,r.id).decision=='accepted'
        assert released.decision=='released'


def test_wrong_criterion_and_nan_rejected(prepared):
    c,ws,_=prepared
    slots=c.get('/api/judgments',headers=headers(ws)).json();rubric=next(s for s in slots if s['kind']=='rubric')
    r=c.post('/api/judgments/'+rubric['slot_key']+'/override',headers={**headers(ws),'If-Match-Generation':str(rubric['generation'])},json={'value':{'grade':1,'criterion':'another-question'}})
    assert r.status_code==422
    impact=next(s for s in slots if s['kind']=='impact')
    r=c.post('/api/judgments/'+impact['slot_key']+'/override',headers={**headers(ws),'If-Match-Generation':str(impact['generation'])},json={'value':{'magnitude':'NaN'}})
    assert r.status_code==422


def test_task_retry_permission_and_scope(prepared):
    c,ws,isolated=prepared
    with Session() as db:
        row=Outbox(workspace_id=ws,aggregate_type='research',aggregate_id='retry',event_type='research.updated',attempts=3,last_error='test failure')
        db.add(row);db.commit();id=row.id
    assert c.post('/api/worker/outbox/'+id+'/retry',headers=headers(ws)).status_code==403
    assert c.post('/api/worker/outbox/'+id+'/retry',headers=headers(isolated,'data@demo')).status_code==404
    assert c.post('/api/worker/outbox/'+id+'/retry',headers=headers(ws,'data@demo')).status_code==200
    with Session() as db:
        token=claim(db,'retry-worker',id,ws);db.commit();assert complete(db,token)=='completed';db.commit()


def test_invalid_template_does_not_publish(prepared):
    c,ws,_=prepared;h=headers(ws,'strat@demo');id='00000000-0000-4000-8000-000000000001'
    for patch in [{'dimension':'business_model','baseline':{'method':'unknown'}},
                  {'dimension':'governance','quality_policy':{'evidence_requirement':'accessible_original','freshness':{'kind':'age_days','max_age_days':0}}}]:
        assert c.post('/api/templates/'+id+'/publish',headers=h,json={'patches':[patch]}).status_code==422
    assert c.get('/api/templates/'+id,headers=h).json()['version'] is None
    assert c.get('/api/companies/'+id+'/score?as_of=2026-09-29T00:00:00',headers=h).status_code==422
    assert c.get('/api/companies/'+id+'/score?cutoff=2026-09-29T00:00:00Z',headers=h).status_code==422


def test_initial_baseline_and_missing_from_confirmed_out():
    s=state();s.last_confirmed=None
    changes,_=apply_session(s,Eval('s1',True,True,ordinal=1))
    assert s.status=='IN' and s.last_confirmed=='IN' and changes==[]
    s=state();s.last_session='s0';s.last_ordinal=0
    changes,_=apply_session(s,Eval('s1',False,False,ordinal=1,previous_session='s0'))
    assert s.status=='UNKNOWN' and s.last_confirmed=='OUT' and changes[0]['reason']=='MISSING_DATA'
