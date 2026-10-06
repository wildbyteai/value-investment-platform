"""Synthetic-only provider fixtures; no live SDK import, login or requests."""
import json
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from sqlalchemy import select, func
from app.models.company import Company, Security, ItemCompanyLink
from app.models.intake import SourceRegistry, InformationItem
from app.models.runtime import ResearchInput
from app.models.audit import AuditLog, Outbox
from app.services.item_history import observe
from app.services.transactions import digest, canonical
from app.services.futu_source import (SourceError, REQUEST, ISSUERS, SDK_VERSION,
    validate, validate_rights, import_snapshot, capture)
from app.services.research_pipeline import source_stats, evidence_for
from test_remediation import prepared, Session


def rights():
    return {'provider':'futu','reviewed':True,'fetch':True,'store':True,'analyze':True,
            'export':False,'external_model':False,'use':'local_personal_research',
            'agreement':'SYNTHETIC agreement, not a real provider license',
            'clause_locator':'synthetic clause 1','permitted_scope':'synthetic-only test',
            'reviewed_at':(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()}


def snapshot(ticker='01211.HK', receipt=None):
    day=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat()
    info=[{'code':'HK.'+ticker[:5],'name':ISSUERS[ticker][1][0], 'stock_type':'STOCK',
           'exchange_type':'HK_MAINBOARD','delisting':False,'stock_id':'12345'}]
    bars=[{'code':'HK.'+ticker[:5],'time_key':day+' 00:00:00','open':'10.00','high':'12.00',
           'low':'9.00','close':'11.25','volume':'100'}]
    return {'provider':'futu','ticker':ticker,'sdk_version':SDK_VERSION,'representation':'sdk_decoded_rows',
            'request':deepcopy(REQUEST),'start':day,'end':day,'rights':receipt or rights(),
            'observed_at':datetime.now(timezone.utc).isoformat(),'next_page_present':False,
            'identity_rows':info,'bars_rows':bars,'identity_rows_sha256':digest(info),'bars_rows_sha256':digest(bars)}


@pytest.mark.parametrize('defect',['ticker','unknown','exchange','stock_id','delisted','identity_duplicate',
    'adjusted','pagination','hash','future','today','window','duplicate','wrong_code','ohlc','nan','volume','rights'])
def test_unsafe_snapshot_rejected(defect):
    s=snapshot()
    if defect=='ticker':s['ticker']='00700.HK'
    if defect=='unknown':s['identity_rows'][0]['name']='未知股票'
    if defect=='exchange':s['identity_rows'][0]['exchange_type']='US_NYSE'
    if defect=='stock_id':s['identity_rows'][0]['stock_id']='0'
    if defect=='delisted':s['identity_rows'][0]['delisting']=True
    if defect=='identity_duplicate':s['identity_rows']*=2
    if defect=='adjusted':s['request']['autype']='QFQ'
    if defect=='pagination':s['next_page_present']=True
    if defect=='future':s['observed_at']='2099-01-01T00:00:00+00:00'
    if defect=='today':s['end']=datetime.now(timezone.utc).date().isoformat()
    if defect=='window':s['start']='2020-01-01'
    if defect=='duplicate':s['bars_rows']*=2
    if defect=='wrong_code':s['bars_rows'][0]['code']='HK.09969'
    if defect=='ohlc':s['bars_rows'][0]['high']='1'
    if defect=='nan':s['bars_rows'][0]['close']='NaN'
    if defect=='volume':s['bars_rows'][0]['volume']='1.5'
    if defect=='rights':s['rights']['store']=False
    s['identity_rows_sha256']=digest(s['identity_rows']);s['bars_rows_sha256']=digest(s['bars_rows'])
    if defect=='hash':s['bars_rows_sha256']='a'*64
    with pytest.raises(SourceError):validate(s)


def install_fake_sdk(monkeypatch, snapshots, fail=False, pagination=False):
    import app.services.futu_source as source
    calls=[]
    class Frame:
        def __init__(self, rows):self.rows=rows
        def to_dict(self,orient):assert orient=='records';return self.rows
    class Context:
        def __init__(self,**kwargs):calls.append(('open',kwargs))
        def set_sync_query_connect_timeout(self,n):calls.append(('timeout',n))
        def get_stock_basicinfo(self, market, **kwargs):
            calls.append(('identity',kwargs))
            rows=[{**s['identity_rows'][0],'stock_id':12345} for s in snapshots]
            return 0,Frame(rows)
        def request_history_kline(self,code,**kwargs):
            calls.append(('history',code,kwargs))
            if fail:return -1,'secret account text must never escape',None
            s=next(s for s in snapshots if s['ticker'][:5]==code[3:])
            return 0,Frame(s['bars_rows']),b'next' if pagination else None
        def close(self):calls.append(('close',))
    fields=SimpleNamespace(**{k:k for k in ('DATE_TIME','OPEN','HIGH','LOW','CLOSE','VOLUME')})
    sdk=SimpleNamespace(OpenQuoteContext=Context,Market=SimpleNamespace(HK='HK'),SecurityType=SimpleNamespace(STOCK='STOCK'),
        KLType=SimpleNamespace(K_DAY='K_DAY'),AuType=SimpleNamespace(NONE='NONE'),KL_FIELD=fields,RET_OK=0)
    logger=SimpleNamespace(enable_console_log=lambda value:None)
    monkeypatch.setitem(sys.modules,'futu',sdk)
    monkeypatch.setitem(sys.modules,'futu.common.ft_logger',SimpleNamespace(logger=logger))
    monkeypatch.setattr(source,'connection_ready',lambda:True)
    monkeypatch.setattr(source,'version',lambda name:SDK_VERSION)
    return calls


def test_capture_explicit_unadjusted_two_symbols_and_no_trade(monkeypatch,tmp_path):
    import app.services.futu_source as source
    receipt=rights();snapshots=[snapshot(t,receipt) for t in ISSUERS]
    calls=install_fake_sdk(monkeypatch,snapshots)
    monkeypatch.setattr(source,'ROOT',tmp_path)
    start=datetime.fromisoformat(snapshots[0]['start']).date()
    captured=capture(start,start,receipt)
    assert len(captured)==2 and all(p.exists() for p,_ in captured)
    histories=[call for call in calls if call[0]=='history']
    assert {call[1] for call in histories}=={'HK.01211','HK.09969'}
    assert all(call[2]['autype']=='NONE' and call[2]['max_count']==40 and call[2]['page_req_key'] is None for call in histories)
    assert calls[-1]==('close',)
    assert all('currency' not in s for _,s in captured)


@pytest.mark.parametrize('failure',['login','pagination','offline','rights'])
def test_capture_stops_without_outputting_secret_or_saving_partial(monkeypatch,tmp_path,failure):
    import app.services.futu_source as source
    receipt=rights();snapshots=[snapshot(t,receipt) for t in ISSUERS]
    calls=install_fake_sdk(monkeypatch,snapshots,fail=failure=='login',pagination=failure=='pagination')
    monkeypatch.setattr(source,'ROOT',tmp_path)
    if failure=='offline':monkeypatch.setattr(source,'connection_ready',lambda:False)
    if failure=='rights':receipt['store']=False
    day=datetime.fromisoformat(snapshots[0]['start']).date()
    with pytest.raises(SourceError) as error:capture(day,day,receipt)
    assert 'secret' not in str(error.value)
    assert not list(tmp_path.rglob('*.json'))
    if failure in ('login','pagination'):assert calls[-1]==('close',)
    else:assert calls==[]


def seed_identity_and_currency(db,ws,ticker):
    company=Company(name=ISSUERS[ticker][0]);db.add(company);db.flush()
    db.add(Security(company_id=company.id,ticker=ticker,market='HK',currency='HKD'))
    source=SourceRegistry(source_key='synthetic-currency-'+ticker,name='合成挂牌币种依据',policy_json=canonical({'license':'synthetic-only','fetch':True,'store':True,'analyze':True}))
    db.add(source);db.flush()
    passage='合成挂牌说明：'+ticker+'报价币种HKD；不代表任何真实挂牌证据。'
    item=InformationItem(workspace_id=ws,source_id=source.id,entry_key=ticker,title='合成币种原文',content_kind='dataset',body_state='available',reading_metadata_json=canonical({'data_mode':'real_public'}))
    db.add(item);db.flush();rev=observe(db,item,{'readable_text':passage})
    db.add(ItemCompanyLink(item_id=item.id,company_id=company.id,status='accepted',label_text=company.name,relevance=1,confidence=1));db.flush()
    ref={'synthetic':False,'source_revision_id':rev.id,'hash':rev.content_hash,'locator':'readable_text','item_id':item.id}
    return {'ticker':ticker,'currency':'HKD','reviewed':True,'excerpt':passage,'evidence':[ref]}


def test_two_companies_import_replay_evidence_summary_and_atomic_audit(prepared):
    _,ws,_=prepared
    receipt=rights()
    with Session() as db:
        results=[]
        for ticker in ISSUERS:
            basis=seed_identity_and_currency(db,ws,ticker)
            s=snapshot(ticker,receipt)
            first=import_snapshot(db,ws,s,basis);db.commit()
            second=import_snapshot(db,ws,s,basis);db.commit()
            assert second['reused'] and first['input_id']==second['input_id']
            payload=json.loads(db.get(ResearchInput,first['input_id']).payload_json)
            assert payload['raw_close']=='11.25' and payload['is_final'] is False
            assert payload['currency']=='HKD' and len(payload['evidence'])==2 and 'fx_per_cny' not in payload
            item=db.get(InformationItem,first['item_id'])
            summary=source_stats(db,item,evidence_for(db,item))
            assert summary['kind']=='market_summary' and summary['last_close']=='11.25'
            results.append(first)
        assert results[0]['input_id']!=results[1]['input_id']
        for model,field in ((AuditLog,AuditLog.action),(Outbox,Outbox.event_type)):
            assert db.scalar(select(func.count(model.id)).where(field=='research.futu_imported'))==2


@pytest.mark.parametrize('failure',['no_currency','wrong_currency','invented_excerpt','cross_workspace','revoked'])
def test_no_currency_or_inaccessible_evidence_never_creates_price(prepared,failure):
    _,ws,other=prepared
    with Session() as db:
        basis=seed_identity_and_currency(db,ws,'09969.HK')
        if failure=='no_currency':basis={}
        if failure=='wrong_currency':basis['currency']='CNY'
        if failure=='invented_excerpt':basis['excerpt']='not in the original source'
        if failure=='revoked':
            source=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key=='synthetic-currency-09969.HK'))
            source.policy_json=canonical({'license':'synthetic-only','fetch':True,'store':True,'analyze':True,'revoked':True});db.flush()
        with pytest.raises(SourceError):import_snapshot(db,other if failure=='cross_workspace' else ws,snapshot('09969.HK'),basis)
        assert db.scalar(select(func.count(ResearchInput.id)).where(ResearchInput.input_key=='price:09969.HK'))==0
        assert db.scalar(select(SourceRegistry).where(SourceRegistry.source_key=='futu-personal-hk')) is None
