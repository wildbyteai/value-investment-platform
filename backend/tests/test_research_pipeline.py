"""Original provider-shaped fixtures; never download or reset real data."""
import copy
import json
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select, func
from app.config import get_settings
from app.models.company import Company, Security
from app.models.intake import SourceRegistry
from app.models.runtime import ResearchInput, ItemRevision, ResearchRun, Evaluation
from app.models.audit import AuditLog, Outbox
from app.services.baostock_source import FIELDS, SourceError, validate, import_snapshots
from app.services.transactions import canonical, digest
from test_remediation import prepared, headers, Session


def original_snapshot(code='sz.002594'):
    today=datetime.now(timezone.utc).date()
    dates=[(today-timedelta(days=n)).isoformat() for n in (2,1)]
    payload={'provider':'baostock','version':'0.9.4','code':code,'start':dates[0],'end':dates[1],
        'fields':FIELDS,'observed_at':datetime.now(timezone.utc).isoformat(),
        'rows':[[dates[0],code,'10','11','9','10','10','100','1000','3','1'],
                [dates[1],code,'10','11','9','11','10','100','1100','3','1']]}
    return {'payload':payload,'hash':digest(payload)}


@pytest.mark.parametrize('defect',['identity','duplicate','adjustment','nan','future','empty','ohlc'])
def test_reject_bad_provider_rows(defect):
    p=copy.deepcopy(original_snapshot()['payload'])
    if defect=='identity':p['rows'][0][1]='sz.000651'
    if defect=='duplicate':p['rows'][1][0]=p['rows'][0][0]
    if defect=='adjustment':p['rows'][0][9]='1'
    if defect=='nan':p['rows'][0][5]='NaN'
    if defect=='future':p['observed_at']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    if defect=='empty':p['rows']=[]
    if defect=='ohlc':p['rows'][0][2]='12'
    with pytest.raises(SourceError):validate(p)


@pytest.fixture()
def market(prepared,monkeypatch):
    c,ws,isolated=prepared
    with Session() as db:
        co=Company(name='比亚迪股份有限公司');db.add(co);db.flush()
        db.add_all([Security(company_id=co.id,ticker='002594.SZ',market='CN_A',currency='CNY'),
                    Security(company_id=co.id,ticker='01211.HK',market='HK',currency='HKD')])
        db.flush();snapshot=original_snapshot();run=import_snapshots(db,ws,[snapshot]);db.commit()
        entry=json.loads(run.output_json)['entries'][0]
    monkeypatch.setattr(get_settings(),'demo_mode',False)
    return c,ws,isolated,entry,snapshot


def test_import_retry_and_clock_do_not_invent_revision(market,monkeypatch):
    _,ws,_,entry,snapshot=market
    monkeypatch.setattr(get_settings(),'demo_mode',True)
    with Session() as db:
        before=db.scalar(select(func.count(ResearchInput.id)).where(ResearchInput.synthetic.is_(False)))
        retry=copy.deepcopy(snapshot)
        retry['payload']['observed_at']=datetime.now(timezone.utc).isoformat()
        retry['hash']=digest(retry['payload'])
        import_snapshots(db,ws,[retry]);db.commit()
        assert db.scalar(select(func.count(ResearchInput.id)).where(ResearchInput.synthetic.is_(False)))==before
        assert db.scalar(select(func.count(ItemRevision.id)).where(ItemRevision.item_id==entry['item_id']))==1


def test_real_run_computes_stats_and_preserves_unknown(market):
    c,ws,_,entry,_=market;h={**headers(ws),'Idempotency-Key':'original-run-001'}
    response=c.post('/api/research/runs',headers=h)
    assert response.status_code==200,response.text
    run=response.json();assert run['status']=='partial'
    assert run['manifest']['membership_applied'] is False
    assert run['manifest']['external_model'] is False
    assert run['manifest_hash']==digest(run['manifest'])
    assert len(run['result']['companies'])==1
    co=run['result']['companies'][0];summary=co['analysis'][0]
    assert summary['observations']==2 and summary['change_pct']=='10.000000000000'
    assert co['quality']['quality_score'] is None
    securities={s['market']:s for s in co['securities']}
    assert securities['CN_A']['latest_quote']['raw_close']=='11'
    assert securities['HK']['latest_quote'] is None
    assert all(s['valuation']['pe_ttm'] is None and s['strategy']['result']=='UNKNOWN' for s in securities.values())
    assert c.post('/api/research/runs',headers=h).json()['id']==run['id']
    with Session() as db:
        assert db.scalar(select(func.count(ResearchRun.id)))==1
        assert db.scalar(select(func.count(Evaluation.id)))==0
        for model,field in [(AuditLog,AuditLog.action),(Outbox,Outbox.event_type)]:
            assert db.scalar(select(func.count(model.id)).where(field=='research.preview_completed'))==1
    assert c.get(f"/api/intake/items/{entry['item_id']}",headers=headers(ws)).json()['original_text'].startswith('date,code')
    assert c.get(f"/api/intake/items/{entry['item_id']}?revision_id={entry['revision_id']}",headers=headers(ws)).json()['revision']['id']==entry['revision_id']
    assert c.get(f"/api/intake/items/{entry['item_id']}?revision_id=wrong",headers=headers(ws)).status_code==404
    score=c.get(f"/api/companies/{co['company_id']}/score",headers=headers(ws)).json()
    assert next(s for s in score['securities'] if s['market']=='CN_A')['latest_quote']['raw_close']=='11'
    from app.models.intake import InformationItem
    from app.services.item_history import observe
    with Session() as db:
        observe(db,db.get(InformationItem,entry['item_id']),{'readable_text':'原创后续修订'});db.commit()
    assert c.get(f"/api/intake/items/{entry['item_id']}",headers=headers(ws)).json()['original_text']=='原创后续修订'
    assert c.get(f"/api/intake/items/{entry['item_id']}?revision_id={entry['revision_id']}",headers=headers(ws)).json()['original_text'].startswith('date,code')


def test_run_permissions_workspace_and_revocation(market):
    c,ws,isolated,_,_=market;h={**headers(ws),'Idempotency-Key':'original-run-002'}
    assert c.post('/api/research/runs',headers={**headers(ws,'viewer@demo'),'Idempotency-Key':'denied-key'}).status_code==403
    run=c.post('/api/research/runs',headers=h).json()
    assert c.get('/api/research/runs/'+run['id'],headers=headers(isolated)).status_code==404
    assert c.post('/api/research/runs',headers={**headers(isolated),'Idempotency-Key':'empty-key'}).status_code==409
    # Same business command with a different actor conflicts, even a researcher.
    from app.models.identity import User,Membership
    with Session() as db:
        user=User(login='second-researcher',display_name='原创测试研究员');db.add(user);db.flush()
        db.add(Membership(user_id=user.id,workspace_id=ws,role='researcher'));db.commit()
    assert c.post('/api/research/runs',headers={**headers(ws,'second-researcher'),'Idempotency-Key':h['Idempotency-Key']}).status_code==409
    with Session() as db:
        source=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key=='baostock-a-daily'))
        source.policy_json=canonical({**json.loads(source.policy_json),'revoked':True});db.commit()
    assert c.get('/api/research/runs/'+run['id'],headers=headers(ws)).status_code==403
    assert c.get('/api/research/runs',headers=headers(ws)).json()==[]
    assert c.post('/api/research/runs',headers=h).status_code==403


def test_failed_import_rolls_back_all_effects(prepared):
    _,ws,_=prepared
    with Session() as db:
        with pytest.raises(SourceError,match='REGISTERED_IDENTITY_MISMATCH'):
            import_snapshots(db,ws,[original_snapshot()])
        db.rollback()
        assert db.scalar(select(SourceRegistry.id).where(SourceRegistry.source_key=='baostock-a-daily')) is None
        assert db.scalar(select(AuditLog.id).where(AuditLog.action=='ingestion.baostock_completed')) is None
