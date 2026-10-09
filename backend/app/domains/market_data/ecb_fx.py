"""Bounded ECB reference FX capture; EUR cross-rate, never a market close."""
import csv
import hashlib
import io
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from sqlalchemy import select, text, func
from app.models.company import Company, ItemCompanyLink
from app.models.intake import SourceRegistry, InformationItem
from app.models.runtime import ResearchInput
from app.domains.platform.transactions import canonical, digest, record
from app.domains.news.item_history import observe

URL = 'https://data-api.ecb.europa.eu/service/data/EXR/D.HKD+CNY.EUR.SP00.A'
POLICY = {'license':'ECB-free-attributed-reference-data',
          'basis':'https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html',
          'fetch':'explicit official API, at most 30 calendar days, no polling',
          'store':'attributed local personal research', 'analyze':'accurate local reference analysis; derived cross-rate identified',
          'export':'disabled', 'external_model':False}


def validate(snapshot):
    if snapshot.get('provider')!='ecb' or snapshot.get('url')!=URL:
        raise ValueError('ECB source mismatch')
    raw=snapshot['raw'];observed=datetime.fromisoformat(snapshot['observed_at'])
    start=date.fromisoformat(snapshot['start']);end=date.fromisoformat(snapshot['end'])
    if (observed.tzinfo is None or observed>datetime.now(timezone.utc)+timedelta(seconds=1)
        or end>observed.date() or not 0<=(end-start).days<=29
        or len(raw.encode())>1_000_000 or hashlib.sha256(raw.encode()).hexdigest()!=snapshot['raw_sha256']):
        raise ValueError('ECB hash/window/clock mismatch')
    rows=list(csv.DictReader(io.StringIO(raw)));pairs={}
    if not 1<=len(rows)<=60:raise ValueError('ECB row bound')
    for index,row in enumerate(rows):
        day=date.fromisoformat(row['TIME_PERIOD']);currency=row['CURRENCY']
        if (not start<=day<=end or currency not in ('HKD','CNY') or row.get('CURRENCY_DENOM')!='EUR'
            or row.get('FREQ')!='D' or row.get('EXR_TYPE')!='SP00' or row.get('EXR_SUFFIX')!='A'
            or row.get('OBS_STATUS')!='A' or row.get('UNIT')!=currency or row.get('UNIT_MULT')!='0'
            or row.get('KEY')!='EXR.D.'+currency+'.EUR.SP00.A'):
            raise ValueError('ECB date/series/unit/status mismatch')
        try:value=Decimal(row['OBS_VALUE'])
        except (InvalidOperation,TypeError):raise ValueError('ECB decimal mismatch') from None
        if not value.is_finite() or value<=0:raise ValueError('ECB rate must be positive finite')
        pair=pairs.setdefault(day.isoformat(),{})
        if currency in pair:raise ValueError('ECB duplicate day/currency')
        pair[currency]={'original_value':row['OBS_VALUE'],'row_index':index}
    result=[]
    for day,pair in sorted(pairs.items()):
        if set(pair)!= {'HKD','CNY'}:raise ValueError('ECB same-day currency pair incomplete')
        with localcontext() as context:
            context.prec=50
            rate=Decimal(pair['HKD']['original_value'])/Decimal(pair['CNY']['original_value'])
        result.append({'session':day,'pair':'HKD_PER_CNY','value':format(rate,'f'),
                       'components':pair,'method':'hkd_per_eur_divided_by_cny_per_eur_v1'})
    return result


def capture(start,end,directory):
    if not 0<=(end-start).days<=29:raise ValueError('ECB capture bound')
    request=Request(URL+'?'+urlencode({'startPeriod':start.isoformat(),'endPeriod':end.isoformat(),'format':'csvdata'}),
                    headers={'Accept':'text/csv'})
    with urlopen(request,timeout=30) as response:
        if response.url.split('/')[2]!='data-api.ecb.europa.eu':raise ValueError('ECB response host mismatch')
        raw=response.read(1_000_001)
    if len(raw)>1_000_000:raise ValueError('ECB response too large')
    snapshot={'provider':'ecb','url':URL,'start':start.isoformat(),'end':end.isoformat(),
              'observed_at':datetime.now(timezone.utc).isoformat(),'raw':raw.decode('utf-8-sig'),
              'raw_sha256':hashlib.sha256(raw.decode('utf-8-sig').encode()).hexdigest()}
    validate(snapshot);directory.mkdir(parents=True,exist_ok=True)
    path=directory/(digest(snapshot)+'.json');path.write_text(canonical(snapshot))
    return path,snapshot


def import_snapshot(db,workspace_id,company_ids,snapshot):
    from app.domains.platform import data_mode
    actual=db.execute(text('SELECT current_database(),inet_server_addr()::text')).one()
    if actual[0]!='vip_v0001_local' and not (actual[0]=='vip_v0001_test' and data_mode.fixture_mode()):raise ValueError('ECB database mismatch')
    if actual[1] not in ('127.0.0.1/32','::1/128'):raise ValueError('ECB server mismatch')
    if not 1<=len(company_ids)<=3 or len(set(company_ids))!=len(company_ids):raise ValueError('ECB company bound')
    for id in company_ids:data_mode.require_company(db,id,workspace_id)
    rows=validate(snapshot)
    db.execute(select(func.pg_advisory_xact_lock(int(digest({'source':'ecb-reference-fx'})[:15],16))))
    source=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key=='ecb-reference-fx'))
    if source and json.loads(source.policy_json)!=POLICY:raise ValueError('ECB policy changed/revoked')
    if not source:
        source=SourceRegistry(source_key='ecb-reference-fx',name='欧洲央行｜每日参考汇率',policy_json=canonical(POLICY));db.add(source);db.flush()
    key=snapshot['start']+':'+snapshot['end']
    item=db.scalar(select(InformationItem).where(InformationItem.workspace_id==workspace_id,InformationItem.source_id==source.id,InformationItem.entry_key==key).with_for_update())
    if not item:
        item=InformationItem(workspace_id=workspace_id,source_id=source.id,entry_key=key,title='欧洲央行｜人民币与港币同日参考汇率',content_kind='dataset');db.add(item);db.flush()
    item.summary_text=f'{len(rows)}日官方参考汇率；人民币与港币对欧元原值相除，不代表香港收盘时点汇率。'
    item.publication_json=canonical({'date':None,'precision':'unknown','meaning':'逐日参考日期保留；确切各日发布时点未核验'})
    item.reading_metadata_json=canonical({'data_mode':'real_public','material_type':'fx_daily','license':POLICY['license'],
                                         'attribution':'European Central Bank; derived cross-rate','source_observed_at':snapshot['observed_at']})
    item.body_state='available';item.body_url=URL
    retained={k:v for k,v in snapshot.items() if k!='observed_at'}
    revision=observe(db,item,{'readable_text':snapshot['raw'],'raw_capture':retained,'source_policy':POLICY})
    ref={'synthetic':False,'source_revision_id':revision.id,'hash':revision.content_hash,'item_id':item.id,'locator':'raw_capture.raw / CSV rows'}
    payload={'provider':'ecb','pair':'HKD_PER_CNY','rows':rows,'evidence':[ref],
             'meaning':'ECB daily reference cross-rate; not Hong Kong close-time FX', 'raw_sha256':snapshot['raw_sha256']}
    sha=digest(payload);result=[]
    for id in company_ids:
        if not db.scalar(select(ItemCompanyLink.id).where(ItemCompanyLink.item_id==item.id,ItemCompanyLink.company_id==id)):
            company=db.get(Company,id);db.add(ItemCompanyLink(item_id=item.id,company_id=id,status='accepted',label_text=company.name,relevance=1,confidence=1));db.flush()
        input_key='fx:HKD_PER_CNY:'+id
        old=db.scalar(select(ResearchInput).where(ResearchInput.workspace_id==workspace_id,ResearchInput.company_id==id,ResearchInput.input_key==input_key,ResearchInput.content_hash==sha))
        reused=old is not None
        if not old:
            at=datetime.fromisoformat(snapshot['observed_at'])
            old=ResearchInput(workspace_id=workspace_id,company_id=id,input_key=input_key,kind='fx',payload_json=canonical(payload),content_hash=sha,effective_at=at,published_at=at,synthetic=False)
            db.add(old);db.flush();record(db,workspace_id,None,'research.ecb_fx_imported','research_input',old.id,{'hash':sha,'days':len(rows)})
        result.append({'input_id':old.id,'reused':reused})
    return {'item_id':item.id,'revision_id':revision.id,'hash':revision.content_hash,'days':len(rows),'last_session':rows[-1]['session'],'inputs':result}


def analysis(snapshot,ref):
    rows=validate(snapshot)
    return {'kind':'fx_summary','source_item_id':ref['item_id'],'source_revision_id':ref['source_revision_id'],
            'first_session':rows[0]['session'],'last_session':rows[-1]['session'],'observations':len(rows),
            'pair':'HKD_PER_CNY','last_rate':rows[-1]['value'],'meaning':'欧洲央行同日参考汇率交叉换算；每1元人民币对应港币金额，非香港收盘时点汇率。', 'evidence':[ref]}


def matching_fx(input_rows,session):
    """Only already-eligible input rows; never reuse the nearest or latest day."""
    for row in input_rows:
        if row.kind!='fx':continue
        payload=json.loads(row.payload_json)
        if payload.get('provider')!='ecb' or payload.get('pair')!='HKD_PER_CNY':continue
        matches=[r for r in payload['rows'] if r['session']==session]
        if len(matches)!=1:continue
        matched=matches[0]
        return row,{'pair':'HKD_PER_CNY','session':session,'value':matched['value'],
                    'method':matched['method'],'components':matched['components'],
                    'evidence':[{**ref,'locator':f"raw_capture.raw / CSV rows {matched['components']['HKD']['row_index']},{matched['components']['CNY']['row_index']}"} for ref in payload['evidence']]}
    return None,None
