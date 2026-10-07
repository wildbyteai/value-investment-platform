"""T43: real PG snapshots, knowledge cutoff, fencing and atomic recovery.

All source values are original disposable fixtures, never product real inputs.
"""
import json
from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from jsonschema import Draft202012Validator,FormatChecker
from sqlalchemy import select,func,text
from sqlalchemy.exc import DBAPIError
from app.core.errors import DomainError
from sqlalchemy import event
from app.db import engine
from test_remediation import prepare_database,Session,headers
from app.models.company import Company,Security
from app.models.runtime import ResearchInput,Evaluation
from app.models.strategy import StrategyVersion,SecurityState,ChangeRecord
from app.models.sealing import PrimaryListing,MarketSession,KnowledgeEntry,FrozenManifest,EvaluationSeal
from app.models.judgment import JudgmentSlot,JudgmentRevision
from app.models.audit import AuditLog,Outbox
from app.services.transactions import canonical,digest
from app.services.scoring_service import config,ROOT
from app.services import sealing_service as seal
CLOSE=datetime(2026,10,7,8,tzinfo=timezone.utc)
CTX=seal.WorkerContext('seal-a',frozenset({'strategy.seal'}))
# Fixture seeding must be known before the fixed CLOSE cutoff. Without this, seeding
# used the real wall clock and every test failed once real time passed CLOSE+60min
# (a date bomb that went off on 2026-10-07).
SEED_CLOCK=CLOSE-timedelta(hours=6)


def _seed_clock(conn):
    conn.exec_driver_sql("SELECT set_config('vip.test_clock',%(v)s,true)",{'v':SEED_CLOCK.isoformat()})


@pytest.fixture()
def prepared():
    event.listen(engine,'begin',_seed_clock)
    try:
        gen=prepare_database()
        value=next(gen)
    finally:
        event.remove(engine,'begin',_seed_clock)
    yield value
    next(gen,None)

def at(db,minute):db.execute(text("SELECT set_config('vip.test_clock',:v,true)"),{'v':(CLOSE+timedelta(minutes=minute)).isoformat()})

def arrange(ws,market='CN_A',evidence_refs=None):
    with Session() as db:
        at(db,-120);seal.install_artifacts(db,CTX)
        company=db.get(Company,'00000000-0000-4000-8000-000000000001')
        security=db.scalar(select(Security).where(Security.company_id==company.id,Security.market==market))
        release=StrategyVersion(workspace_id=ws,strategy_key='value-standard',version=1,name='T43 fixture',rules_json=canonical(config('strategy-standard-v1.json')),published=True)
        db.add(release);db.flush()
        listing=PrimaryListing(security_id=security.id,exchange=market,currency=security.currency,calendar_ref='approved-'+market,
            close_policy_json=canonical({'approved':True,'price_kinds':['CLOSING'],'evidence':evidence_refs or [{'original_fixture':True}]}))
        db.add(listing);db.add(MarketSession(calendar_ref=listing.calendar_ref,market_session='2026-10-07',ordinal=1,previous_session='2026-10-06',final_market_at=CLOSE,evidence_json=canonical(evidence_refs or [{'fixture':True}])))
        db.flush();session=db.scalar(select(MarketSession).where(MarketSession.calendar_ref==listing.calendar_ref))
        slot=seal.schedule(db,CTX,ws,release.id,security.id,session.id);db.commit()
        return slot.id,security.id,release.id

def claim(id,minute=65,context=CTX):
    with Session() as db:
        at(db,minute);token=seal.claim(db,context,id);db.commit();return token

def freeze(token,minute=65):
    with Session() as db:
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'});at(db,minute)
        row=seal.freeze(db,CTX,token);db.commit();return row.id,row.manifest_hash,json.loads(row.manifest_json)

def finish(token,frozen,minute=65,context=CTX):
    with Session() as db:
        at(db,minute);row=seal.finish(db,context,token,frozen[0],frozen[1]);db.commit();return row.id if row else None

def test_t43_missing_price_provisional_fixed_manifest_lost_ack(prepared):
    _,ws,_=prepared;id,security,release=arrange(ws)
    assert claim(id,15)['state']=='provisional'
    token=claim(id);f=freeze(token)
    Draft202012Validator(json.loads((ROOT/'contracts/evaluation-input-manifest.schema.json').read_text()),format_checker=FormatChecker()).validate(f[2])
    assert datetime.fromisoformat(f[2]['knowledge_cutoff'])==CLOSE+timedelta(minutes=60)
    assert f[2]['inputs']['price']['quality']=='missing'
    assert freeze(token)[0]==f[0]
    result=finish(token,f);assert finish(token,f)==result
    with Session() as db:
        ev=db.get(Evaluation,result);payload=json.loads(ev.result_json)
        assert payload['validity']=='UNKNOWN' and ev.generated_at==CLOSE+timedelta(minutes=65)
        state=db.scalar(select(SecurityState).where(SecurityState.security_id==security,SecurityState.strategy_id==release))
        assert state.pending_count==0
        assert db.scalar(select(func.count(Evaluation.id)))==1
        assert db.scalar(select(func.count(FrozenManifest.id)))==1
        for cls,field in [(AuditLog,AuditLog.action),(Outbox,Outbox.event_type)]:
            assert db.scalar(select(func.count(cls.id)).where(field=='strategy.sealed'))==1
    assert claim(id)['evaluation_id']==result

def price(ws,minute,published=0,key='price:600001.SH',kind='price'):
    with Session() as db:
        at(db,minute)
        payload={'ticker':'600001.SH','currency':'CNY','raw_close':str(10+minute),'fx_per_cny':'1','evidence':[{'fixture':True}],'session':'2026-10-07','is_final':True,'price_kind':'CLOSING'}
        row=ResearchInput(workspace_id=ws,company_id='00000000-0000-4000-8000-000000000001',input_key=key,kind=kind,payload_json=canonical(payload),content_hash=digest(payload),
            effective_at=CLOSE,published_at=CLOSE+timedelta(minutes=published),known_at=CLOSE+timedelta(minutes=minute),synthetic=True)
        db.add(row);db.commit();return row.id

def test_t43_cutoff_and_publication_no_backfill(prepared):
    _,ws,_=prepared;id,_,_=arrange(ws)
    usable=price(ws,40,published=15);late=price(ws,61,published=40)
    after_close=price(ws,50,published=1,key='late-announcement',kind='financial_observations')
    token=claim(id);f=freeze(token)
    refs={r['revision_id'] for group in f[2]['inputs'].values() for r in group['inputs']}
    assert usable in refs and late not in refs and after_close not in refs
    assert f[2]['inputs']['price']['quality']=='valid'
    finish(token,f)

@pytest.mark.parametrize('minute',[15,40,60])
def test_daily_quote_after_close_grace_period_shared_by_preview_and_seal(prepared,minute):
    _,ws,_=prepared;id,_,_=arrange(ws)
    usable=price(ws,minute,published=minute)
    from app.services.scoring_service import inputs
    with Session() as db:
        chosen=inputs(db,'00000000-0000-4000-8000-000000000001',ws,CLOSE,CLOSE+timedelta(minutes=60))
        assert usable in {r.id for r in chosen}
    token=claim(id);f=freeze(token)
    assert usable in {r['revision_id'] for r in f[2]['inputs']['price']['inputs']}
    price(ws,70,published=70)
    assert freeze(token)[0:2]==f[0:2]
    finish(token,f)

def test_after_close_approval_before_cutoff_is_a_known_decision(prepared):
    _,ws,_=prepared;id,_,_=arrange(ws)
    with Session() as db:
        at(db,50)
        slot=JudgmentSlot(slot_key='after-close-review',workspace_id=ws,company_id='00000000-0000-4000-8000-000000000001',kind='risk')
        db.add(slot);db.flush()
        rev=JudgmentRevision(slot_id=slot.id,author_type='human',decision='accepted',created_at=CLOSE+timedelta(minutes=50),
            published_at=CLOSE+timedelta(minutes=50),effective_at=CLOSE,
            value_json=canonical({'confirmed':True,'risk_code':'confirmed_fraud','target_kind':'company','target_id':slot.company_id}),evidence_json='[{"fixture":true}]')
        db.add(rev);db.commit();revision_id=rev.id
    token=claim(id);f=freeze(token)
    assert revision_id in {r['revision_id'] for r in f[2]['inputs']['risks']['inputs']}
    finish(token,f)

def test_real_after_close_disclosure_not_legalized_by_early_approval(prepared,monkeypatch):
    _,ws,_=prepared;_,item,ref=real_branch_fixture(ws)
    from app.services.scoring_service import decision_evidence_published_by
    from app.models.runtime import ItemRevision
    from app.services import data_mode
    monkeypatch.setattr(data_mode,'fixture_mode',lambda:False)
    with Session() as db:
        source=db.get(ItemRevision,ref['source_revision_id'])
        payload=json.loads(source.payload_json);payload['raw_capture']={'disclosure_date':'2026-10-08'}
        source.payload_json=canonical(payload)
        assert not decision_evidence_published_by(db,[ref],CLOSE)
        payload['raw_capture']['disclosure_date']='2026-10-06';source.payload_json=canonical(payload)
        assert decision_evidence_published_by(db,[ref],CLOSE)
        db.rollback()

def test_independent_share_balance_frozen_with_original_reference(prepared):
    _,ws,_=prepared;id,_,_=arrange(ws)
    from test_share_capital import bundle
    from app.services.share_capital import normalize
    b=bundle();b.update(shares_as_of='2026-10-07',ordinary_shares_verified_through='2026-10-07')
    value=normalize(b)
    with Session() as db:
        at(db,-10)
        row=ResearchInput(workspace_id=ws,company_id='00000000-0000-4000-8000-000000000001',input_key='share_capital:c:2026-10-07',kind='share_capital',
            payload_json=canonical(value),content_hash=digest(value),effective_at=CLOSE-timedelta(minutes=10),published_at=CLOSE-timedelta(minutes=10),known_at=CLOSE-timedelta(minutes=10),synthetic=True)
        db.add(row);db.commit();row_id=row.id
    token=claim(id);f=freeze(token)
    assert row_id in {r['revision_id'] for r in f[2]['inputs']['share_capital']['inputs']}
    result=finish(token,f)
    with Session() as db:
        assert json.loads(db.get(Evaluation,result).result_json)['valuation']['share_capital']['input_id']==row_id

def test_two_claimers_expiry_old_fence_recovery(prepared):
    _,ws,_=prepared;id,_,_=arrange(ws)
    contexts=[CTX,seal.WorkerContext('seal-b',CTX.capabilities)]
    with ThreadPoolExecutor(2) as pool:tokens=list(pool.map(lambda c:claim(id,65,c),contexts))
    assert sum(t is not None for t in tokens)==1
    old=next(t for t in tokens if t)
    # Release old claim via expiry, not resetting or stealing it.
    replacement=claim(id,68,CTX);assert replacement['fence']==old['fence']+1
    with Session() as db:
        at(db,68)
        with pytest.raises(DomainError,match='fence'):seal.leased(db,CTX,old)
    f=freeze(replacement,68);assert finish(replacement,f,68)

def test_finish_atomic_rollback_and_append_only(prepared):
    _,ws,_=prepared;id,_,_=arrange(ws);token=claim(id);f=freeze(token)
    with Session() as db:
        at(db,65);seal.finish(db,CTX,token,f[0],f[1]);db.rollback()
    with Session() as db:
        assert db.scalar(select(func.count(Evaluation.id)))==0
        assert db.get(EvaluationSeal,id).state!='sealed'
    result=finish(token,f)
    with Session() as db:
        with pytest.raises(DBAPIError):db.execute(text('UPDATE evaluation SET result_json=\'{}\' WHERE id=:id'),{'id':result})
        db.rollback()
        with pytest.raises(DBAPIError):db.execute(text('DELETE FROM frozen_manifest WHERE id=:id'),{'id':f[0]})
        db.rollback()
        db.execute(text("SELECT set_config('vip.force_immutable','on',true)"))
        with pytest.raises(DBAPIError):db.execute(text('UPDATE research_input SET known_at=:v'),{'v':CLOSE-timedelta(days=500)})

def test_new_live_risk_cannot_be_cleared_by_old_snapshot(prepared):
    _,ws,_=prepared;id,security,release=arrange(ws);token=claim(id);f=freeze(token)
    with Session() as db:
        at(db,66);slot=JudgmentSlot(slot_key='current-risk',workspace_id=ws,company_id='00000000-0000-4000-8000-000000000001',kind='risk')
        db.add(slot);db.flush();rev=JudgmentRevision(slot_id=slot.id,author_type='human',decision='accepted',created_at=CLOSE+timedelta(minutes=66),
            effective_at=CLOSE,value_json=canonical({'confirmed':True,'risk_code':'confirmed_fraud','target_kind':'company','target_id':slot.company_id}),evidence_json='[{"fixture":true}]')
        db.add(rev);db.flush();slot.effective_revision_id=rev.id;db.commit();risk_id=rev.id
    result=finish(token,f,66)
    with Session() as db:
        value=json.loads(db.get(Evaluation,result).result_json)
        assert value['rules']['status']=='risk_excluded' and risk_id in value['current_risk_gate_refs']
        assert risk_id not in {r['revision_id'] for r in f[2]['inputs']['risks']['inputs']}
        state=db.scalar(select(SecurityState).where(SecurityState.security_id==security,SecurityState.strategy_id==release))
        assert state.status=='OUT' and state.pending_count==0

def test_new_release_historical_only_and_unknown_calendar_rejected(prepared):
    _,ws,_=prepared;id,security,release=arrange(ws);token=claim(id);f=freeze(token)
    with Session() as db:
        at(db,66);db.add(StrategyVersion(workspace_id=ws,strategy_key='value-standard',version=2,name='later',rules_json=canonical(config('strategy-standard-v1.json')),published=True));db.commit()
    result=finish(token,f,66)
    with Session() as db:
        assert db.get(Evaluation,result).application_status=='superseded'
        with pytest.raises(DomainError):seal.schedule(db,CTX,ws,release,security,'no-calendar')
        with pytest.raises(DomainError):seal.claim(db,seal.WorkerContext('user',frozenset()),id)

def test_a_h_distinct_slots(prepared):
    _,ws,_=prepared;a,_,_=arrange(ws)
    # Same published release, independent HK listing and approved session.
    with Session() as db:
        at(db,-100);sa=db.get(EvaluationSeal,a);hk=db.scalar(select(Security).where(Security.market=='HK'))
        listing=PrimaryListing(security_id=hk.id,exchange='HKEX',currency='HKD',calendar_ref='HKEX-fixture',close_policy_json='{"approved":true,"price_kinds":["CAS"],"evidence":[{"fixture":true}]}')
        db.add(listing);db.add(MarketSession(calendar_ref=listing.calendar_ref,market_session='2026-10-07',ordinal=1,final_market_at=CLOSE+timedelta(hours=1),evidence_json='[{"fixture":true}]'));db.flush()
        ms=db.scalar(select(MarketSession).where(MarketSession.calendar_ref==listing.calendar_ref));sh=seal.schedule(db,CTX,ws,sa.release_id,hk.id,ms.id);db.commit()
        assert sa.security_id!=sh.security_id and sh.knowledge_cutoff==sa.knowledge_cutoff+timedelta(hours=1)

def test_missing_price_clears_pending_preserves_confirmed_and_explains(prepared):
    c,ws,isolated=prepared;id,security,release=arrange(ws)
    with Session() as db:
        db.add(SecurityState(security_id=security,strategy_id=release,status='EXIT_PENDING',pending_count=1,last_confirmed='IN',last_session='2026-10-06',last_ordinal=0));db.commit()
    token=claim(id);f=freeze(token);result=finish(token,f)
    with Session() as db:
        state=db.scalar(select(SecurityState).where(SecurityState.security_id==security,SecurityState.strategy_id==release))
        assert state.status=='UNKNOWN' and state.pending_count==0 and state.last_confirmed=='IN'
        assert db.scalar(select(ChangeRecord.reason).where(ChangeRecord.evaluation_id==result))=='MISSING_DATA'
    response=c.get('/api/strategy/seals',headers=headers(ws)).json()
    assert response['rows'][0]['validity']=='UNKNOWN' and response['rows'][0]['gaps']
    assert c.get('/api/strategy/seals',headers=headers(isolated)).json()['rows']==[]
    assert c.get('/api/strategy/evaluations/'+result,headers=headers(ws)).status_code==200
    assert c.get('/api/strategy/evaluations/'+result,headers=headers(isolated)).status_code==404
    assert c.post('/api/strategy/seals',headers=headers(ws),json={'is_final':True}).status_code==405

def test_evidence_link_revoked_blocks_old_freeze(prepared):
    _,ws,_=prepared;id,_,_=arrange(ws);token=claim(id);f=freeze(token)
    from app.models.company import ItemCompanyLink
    with Session() as db:
        at(db,66);link=db.get(ItemCompanyLink,f[2]['inputs']['links']['inputs'][0]['revision_id']);link.status='no_link';db.commit()
    assert finish(token,f,66) is None
    with Session() as db:
        assert db.scalar(select(func.count(Evaluation.id)))==0 and db.get(EvaluationSeal,id).state=='blocked_safety'
    assert claim(id,68)['state']=='blocked_safety'

def test_frozen_crash_reclaim_reuses_manifest(prepared):
    _,ws,_=prepared;id,_,_=arrange(ws);token=claim(id);f=freeze(token)
    replacement=claim(id,68);assert replacement['fence']>token['fence']
    assert freeze(replacement,68)[0]==f[0]
    assert finish(replacement,f,68)

def test_template_changes_block_application(prepared):
    _,ws,_=prepared;id,_,_=arrange(ws);token=claim(id);f=freeze(token)
    from app.models.runtime import TemplateRelease
    from app.services.scoring_service import resolve_template
    with Session() as db:
        at(db,66);company=db.get(Company,'00000000-0000-4000-8000-000000000001');template=resolve_template(company)
        template['baseline_max_age_days']=100
        db.add(TemplateRelease(workspace_id=ws,company_id=company.id,version=1,config_json=canonical(template),config_hash=digest(template)));db.commit()
    assert finish(token,f,66) is None

def test_worker_orchestration_calls_real_snapshot_transactions(prepared):
    _,ws,_=prepared;id,_,_=arrange(ws)
    from app.services.seal_worker import run_one
    # Arrange all worker connections at a synthetic clock beyond the fixed cutoff.
    from sqlalchemy import event
    def clock_conn(connection):connection.exec_driver_sql("SELECT set_config('vip.test_clock','2026-10-07T09:05:00+00:00',true)")
    from app.db import engine
    event.listen(engine,'begin',clock_conn)
    try:
        result=run_one(Session,CTX,id);assert result['state']=='sealed'
        assert run_one(Session,CTX,id)['evaluation_id']==result['evaluation_id']
    finally:event.remove(engine,'begin',clock_conn)

def test_late_commit_cannot_backfill_cutoff_even_with_early_created_time(prepared):
    _,ws,_=prepared;id,_,_=arrange(ws)
    with Session() as db:
        at(db,50)
        payload={'ticker':'600001.SH','currency':'CNY','raw_close':'10','fx_per_cny':'1','evidence':[{'fixture':True}],
                 'session':'2026-10-07','is_final':True,'price_kind':'CLOSING'}
        row=ResearchInput(workspace_id=ws,company_id='00000000-0000-4000-8000-000000000001',input_key='price:600001.SH',kind='price',payload_json=canonical(payload),content_hash=digest(payload),effective_at=CLOSE,published_at=CLOSE,known_at=CLOSE+timedelta(minutes=50))
        db.add(row);db.flush();row_id=row.id
        assert db.scalar(select(func.count(KnowledgeEntry.sequence)).where(KnowledgeEntry.entity_id==row_id))==0
        at(db,61);db.commit()
        entry=db.scalar(select(KnowledgeEntry).where(KnowledgeEntry.entity_id==row_id))
        assert entry.recorded_at==CLOSE+timedelta(minutes=61)
    token=claim(id);f=freeze(token)
    assert row_id not in {r['revision_id'] for r in f[2]['inputs']['price']['inputs']}

def test_db_stamp_rejects_caller_backdating_in_strict_mode(prepared):
    _,ws,_=prepared
    with Session() as db:
        at(db,65);db.execute(text("SELECT set_config('vip.force_immutable','on',true)"))
        row=ResearchInput(workspace_id=ws,company_id='00000000-0000-4000-8000-000000000001',input_key='strict-clock',kind='fixture',payload_json='{}',content_hash=digest({}),effective_at=CLOSE,published_at=CLOSE,known_at=CLOSE-timedelta(days=500))
        db.add(row);db.commit();db.refresh(row)
        assert row.known_at==CLOSE+timedelta(minutes=65)

def test_runtime_policy_change_cannot_apply_old_frozen_result(prepared,monkeypatch):
    _,ws,_=prepared;id,_,_=arrange(ws);token=claim(id);f=freeze(token)
    original=seal.config
    def changed(name):
        value=original(name)
        if name=='numeric-policy-v1.json':value={**value,'unexpected_runtime_version':2}
        return value
    monkeypatch.setattr(seal,'config',changed)
    assert finish(token,f) is None

def real_branch_fixture(ws):
    """Exercise real-evidence code using explicitly disposable original test text.

    Registry remains local-fixture. This is not a source license or real material.
    """
    from app.models.intake import InformationItem,SourceRegistry
    from app.models.runtime import ItemRevision
    from app.models.company import ItemCompanyLink
    with Session() as db:
        at(db,-120)
        item=db.scalar(select(InformationItem).join(ItemCompanyLink,ItemCompanyLink.item_id==InformationItem.id).where(
            ItemCompanyLink.company_id=='00000000-0000-4000-8000-000000000001',ItemCompanyLink.status=='accepted'))
        item.reading_metadata_json=canonical({'data_mode':'real_public','test_only':'original disposable fixture'});item.body_state='available'
        source=db.get(SourceRegistry,item.source_id);source.policy_json=canonical({'license':'original disposable fixture only','fetch':True,'store':True,'analyze':True,'export':False})
        revision=db.scalar(select(ItemRevision).where(ItemRevision.item_id==item.id))
        # server_default now() is wall-clock; pin the fixture revision before the fixed cutoff.
        revision.created_at=SEED_CLOCK
        ref={'synthetic':False,'source_revision_id':revision.id,'hash':revision.content_hash,'locator':'original disposable test document table 1'}
        db.commit();return source.id,item.id,ref

def add_original_fixture_input(ws,ref):
    with Session() as db:
        at(db,-90);original=db.scalar(select(ResearchInput).where(ResearchInput.kind=='financials'))
        payload={**json.loads(original.payload_json),'evidence':[ref]}
        db.add(ResearchInput(workspace_id=ws,company_id=original.company_id,input_key='financials',kind='financials',payload_json=canonical(payload),content_hash=digest(payload),effective_at=original.effective_at,published_at=original.published_at,known_at=CLOSE-timedelta(minutes=90),synthetic=False));db.commit()

def test_real_evidence_branch_and_source_revocation(prepared,monkeypatch):
    _,ws,_=prepared;source,item,ref=real_branch_fixture(ws);id,_,_=arrange(ws,evidence_refs=[ref]);add_original_fixture_input(ws,ref)
    from app.services import data_mode
    monkeypatch.setattr(data_mode,'fixture_mode',lambda:False)
    token=claim(id);f=freeze(token)
    assert f[2]['inputs']['financials']['quality']=='valid'
    assert any(r['revision_id']==source for r in f[2]['inputs']['rights']['inputs'])
    from app.models.intake import SourceRegistry
    with Session() as db:
        at(db,66);row=db.get(SourceRegistry,source);row.policy_json=canonical({**json.loads(row.policy_json),'revoked':True});db.commit()
    assert finish(token,f,66) is None

def test_new_permission_cannot_be_backfilled_to_frozen_cutoff(prepared,monkeypatch):
    _,ws,_=prepared;source,item,ref=real_branch_fixture(ws);id,_,_=arrange(ws,evidence_refs=[ref]);add_original_fixture_input(ws,ref)
    from app.models.intake import SourceRegistry
    with Session() as db:
        at(db,61);row=db.get(SourceRegistry,source);row.policy_json=canonical({**json.loads(row.policy_json),'new_permission_scope':'changed after cutoff'});db.commit()
    from app.services import data_mode
    monkeypatch.setattr(data_mode,'fixture_mode',lambda:False)
    token=claim(id)
    with pytest.raises(DomainError,match='新许可'):freeze(token)

def test_late_link_does_not_make_old_input_known_at_cutoff(prepared,monkeypatch):
    _,ws,_=prepared;source,item,ref=real_branch_fixture(ws);id,_,_=arrange(ws,evidence_refs=[ref]);add_original_fixture_input(ws,ref)
    from app.models.company import ItemCompanyLink
    with Session() as db:
        at(db,50);links=db.scalars(select(ItemCompanyLink).where(ItemCompanyLink.item_id==item,ItemCompanyLink.company_id=='00000000-0000-4000-8000-000000000001')).all()
        for link in links:link.status='no_link'
        db.commit();at(db,61)
        for link in links:link.status='accepted'
        db.commit()
    from app.services import data_mode
    monkeypatch.setattr(data_mode,'fixture_mode',lambda:False)
    token=claim(id);f=freeze(token)
    assert f[2]['inputs']['financials']['quality']=='missing'
    assert finish(token,f)

def test_late_source_revision_does_not_make_financials_eligible(prepared,monkeypatch):
    _,ws,_=prepared;source,item,ref=real_branch_fixture(ws);id,_,_=arrange(ws,evidence_refs=[ref])
    from app.models.runtime import ItemRevision
    with Session() as db:
        at(db,50);payload={'readable_text':'original disposable late source fixture'}
        rev=ItemRevision(item_id=item,payload_json=canonical(payload),content_hash=digest(payload),created_at=CLOSE+timedelta(minutes=50));db.add(rev);db.flush()
        late_ref={'synthetic':False,'source_revision_id':rev.id,'hash':rev.content_hash,'locator':'late original fixture table A'}
        at(db,61);db.commit()
    # Input record is backdated only in disposable fixtures to prove DB-ledger filtering.
    with Session() as db:
        at(db,50);original=db.scalar(select(ResearchInput).where(ResearchInput.kind=='financials'));payload={**json.loads(original.payload_json),'evidence':[late_ref]}
        db.add(ResearchInput(workspace_id=ws,company_id=original.company_id,input_key='financials',kind='financials',payload_json=canonical(payload),content_hash=digest(payload),effective_at=original.effective_at,published_at=original.published_at,known_at=CLOSE+timedelta(minutes=50),synthetic=False));db.commit()
    from app.services import data_mode
    monkeypatch.setattr(data_mode,'fixture_mode',lambda:False)
    token=claim(id);f=freeze(token)
    assert f[2]['inputs']['financials']['quality']=='missing'
