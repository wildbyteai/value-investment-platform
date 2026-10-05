"""Provider financial observations are readable facts, not normalized financials."""
import hashlib
import json
import calendar
from datetime import datetime, date, timezone
from decimal import Decimal, InvalidOperation, localcontext
from contextlib import redirect_stdout
from io import StringIO
from zoneinfo import ZoneInfo
from sqlalchemy import select, func, text
from app.models.intake import SourceRegistry, InformationItem
from app.models.company import Company, Security, ItemCompanyLink
from app.models.audit import IngestionRun
from app.models.runtime import ResearchInput
from app.services.baostock_source import ROOT, TARGETS, POLICY, SourceError, provider_connection
from app.services.transactions import canonical, digest, record
from app.services.item_history import observe

FIELDS={
 'profit':['code','pubDate','statDate','roeAvg','npMargin','gpMargin','netProfit','epsTTM','MBRevenue','totalShare','liqaShare'],
 'balance':['code','pubDate','statDate','currentRatio','quickRatio','cashRatio','YOYLiability','liabilityToAsset','assetToEquity'],
 'cash_flow':['code','pubDate','statDate','CAToAsset','NCAToAsset','tangibleAssetToAsset','ebitToInterest','CFOToOR','CFOToNP','CFOToGr'],
 'dupont':['code','pubDate','statDate','dupontROE','dupontAssetStoEquity','dupontAssetTurn','dupontPnitoni','dupontNitogr','dupontTaxBurden','dupontIntburden','dupontEbittogr'],
}
FINANCIAL_POLICY={**POLICY,'fetch':'anonymous public financial API; two named companies; last three complete fiscal years plus latest half-year/comparative; at most 100 rows',
 'financial_semantics':'raw provider fields; currency/unit/consolidation/share rights/flow period not asserted; no standardized scoring from ratios'}
GAPS=[
 '供应商未附完整币种、单位、合并/归母/普通股及累计/单季口径说明',
 '缺少可匹配的普通股TTM利润与平均普通股权益原始值',
 '缺少三个完整年度同合并口径的CFO与净利润原始值',
 '缺少利息负债、现金、EBITDA、EBIT及利息费用原始值',
 '股本字段未证明A/H等权普通股范围；报告义务尚未配置',
]


def periods(as_of):
    year=as_of.year
    full=[(y,4) for y in range(year-3,year)]
    # On/before June 30 no current half-year has ended.
    if as_of>date(year,6,30):full += [(year-1,2),(year,2)]
    return full


def capture():
    as_of=datetime.now(ZoneInfo('Asia/Shanghai')).date();snapshots=[];total=0
    with provider_connection() as (bs,context):
        for code in TARGETS:
            reports=[]
            for year,quarter in periods(as_of):
                for kind in FIELDS:
                    context.default_socket.total=0
                    with redirect_stdout(StringIO()):
                        result=getattr(bs,'query_'+kind+'_data')(code,year=year,quarter=quarter)
                        rows=[]
                        while result.error_code=='0' and result.next():
                            rows.append(result.get_row_data());total+=1
                            if len(rows)>2 or total>100:raise SourceError('FINANCIAL_ROW_BOUND_EXCEEDED')
                    if result.error_code!='0':raise SourceError('FINANCIAL_QUERY_FAILED:'+result.error_code)
                    reports.append({'kind':kind,'year':year,'quarter':quarter,'fields':result.fields,'rows':rows})
            payload={'provider':'baostock','version':'0.9.4','report_type':'financial_metrics','code':code,
                'as_of':as_of.isoformat(),'observed_at':datetime.now(timezone.utc).isoformat(),'reports':reports}
            validate(payload)
            raw=canonical(payload).encode();h=hashlib.sha256(raw).hexdigest()
            directory=ROOT/'raw-data/baostock-financial';directory.mkdir(parents=True,exist_ok=True)
            path=directory/(code+'-'+h+'.json')
            if not path.exists():path.write_bytes(raw)
            snapshots.append({'payload':payload,'hash':h,'path':str(path)})
    return snapshots


def validate(payload):
    if payload.get('provider')!='baostock' or payload.get('version')!='0.9.4' or payload.get('report_type')!='financial_metrics' or payload.get('code') not in TARGETS:
        raise SourceError('FINANCIAL_SOURCE_MISMATCH')
    try:
        observed=datetime.fromisoformat(payload['observed_at']);as_of=date.fromisoformat(payload['as_of'])
    except (KeyError,ValueError,TypeError):raise SourceError('INVALID_FINANCIAL_CLOCK') from None
    if observed.tzinfo is None or observed>datetime.now(timezone.utc) or as_of>observed.astimezone(ZoneInfo('Asia/Shanghai')).date():raise SourceError('FUTURE_OR_UNZONED_FINANCIAL_CAPTURE')
    reports=payload.get('reports',[]);expected={(y,q,k) for y,q in periods(as_of) for k in FIELDS}
    keys=set();normalized=[]
    for ri,report in enumerate(reports):
        key=(report.get('year'),report.get('quarter'),report.get('kind'))
        if key not in expected or key in keys:raise SourceError('FINANCIAL_PERIOD_OR_REPORT_MISMATCH')
        keys.add(key);kind=key[2]
        if report.get('fields')!=FIELDS[kind]:raise SourceError('UNEXPECTED_FINANCIAL_COLUMNS')
        rows=report.get('rows',[])
        if len(rows)>1:raise SourceError('AMBIGUOUS_FINANCIAL_REVISION')
        for rj,values in enumerate(rows):
            if len(values)!=len(FIELDS[kind]) or not all(isinstance(v,str) for v in values):raise SourceError('INVALID_FINANCIAL_ROW_SHAPE')
            row=dict(zip(FIELDS[kind],values))
            if row['code']!=payload['code']:raise SourceError('FINANCIAL_IDENTITY_MISMATCH')
            try:
                pub=date.fromisoformat(row['pubDate']);stat=date.fromisoformat(row['statDate'])
            except ValueError:raise SourceError('INVALID_FINANCIAL_DATE') from None
            month=key[1]*3;expected_stat=date(key[0],month,calendar.monthrange(key[0],month)[1])
            if stat!=expected_stat or not stat<=pub<=as_of:raise SourceError('FINANCIAL_PERIOD_OR_PUBLICATION_MISMATCH')
            for field,value in row.items():
                if field in ('code','pubDate','statDate') or value=='':continue
                try:number=Decimal(value)
                except InvalidOperation:raise SourceError('INVALID_FINANCIAL_DECIMAL') from None
                if not number.is_finite() or (field in ('totalShare','liqaShare') and number<0):raise SourceError('INVALID_FINANCIAL_VALUE')
            normalized.append({'kind':kind,'year':key[0],'quarter':key[1],'values':row,'report_index':ri,'row_index':rj})
    if keys!=expected:raise SourceError('INCOMPLETE_FINANCIAL_QUERY_MANIFEST')
    if not normalized:raise SourceError('NO_FINANCIAL_DATA')
    return normalized


def analysis(payload,ref):
    rows=validate(payload);by_period={}
    for row in rows:
        values=row['values'];key=values['statDate']
        entry=by_period.setdefault(key,{'stat_date':key,'reports':{},'values':{}})
        entry['reports'][row['kind']]={'pub_date':values['pubDate'],'locator':f"raw_capture.reports[{row['report_index']}].rows[{row['row_index']}]"}
        entry['values'].update({k:v or None for k,v in values.items() if k not in ('code','pubDate','statDate')})
    annual=sorted((r for r in rows if r['kind']=='profit' and r['quarter']==4),key=lambda r:r['year'])
    change=None
    if len(annual)==3:
        first,last=(Decimal(r['values']['netProfit']) if r['values']['netProfit'] else None for r in (annual[0],annual[-1]))
        if first is not None and last is not None and first>0:
            with localcontext() as ctx:
                ctx.prec=50;change=format(((last/first-1)*100).quantize(Decimal('0.000000000001')),'f')
    return {'kind':'financial_summary','source_item_id':ref['item_id'],'source_revision_id':ref['source_revision_id'],
        'report_rows':len(rows),'periods':[by_period[k] for k in sorted(by_period)],
        'annual_net_profit_field_change_pct':change,
        'meaning':'供应商同名字段的描述比较；字段口径待核验，不是标准财务指标或投资评分',
        'standard_metrics_eligible':False,'missing_data':GAPS,'evidence':[ref]}


def import_snapshots(db,workspace_id,snapshots,actor_id=None):
    from app.services.data_mode import fixture_mode
    actual=db.execute(text('SELECT current_database(),inet_server_addr()::text')).one()
    if actual[0]!='vip_v0001_local' and not (actual[0]=='vip_v0001_test' and fixture_mode()):raise SourceError('UNAPPROVED_DB')
    if actual[1] not in ('127.0.0.1/32','::1/128'):raise SourceError('NONLOCAL_DATABASE')
    if not 1<=len(snapshots)<=2:raise SourceError('FINANCIAL_CAPTURE_BOUND_EXCEEDED')
    normalized=[validate(s['payload']) for s in snapshots]
    if sum(map(len,normalized))>100 or len({s['payload']['code'] for s in snapshots})!=len(snapshots):raise SourceError('FINANCIAL_CAPTURE_BOUND_EXCEEDED')
    key='baostock-a-financial'
    db.execute(select(func.pg_advisory_xact_lock(int(digest({'source':key})[:15],16))))
    source=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key==key))
    if source and json.loads(source.policy_json).get('revoked'):raise SourceError('SOURCE_REVOKED')
    if source is None:
        source=SourceRegistry(source_key=key,name='BaoStock免费财务指标',policy_json=canonical(FINANCIAL_POLICY));db.add(source);db.flush()
    run=IngestionRun(workspace_id=workspace_id,source_key=key,status='running',note='three complete fiscal years and latest half-year; raw provider semantics')
    db.add(run);db.flush();entries=[]
    for snapshot,rows in zip(snapshots,normalized):
        payload=snapshot['payload'];name,ticker=TARGETS[payload['code']]
        company=db.scalar(select(Company).where(Company.name==name))
        security=db.scalar(select(Security).where(Security.ticker==ticker,Security.market=='CN_A'))
        if company is None or security is None or security.company_id!=company.id or security.currency!='CNY':raise SourceError('REGISTERED_IDENTITY_MISMATCH')
        entry_key=payload['code']+':'+str(date.fromisoformat(payload['as_of']).year)
        item=db.scalar(select(InformationItem).where(InformationItem.workspace_id==workspace_id,InformationItem.source_id==source.id,InformationItem.entry_key==entry_key).with_for_update())
        if item is None:
            item=InformationItem(workspace_id=workspace_id,source_id=source.id,entry_key=entry_key,title=name+'｜三年真实财务指标',content_kind='dataset');db.add(item);db.flush()
        lines=[]
        for report in payload['reports']:
            lines.append(f"{report['year']} Q{report['quarter']} / {report['kind']}")
            lines.append(','.join(report['fields']))
            lines.extend(','.join(values) for values in report['rows'])
            if not report['rows']:lines.append('NO_DATA（供应商未返回该报告）')
        item.summary_text=f"{name}，{len(rows)}条真实财务指标记录；含三个完整年度及最新中期/比较期。不是完整财报；标准指标口径仍待补齐。"
        item.publication_json=canonical({'date':None,'precision':'unknown','meaning':'多报告数据集无单一出版日期；各行pubDate保留提供商披露日'})
        item.reading_metadata_json=canonical({'data_mode':'real_public','material_type':'financial_metrics','license':FINANCIAL_POLICY['license'],
            'attribution':'BaoStock 0.9.4 public financial API','source_observed_at':payload['observed_at'],'raw_hash':snapshot['hash'],
            'change_notice':'原始字段保留，空值不是0；单位/币种/口径未推断；只在本地比较，不外传','normalization_status':'unsupported_standard_metrics'})
        item.body_state='available';item.body_url=None
        revision=observe(db,item,{'readable_text':'\n'.join(lines),'raw_capture':{k:v for k,v in payload.items() if k!='observed_at'},'source_policy':FINANCIAL_POLICY})
        if not db.scalar(select(ItemCompanyLink.id).where(ItemCompanyLink.item_id==item.id,ItemCompanyLink.company_id==company.id)):
            db.add(ItemCompanyLink(item_id=item.id,company_id=company.id,status='accepted',label_text=name,relevance=1,confidence=1))
        evidence={'synthetic':False,'source_revision_id':revision.id,'hash':revision.content_hash,'item_id':item.id,'locator':'raw_capture.reports','issuer_original':False}
        observation={'provider':'baostock','reports':rows,'standard_metrics_eligible':False,'missing_data':GAPS,'evidence':[evidence]}
        h=digest(observation)
        # input_key includes identity because the unique input constraint is workspace-wide.
        key_for_company='financial_observations:'+ticker
        if not db.scalar(select(ResearchInput.id).where(ResearchInput.workspace_id==workspace_id,ResearchInput.input_key==key_for_company,ResearchInput.content_hash==h)):
            at=datetime.fromisoformat(payload['observed_at'])
            db.add(ResearchInput(workspace_id=workspace_id,company_id=company.id,input_key=key_for_company,kind='financial_observations',payload_json=canonical(observation),content_hash=h,effective_at=at,published_at=at,synthetic=False))
        entries.append({'item_id':item.id,'revision_id':revision.id,'ticker':ticker,'report_rows':len(rows),'raw_hash':snapshot['hash'],'standard_metrics_eligible':False})
    run.status='completed';run.input_manifest_hash=digest([s['hash'] for s in snapshots]);run.output_json=canonical({'entries':entries,'mode':'real_public','external_model':False})
    record(db,workspace_id,actor_id,'ingestion.financial_observations_completed','ingestion_run',run.id,{'entries':len(entries),'manifest_hash':run.input_manifest_hash})
    db.flush();return run
