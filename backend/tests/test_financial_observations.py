"""Original financial fixtures; provider ratios never normalize themselves."""
import calendar
import copy
import json
from datetime import datetime, date, timedelta, timezone
import pytest
from sqlalchemy import select,func
from app.config import get_settings
from app.models.company import Company,Security
from app.models.runtime import ResearchInput,ResearchRun,ItemRevision
from app.models.intake import SourceRegistry
from app.domains.market_data.baostock_source import SourceError,TARGETS
from app.domains.companies.baostock_financial import FIELDS,periods,validate,import_snapshots
from app.domains.platform.transactions import canonical,digest
from test_remediation import prepared,headers,Session


def original(code='sz.002594'):
    as_of=date(2026,10,2);reports=[]
    for year,quarter in periods(as_of):
        stat=date(year,quarter*3,calendar.monthrange(year,quarter*3)[1]);pub=stat+timedelta(days=1)
        for kind,fields in FIELDS.items():
            values={k:'1' for k in fields};values.update(code=code,statDate=stat.isoformat(),pubDate=pub.isoformat())
            if kind=='profit':values.update(netProfit=str(10+5*(year-2023)),totalShare='100',liqaShare='50')
            reports.append({'kind':kind,'year':year,'quarter':quarter,'fields':fields,'rows':[[values[k] for k in fields]]})
    return {'provider':'baostock','version':'0.9.4','report_type':'financial_metrics','code':code,'as_of':as_of.isoformat(),
        'observed_at':datetime.now(timezone.utc).isoformat(),'reports':reports}


@pytest.mark.parametrize('defect',['identity','period','publication','nan','duplicate','missing_query','no_data','columns'])
def test_bad_financial_snapshot_rejected(defect):
    p=copy.deepcopy(original());r=p['reports'][0];idx=lambda k:r['fields'].index(k)
    if defect=='identity':r['rows'][0][idx('code')]='sz.000651'
    if defect=='period':r['rows'][0][idx('statDate')]='2022-12-31'
    if defect=='publication':r['rows'][0][idx('pubDate')]='2099-01-01'
    if defect=='nan':r['rows'][0][idx('netProfit')]='NaN'
    if defect=='duplicate':p['reports'].append(copy.deepcopy(r))
    if defect=='missing_query':p['reports'].pop()
    if defect=='no_data':
        for report in p['reports']:report['rows']=[]
    if defect=='columns':r['fields']=r['fields'][:-1]
    with pytest.raises(SourceError):validate(p)


@pytest.fixture()
def finance(prepared,monkeypatch):
    c,ws,isolated=prepared;snapshots=[]
    with Session() as db:
        for code,(name,ticker) in TARGETS.items():
            co=Company(name=name);db.add(co);db.flush()
            db.add(Security(company_id=co.id,ticker=ticker,market='CN_A',currency='CNY'))
            if code=='sz.002594':db.add(Security(company_id=co.id,ticker='01211.HK',market='HK',currency='HKD'))
            payload=original(code);snapshots.append({'payload':payload,'hash':digest(payload)})
        db.flush();run=import_snapshots(db,ws,snapshots);db.commit();entries=json.loads(run.output_json)['entries']
    monkeypatch.setattr(get_settings(),'demo_mode',False)
    return c,ws,isolated,snapshots,entries


def test_financial_read_compute_gap_and_retry(finance,monkeypatch):
    c,ws,_,snapshots,entries=finance
    monkeypatch.setattr(get_settings(),'demo_mode',True)
    with Session() as db:
        retry=copy.deepcopy(snapshots)
        for s in retry:s['payload']['observed_at']=datetime.now(timezone.utc).isoformat();s['hash']=digest(s['payload'])
        import_snapshots(db,ws,retry);db.commit()
        assert db.scalar(select(func.count(ResearchInput.id)).where(ResearchInput.synthetic.is_(False),ResearchInput.kind=='financial_observations'))==2
        assert db.scalar(select(func.count(ResearchInput.id)).where(ResearchInput.synthetic.is_(False),ResearchInput.kind=='financials'))==0
        for entry in entries:assert db.scalar(select(func.count(ItemRevision.id)).where(ItemRevision.item_id==entry['item_id']))==1
    monkeypatch.setattr(get_settings(),'demo_mode',False)
    h={**headers(ws),'Idempotency-Key':'original-financial-run'}
    response=c.post('/api/research/runs',headers=h);assert response.status_code==200,response.text
    run=response.json();assert run['status']=='partial' and len(run['result']['companies'])==2
    for co in run['result']['companies']:
        assert co['quality']['financial_observations_available']
        assert co['quality']['quality_score'] is None and co['quality']['metrics']=={}
        summary=next(a for a in co['analysis'] if a['kind']=='financial_summary')
        assert summary['report_rows']==20 and len(summary['periods'])==5
        assert summary['annual_net_profit_field_change_pct']=='100.000000000000'
        assert summary['standard_metrics_eligible'] is False
        assert any('CFO' in gap for gap in summary['missing_data'])
        assert all(s['strategy']['result']=='UNKNOWN' and not s['strategy']['applied'] for s in co['securities'])
    assert c.post('/api/research/runs',headers=h).json()['id']==run['id']
    # Preserve retries of runs created before algorithm v2 was added.
    with Session() as db:
        saved=db.get(ResearchRun,run['id'])
        saved.request_hash=digest({'actor':saved.actor_id,'mode':'real_research_preview','algorithm':'local-research-preview-v1'});db.commit()
    assert c.post('/api/research/runs',headers=h).json()['id']==run['id']
    for entry in entries:
        detail=c.get('/api/intake/items/'+entry['item_id'],headers=headers(ws)).json()
        assert 'netProfit' in detail['original_text'] and detail['body_access']['url'] is None
        assert detail['reading_metadata']['normalization_status']=='unsupported_standard_metrics'


def test_financial_revocation_hides_inputs_and_saved_results(finance):
    c,ws,_,_,_=finance
    run=c.post('/api/research/runs',headers={**headers(ws),'Idempotency-Key':'financial-revocation'}).json()
    with Session() as db:
        source=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key=='baostock-a-financial'))
        source.policy_json=canonical({**json.loads(source.policy_json),'revoked':True});db.commit()
    assert c.get('/api/research/runs/'+run['id'],headers=headers(ws)).status_code==403
    assert c.get('/api/research/runs',headers=headers(ws)).json()==[]
    assert c.get('/api/companies',headers=headers(ws)).json()==[]


def test_empty_field_retained_and_does_not_make_comparison():
    p=original()
    for r in p['reports']:
        if r['kind']=='profit':r['rows'][0][r['fields'].index('netProfit')]=''
    from app.domains.companies.baostock_financial import analysis
    result=analysis(p,{'item_id':'original','source_revision_id':'original'})
    assert result['annual_net_profit_field_change_pct'] is None
    assert result['periods'][0]['values']['netProfit'] is None
