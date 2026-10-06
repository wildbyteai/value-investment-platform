"""Original synthetic market values only; no credentials or live requests."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import pytest
from sqlalchemy import select, func
from app.models.audit import AuditLog, Outbox
from app.models.company import Company, Security
from app.models.intake import SourceRegistry, InformationItem
from app.models.runtime import ResearchInput
from app.services.eodhd_source import (SourceError, validate, validate_fx, identity,
    import_snapshot, POLICY, FX_URL, request_json)
from app.services.transactions import canonical
from test_remediation import prepared, Session


def snapshot():
    end=datetime.now(timezone.utc).date()-timedelta(days=1)
    raw_id=canonical([{'Code':'1211','Exchange':'HK','Currency':'HKD','Type':'Common Stock','Name':'BYD Company Limited'}])
    bars='[{"date":"'+end.isoformat()+'","open":10.01,"high":12.20,"low":9.20,"close":11.1234,"adjusted_close":5.5617,"volume":123456}]'
    return {'provider':'eodhd','ticker':'01211.HK','provider_symbol':'1211.HK','start':(end-timedelta(days=29)).isoformat(),'end':end.isoformat(),
            'observed_at':datetime.now(timezone.utc).isoformat(),'identity_raw':raw_id,'bars_raw':bars,
            'identity_raw_sha256':hashlib.sha256(raw_id.encode()).hexdigest(),'bars_raw_sha256':hashlib.sha256(bars.encode()).hexdigest()}


def fx_snapshot(day):
    raw=canonical({'header':{'success':True},'result':{'records':[{'end_of_day':day,'cny':'1.12345'}]}})
    return {'provider':'hkma','url':FX_URL,'raw':raw,'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'observed_at':datetime.now(timezone.utc).isoformat()}


def test_raw_close_never_uses_adjusted_and_precision_survives():
    rows=validate(snapshot())
    assert rows[0]['close']=='11.1234' and rows[0]['adjusted_close']=='5.5617'


@pytest.mark.parametrize('change',['currency','issuer','symbol','hash','future','window','duplicate','bar','nan'])
def test_invalid_identity_and_response_rejected(change):
    s=snapshot()
    if change in ('currency','issuer'):
        rows=json.loads(s['identity_raw']);rows[0]['Currency' if change=='currency' else 'Name']='OTHER';s['identity_raw']=canonical(rows)
        s['identity_raw_sha256']=hashlib.sha256(s['identity_raw'].encode()).hexdigest()
    if change=='symbol':s['provider_symbol']='002594.SHE'
    if change=='hash':s['bars_raw_sha256']='a'*64
    if change=='future':s['observed_at']='2099-01-01T00:00:00+00:00'
    if change=='window':s['start']='2020-01-01'
    if change in ('duplicate','bar','nan'):
        rows=json.loads(s['bars_raw'])
        if change=='duplicate':rows+=deepcopy(rows)
        if change=='bar':rows[0]['high']='1'
        if change=='nan':rows[0]['close']='NaN'
        s['bars_raw']=canonical(rows);s['bars_raw_sha256']=hashlib.sha256(s['bars_raw'].encode()).hexdigest()
    with pytest.raises(SourceError):validate(s)


def test_ambiguous_identity_not_silently_selected():
    row=json.loads(snapshot()['identity_raw'])[0]
    with pytest.raises(SourceError):identity(canonical([row,row]))


def test_provider_failure_never_exposes_authenticated_url(monkeypatch):
    from urllib.error import HTTPError
    import app.services.eodhd_source as source
    class Broken:
        def open(self,*args,**kwargs):raise HTTPError('https://eodhd.com/?api_token=LOCAL_TEST_SECRET',401,'bad',{},None)
    monkeypatch.setattr(source,'build_opener',lambda *args:Broken())
    with pytest.raises(SourceError) as error:request_json('https://eodhd.com/api/search/1211',{},'LOCAL_TEST_SECRET')
    assert str(error.value)=='PROVIDER_HTTP_401'
    assert 'LOCAL_TEST_SECRET' not in str(error.value)


def test_secret_settings_and_redirect_rejection():
    from app.config import Settings
    from app.services.eodhd_source import NoRedirect
    s=Settings(_env_file=None,EODHD_API_TOKEN='LOCAL_TEST_SECRET')
    assert s.eodhd_api_token.get_secret_value()=='LOCAL_TEST_SECRET'
    assert 'LOCAL_TEST_SECRET' not in repr(s)
    assert NoRedirect().redirect_request(None,None,302,'redirect',{},'https://other.example') is None

def test_absent_hk_exchange_stops_before_price_requests(monkeypatch,tmp_path):
    import app.services.eodhd_source as source
    from app.config import Settings
    calls=[]
    def request(url,params,token):
        calls.append(url)
        return canonical([{'Code':'US','Name':'US exchanges'}])
    monkeypatch.setattr(source,'get_settings',lambda:Settings(_env_file=None,EODHD_API_TOKEN='LOCAL_TEST_SECRET'))
    monkeypatch.setattr(source,'request_json',request)
    monkeypatch.setattr(source,'ROOT',tmp_path)
    with pytest.raises(SourceError,match='PROVIDER_HK_EXCHANGE_NOT_SUPPORTED'):source.capture()
    assert calls==['https://eodhd.com/api/exchanges-list']

@pytest.mark.parametrize('code,retry',[('PROVIDER_HTTP_502',True),('PROVIDER_HTTP_403',False),('PROVIDER_HTTP_429',False)])
def test_fx_direct_retry_only_for_transport_failures(monkeypatch,tmp_path,code,retry):
    import app.services.eodhd_source as source
    calls=[];day=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat()
    def request(url,params,token=None,direct=False):
        calls.append(direct)
        if not direct:raise SourceError(code)
        return fx_snapshot(day)['raw']
    monkeypatch.setattr(source,'request_json',request);monkeypatch.setattr(source,'ROOT',tmp_path)
    if retry:
        _,s=source.capture_fx();assert validate_fx(s)[day]['value']=='1.12345'
        assert calls==[False,True]
    else:
        with pytest.raises(SourceError,match=code):source.capture_fx()
        assert calls==[False]


def seed_byd(db):
    c=Company(name='比亚迪股份有限公司');db.add(c);db.flush()
    db.add(Security(company_id=c.id,ticker='01211.HK',market='HK',currency='HKD'));db.flush()
    return c


def test_real_import_replay_and_same_day_fx(prepared):
    _,ws,_=prepared;s=snapshot();fx=fx_snapshot(s['end'])
    with Session() as db:
        company=seed_byd(db)
        first=import_snapshot(db,ws,s,fx);db.commit()
        second=import_snapshot(db,ws,s,fx);db.commit()
        assert first['input_id']==second['input_id'] and second['reused'] and second['same_day_fx']
        assert not second['price_final']
        row=db.get(ResearchInput,first['input_id']);payload=json.loads(row.payload_json)
        assert payload['raw_close']=='11.1234' and payload['fx_per_cny']=='1.12345'
        assert len(payload['evidence'])==2
        for cls,field in [(AuditLog,AuditLog.action),(Outbox,Outbox.event_type)]:
            assert db.scalar(select(func.count(cls.id)).where(field=='research.eodhd_imported'))==1
        source=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key=='eodhd-byd-hk'))
        source.policy_json=canonical({**POLICY,'revoked':True});db.flush()
        with pytest.raises(SourceError):import_snapshot(db,ws,s,fx)
        db.rollback()


def test_stale_fx_is_not_imported_or_forward_filled(prepared):
    _,ws,_=prepared;s=snapshot();fx=fx_snapshot((datetime.fromisoformat(s['end'])-timedelta(days=1)).date().isoformat())
    with Session() as db:
        seed_byd(db);result=import_snapshot(db,ws,s,fx);db.flush()
        assert not result['same_day_fx']
        assert 'fx_per_cny' not in json.loads(db.get(ResearchInput,result['input_id']).payload_json)
        assert db.scalar(select(SourceRegistry).where(SourceRegistry.source_key=='hkma-daily-fx')) is None
        db.rollback()
