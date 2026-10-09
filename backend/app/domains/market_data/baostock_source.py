"""Bounded free A-share provider; no silent network access or external models."""
from app.core.paths import REPO_ROOT
import hashlib
import json
from contextlib import contextmanager, redirect_stdout
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import getproxies
from zoneinfo import ZoneInfo
from sqlalchemy import select, text, func
from app.models.company import Company, Security, ItemCompanyLink
from app.models.intake import InformationItem, SourceRegistry
from app.models.audit import IngestionRun
from app.models.runtime import ResearchInput
from app.domains.news.item_history import observe
from app.domains.platform.transactions import canonical, digest, record

ROOT=REPO_ROOT
TARGETS={'sz.002594':('比亚迪股份有限公司','002594.SZ'),'sz.000651':('珠海格力电器股份有限公司','000651.SZ')}
FIELDS=['date','code','open','high','low','close','preclose','volume','amount','adjustflag','tradestatus']
POLICY={
    'license':'provider-published-free-local-financial-analysis',
    'basis':'https://pypi.org/project/baostock/0.9.4/',
    'basis_description':'Free china stock market data; financial analysts/data mining; provider example saves API result to CSV',
    'fetch':'anonymous public API; two named A-share companies; 30 days; at most 100 rows',
    'store':'local attributed JSON and research database only',
    'analyze':'local deterministic financial research; no external models',
    'export':'disabled; no redistribution grant inferred',
    'external_model':False,
    'final_close_policy':'unverified; provider daily close may be read but cannot seal strategy',
}


class SourceError(ValueError): pass


@contextmanager
def provider_connection():
    """Use the existing local proxy, without editing the SDK or system settings."""
    import baostock as bs
    import baostock.util.socketutil as sdk
    import baostock.common.context as context
    from baostock.common import contants
    proxy=urlsplit(getproxies().get('all',''))
    original=sdk.SocketUtil.connect
    class BoundedTransport:
        def __init__(self,s):self.s=s;self.total=0
        def send(self,value):self.s.sendall(value);return len(value)
        def recv(self,n):
            value=self.s.recv(n);self.total+=len(value)
            if not value:raise ConnectionError('PROVIDER_CONNECTION_CLOSED')
            if self.total>2_000_000:raise SourceError('RESPONSE_TOO_LARGE')
            return value
        def close(self):return self.s.close()
    def connect(_self,key):
        if key not in ('0',''):raise SourceError('ONLY_ANONYMOUS_PUBLIC_API_ALLOWED')
        if proxy.scheme=='socks5' and proxy.hostname in ('127.0.0.1','localhost'):
            import socks
            connection=socks.socksocket()
            connection.set_proxy(socks.SOCKS5,proxy.hostname,proxy.port,rdns=True)
        else:
            import socket
            connection=socket.socket()
        connection.settimeout(15)
        try:connection.connect((contants.BAOSTOCK_SERVER_IP,contants.BAOSTOCK_SERVER_PORT))
        except Exception:
            connection.close();raise SourceError('PROVIDER_CONNECTION_FAILED') from None
        context.default_socket=BoundedTransport(connection)
    sdk.SocketUtil.connect=connect
    try:
        # SDK prints operational errors; do not log anonymous credentials/proxy URLs.
        with redirect_stdout(StringIO()):
            login=bs.login()
            if login.error_code!='0':raise SourceError('PROVIDER_LOGIN_FAILED:'+login.error_code)
        yield bs,context
    finally:
        connection=getattr(context,'default_socket',None)
        if connection:connection.close()
        context.default_socket=None
        sdk.SocketUtil.connect=original


def capture_daily(end=None):
    end=end or datetime.now(ZoneInfo('Asia/Shanghai')).date()
    start=end-timedelta(days=29)
    results=[];total=0
    with provider_connection() as (bs,context):
        for code in TARGETS:
            context.default_socket.total=0
            with redirect_stdout(StringIO()):
                result=bs.query_history_k_data_plus(code,','.join(FIELDS),start_date=start.isoformat(),end_date=end.isoformat(),frequency='d',adjustflag='3')
                rows=[]
                while result.error_code=='0' and result.next():
                    rows.append(result.get_row_data());total+=1
                    if len(rows)>50 or total>100:raise SourceError('ROW_BOUND_EXCEEDED')
            if result.error_code!='0':raise SourceError('DAILY_QUERY_FAILED:'+result.error_code)
            if not rows:raise SourceError('NO_DAILY_DATA')
            payload={'provider':'baostock','version':'0.9.4','code':code,'start':start.isoformat(),'end':end.isoformat(),
                     'fields':result.fields,'rows':rows,'observed_at':datetime.now(timezone.utc).isoformat()}
            validate(payload)
            raw=canonical(payload).encode();content_hash=hashlib.sha256(raw).hexdigest()
            directory=ROOT/'raw-data/baostock';directory.mkdir(parents=True,exist_ok=True)
            path=directory/(code+'-'+content_hash+'.json')
            if not path.exists():path.write_bytes(raw)
            results.append({'path':str(path),'hash':content_hash,'payload':payload})
    return results


def validate(payload):
    if payload.get('provider')!='baostock' or payload.get('version')!='0.9.4' or payload.get('code') not in TARGETS:
        raise SourceError('SOURCE_OR_IDENTITY_MISMATCH')
    if payload.get('fields')!=FIELDS:raise SourceError('UNEXPECTED_COLUMNS')
    start=date.fromisoformat(payload['start']);end=date.fromisoformat(payload['end'])
    observed=datetime.fromisoformat(payload['observed_at'])
    if observed.tzinfo is None or end<start or (end-start).days>29:raise SourceError('INVALID_WINDOW_OR_CLOCK')
    if observed>datetime.now(timezone.utc)+timedelta(seconds=1) or end>observed.astimezone(ZoneInfo('Asia/Shanghai')).date():raise SourceError('FUTURE_CAPTURE')
    rows=payload.get('rows',[])
    if not rows or len(rows)>50:raise SourceError('INVALID_ROW_COUNT')
    normalized=[];seen=set()
    for index,values in enumerate(rows):
        if len(values)!=len(FIELDS):raise SourceError('INVALID_ROW_SHAPE')
        row=dict(zip(FIELDS,values));session=date.fromisoformat(row['date'])
        if row['code']!=payload['code'] or not start<=session<=end or session in seen:raise SourceError('ROW_IDENTITY_OR_DATE_MISMATCH')
        if row['adjustflag']!='3':raise SourceError('UNADJUSTED_PRICE_REQUIRED')
        if row['tradestatus'] not in ('0','1'):raise SourceError('UNRECOGNIZED_TRADING_STATUS')
        seen.add(session)
        try:
            for key in ['open','high','low','close','preclose','volume','amount']:
                number=Decimal(row[key])
                if not number.is_finite() or number<0 or (key=='close' and number<=0):raise SourceError('INVALID_PRICE_VALUE')
        except (InvalidOperation,TypeError):raise SourceError('INVALID_DECIMAL') from None
        if Decimal(row['high'])<max(Decimal(row['open']),Decimal(row['close'])) or Decimal(row['low'])>min(Decimal(row['open']),Decimal(row['close'])):
            raise SourceError('INCONSISTENT_A_SHARE_BAR')
        normalized.append({**row,'row_index':index})
    return sorted(normalized,key=lambda r:r['date'])


def import_snapshots(db,workspace_id,snapshots,actor_id=None):
    actual=db.execute(text('SELECT current_database(),inet_server_addr()::text')).one()
    # Tests may inject original snapshots; the real CLI is local-only.
    from app.domains.platform.data_mode import fixture_mode
    if actual[0]!='vip_v0001_local' and not (actual[0]=='vip_v0001_test' and fixture_mode()):raise SourceError('UNAPPROVED_DB')
    if actual[1] not in ('127.0.0.1/32','::1/128'):raise SourceError('NONLOCAL_DATABASE')
    if len(snapshots)>2 or sum(len(s['payload']['rows']) for s in snapshots)>100:raise SourceError('CAPTURE_BOUND_EXCEEDED')
    db.execute(select(func.pg_advisory_xact_lock(int(digest({'source':'baostock-a-daily'})[:15],16))))
    source=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key=='baostock-a-daily'))
    if source and json.loads(source.policy_json).get('revoked'):raise SourceError('SOURCE_REVOKED')
    if source is None:
        source=SourceRegistry(source_key='baostock-a-daily',name='BaoStock免费A股日线',policy_json=canonical(POLICY));db.add(source);db.flush()
    run=IngestionRun(workspace_id=workspace_id,source_key=source.source_key,status='running',note='two A-share securities; provider daily close, FINAL policy unverified')
    db.add(run);db.flush();results=[]
    for snapshot in snapshots:
        payload=snapshot['payload'];rows=validate(payload)
        name,ticker=TARGETS[payload['code']]
        company=db.scalar(select(Company).where(Company.name==name))
        security=db.scalar(select(Security).where(Security.ticker==ticker,Security.market=='CN_A'))
        if company is None or security is None or security.company_id!=company.id or security.currency!='CNY':raise SourceError('REGISTERED_IDENTITY_MISMATCH')
        key=payload['code']+':'+payload['start']+':'+payload['end']
        # Concurrent snapshot import serializes by source/key/workspace.
        lock=int(digest({'ws':workspace_id,'source':source.id,'entry':key})[:15],16)
        db.execute(select(func.pg_advisory_xact_lock(lock)))
        item=db.scalar(select(InformationItem).where(InformationItem.workspace_id==workspace_id,InformationItem.source_id==source.id,InformationItem.entry_key==key).with_for_update())
        if item is None:
            item=InformationItem(workspace_id=workspace_id,source_id=source.id,entry_key=key,title=name+'｜真实A股日线',content_kind='dataset');db.add(item);db.flush()
        latest=rows[-1];table='\n'.join([','.join(FIELDS)]+[','.join(values) for values in payload['rows']])
        item.summary_text=f"{name} {ticker}，{len(rows)}个交易日；供应商日线最新日期{latest['date']}。收盘价最终性政策尚未核验，不作为正式策略封存依据。"
        item.publication_json=canonical({'date':None,'precision':'unknown','meaning':'来源未提供批次发布时间；行情交易日独立记录'})
        item.reading_metadata_json=canonical({'data_mode':'real_public','material_type':'market_daily','license':POLICY['license'],'attribution':'BaoStock 0.9.4 public API','change_notice':'原始字段保留，计算仅本地；未复权；CNY；不外传','request_window':{'start':payload['start'],'end':payload['end']},'raw_hash':snapshot['hash'],'source_observed_at':payload['observed_at']})
        item.body_state='available';item.body_url=None
        revision=observe(db,item,{'readable_text':table,'raw_capture':{k:v for k,v in payload.items() if k!='observed_at'},'source_policy':POLICY})
        if not db.scalar(select(ItemCompanyLink.id).where(ItemCompanyLink.item_id==item.id,ItemCompanyLink.company_id==company.id)):
            db.add(ItemCompanyLink(item_id=item.id,company_id=company.id,label_text=company.name,status='accepted',relevance=1,confidence=1))
        price={'ticker':ticker,'currency':'CNY','raw_close':latest['close'],'session':latest['date'],'price_kind':'provider_daily_bar_close','is_final':False,
               'finality_reason':'FINAL_CLOSE_POLICY_NOT_VERIFIED','fx_per_cny':'1','adjustflag':'3','tradestatus':latest['tradestatus'],
               'publication_precision':'unknown','eligibility_basis':'provider_capture_time','evidence':[{'synthetic':False,'source_revision_id':revision.id,'hash':revision.content_hash,'locator':f"raw_capture.rows[{latest['row_index']}].close",'issuer_original':False}]}
        content_hash=digest(price)
        existing=db.scalar(select(ResearchInput.id).where(ResearchInput.workspace_id==workspace_id,ResearchInput.input_key=='price:'+ticker,ResearchInput.content_hash==content_hash))
        if not existing:
            # Date precision is kept in payload; midnight is only a conservative
            # eligibility boundary, never presented as a published instant.
            effective=datetime.fromisoformat(latest['date']+'T00:00:00+08:00')
            db.add(ResearchInput(workspace_id=workspace_id,company_id=company.id,input_key='price:'+ticker,kind='price',payload_json=canonical(price),content_hash=content_hash,effective_at=effective,published_at=datetime.fromisoformat(payload['observed_at']),synthetic=False))
        results.append({'item_id':item.id,'revision_id':revision.id,'ticker':ticker,'rows':len(rows),'last_session':latest['date'],'raw_hash':snapshot['hash'],'price_final':False})
    run.status='completed';run.input_manifest_hash=digest([s['hash'] for s in snapshots]);run.output_json=canonical({'entries':results,'mode':'real_public','external_model':False})
    record(db,workspace_id,actor_id,'ingestion.baostock_completed','ingestion_run',run.id,{'entries':len(results),'manifest_hash':run.input_manifest_hash})
    db.flush();return run
