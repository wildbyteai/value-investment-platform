"""Bounded reviewed statement excerpts; raw PDFs stay on this machine.

This is original evidence, not a ratio provider or a complete financial input.
Unresolved ordinary-share/obligation bases remain explicit and block scoring.
"""
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
from urllib.parse import urlsplit
from sqlalchemy import select, text, func
from app.models.company import Company, Security, ItemCompanyLink
from app.models.intake import InformationItem, SourceRegistry
from app.models.runtime import ResearchInput
from app.services.item_history import observe
from app.services.transactions import canonical, digest, record
from app.services.original_financials import number, MONEY_UNITS

TARGETS={'002594.SZ':'比亚迪股份有限公司','000651.SZ':'珠海格力电器股份有限公司'}
POLICY={'license':'bounded-public-disclosure-personal-study',
    'basis':'https://www.ncac.gov.cn/xxfb/flfg/flfg_532/202103/t20210309_50530.html',
    'basis_description':'Copyright Law art24 personal study scope assessment; NOT an express platform licence',
    'fetch':'finite named public statutory reports; no continuous or bulk scraping',
    'store':'attributed excerpts in local personal research workspace; original PDF local only',
    'analyze':'local personal deterministic research only','export':'disabled','external_model':False}


def validate(bundle):
    ticker=bundle.get('ticker')
    if ticker not in TARGETS or bundle.get('issuer')!=TARGETS[ticker]:raise ValueError('报告公司身份不匹配')
    docs=bundle.get('documents',[]);facts=bundle.get('facts',[])
    if not 1<=len(docs)<=4 or not 1<=len(facts)<=160:raise ValueError('报告或科目超出有界范围')
    known={};now=datetime.now(timezone.utc)
    for doc in docs:
        key=doc['key'];url=urlsplit(doc['url']);day=date.fromisoformat(doc['disclosure_date'])
        at=datetime.fromisoformat(doc['observed_at'])
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',key) or key in known or url.scheme!='https' or url.netloc!='static.cninfo.com.cn' or not re.fullmatch(r'/finalpage/\d{4}-\d{2}-\d{2}/\d+\.PDF',url.path):raise ValueError('报告来源或标识不匹配')
        if at.tzinfo is None or at>now or day>at.date():raise ValueError('报告取得时间或披露日期不合法')
        if not re.fullmatch('[0-9a-f]{64}',doc['pdf_sha256']) or not 1<=doc['page_count']<=500:raise ValueError('PDF校验信息缺失')
        pages=doc['pages']
        if not pages or len(pages)>40 or sum(len(p['text']) for p in pages)>200000:raise ValueError('摘录超出有界范围')
        indices=[p['number'] for p in pages]
        if len(set(indices))!=len(indices) or any(type(n)!=int or not 1<=n<=doc['page_count'] for n in indices):raise ValueError('报告页码不合法')
        if not all(isinstance(p['text'],str) and p['text'] for p in pages):raise ValueError('报告摘录为空')
        if not any(bundle['issuer'] in p['text'].replace(' ','') for p in pages):raise ValueError('PDF正文发行人不匹配')
        unit_page=next((p['text'].replace(' ','') for p in pages if p['number']==doc.get('unit_basis_page')),None)
        marker='千元' if doc.get('money_unit')=='thousand_yuan' else '单位：人民币元' if doc.get('money_unit')=='yuan' and unit_page and '人民币元' in unit_page else '单位：元'
        if not unit_page or doc.get('money_unit') not in ('yuan','thousand_yuan') or marker not in unit_page:raise ValueError('报告单位原文未核验')
        known[key]=doc
    seen=set()
    for row in facts:
        key=(row['key'],row.get('period_start'),row['period_end'])
        if key in seen:raise ValueError('原始科目冲突')
        seen.add(key);end=date.fromisoformat(row['period_end'])
        start=date.fromisoformat(row['period_start']) if row.get('period_start') else None
        doc=known.get(row['document_key'])
        if not doc or end>date.fromisoformat(doc['disclosure_date']) or (start and start>end):raise ValueError('原始科目期间不合法')
        if row.get('reviewed') is not True or row.get('currency')!='CNY' or row.get('statement_scope')!='consolidated':raise ValueError('原始科目单位/范围尚未核对')
        if row['unit'] not in MONEY_UNITS:raise ValueError('原始金额单位不支持')
        if row['unit']!=doc.get('money_unit'):raise ValueError('科目单位与报告单位不匹配')
        number(row['original_value'])
        page=next((p for p in doc['pages'] if p['number']==row['page']),None)
        # Reviewer fixes a source row and column; exact value must occur on that row.
        line=row['original_line']
        if not page or not line or line not in page['text'] or row['original_value'] not in line or row['label'] not in line:raise ValueError('原值或原文行/页定位不匹配')
        pattern=r'-?\d{1,3}(?:,\d{3})+'+(r'\.\d{2}' if row['unit']=='yuan' else '')
        values=re.findall(pattern,line)
        index=row.get('column_index')
        if type(index)!=int or not 0<=index<len(values) or values[index]!=row['original_value']:raise ValueError('原值与选定列不匹配')
        if not row.get('column_label'):raise ValueError('原值列期间缺失')
    if not bundle.get('missing_data'):raise ValueError('未完成普通股/债务/报告义务口径必须明确缺口')
    return known


def analysis(payload, ref):
    by_period={}
    for row in payload['facts']:
        entry=by_period.setdefault(row['period_end'],{'stat_date':row['period_end'],'reports':{},'values':{}})
        doc=next(d for d in payload['documents'] if d['key']==row['document_key'])
        entry['reports'][row['document_key']]={'pub_date':doc['disclosure_date'],
            'locator':f"PDF page {row['page']} / {row['label']} / {row['column_label']}"}
        # Values display in yuan, with raw value/unit/row retained in facts.
        entry['values'][row['key']]=str(number(row['original_value'])*MONEY_UNITS[row['unit']])
    # Only complete matching annual series enter these two independent metrics.
    # Ordinary-share, debt or EBIT gaps do not invent those unrelated fields.
    metrics={};lineage={}
    with localcontext() as context:
        context.prec=50
        ends=sorted(p for p in by_period if p.endswith('-12-31'))
        years=[int(p[:4]) for p in ends]
        if len(ends)==3 and years==list(range(years[0],years[0]+3)) and all({'cfo','consolidated_profit'}<=by_period[p]['values'].keys() for p in ends):
            cash=[Decimal(by_period[p]['values']['cfo']) for p in ends]
            profit=sum(Decimal(by_period[p]['values']['consolidated_profit']) for p in ends)
            if profit>0:metrics['cfo_profit_3y']=format((sum(cash)/profit).quantize(Decimal('0.000000000001')),'f')
            metrics['positive_cfo_year_share_3y']=format((Decimal(sum(v>0 for v in cash))/3).quantize(Decimal('0.000000000001')),'f')
            lineage={'definition':'metric-definitions-v2','periods':ends,'fact_keys':['cfo','consolidated_profit'],'scope':'matching_consolidated_group'}
    return {'kind':'financial_summary','source_item_id':ref['item_id'],'source_revision_id':ref['source_revision_id'],
        'original_statement':True,
        'available_metrics':metrics,'metric_lineage':lineage,
        'report_rows':len(payload['facts']),'periods':[by_period[k] for k in sorted(by_period)],
        'annual_net_profit_field_change_pct':None,'meaning':'发行人合并财务报表原始科目；展示金额已换算人民币元，原值、单位、页码和列期间均保留。资料日期取自来源目录，确切发布时间未核验，系统知识时间为实际入库。尚未完成全部标准口径，不生成完整评分。',
        'standard_metrics_eligible':False,'missing_data':payload['missing_data'],'evidence':[ref]}


def import_bundle(db,workspace_id,bundle):
    validate(bundle)
    from app.services.data_mode import require_company
    actual=db.execute(text('SELECT current_database(),inet_server_addr()::text')).one()
    if actual[0]!='vip_v0001_local' or actual[1] not in ('127.0.0.1/32','::1/128'):raise ValueError('未核验的真实数据库')
    company=db.scalar(select(Company).where(Company.name==bundle['issuer']))
    if not company:raise ValueError('未登记研究公司')
    require_company(db,company.id,workspace_id)
    if not db.scalar(select(Security.id).where(Security.company_id==company.id,Security.ticker==bundle['ticker'],Security.currency=='CNY')):raise ValueError('已登记证券身份不匹配')
    key='cninfo-reviewed-statements'
    db.execute(select(func.pg_advisory_xact_lock(int(digest({'source':key})[:15],16))))
    source=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key==key))
    if source and json.loads(source.policy_json)!=POLICY:raise ValueError('来源政策已变更或撤销，拒绝隐式授权')
    if not source:
        source=SourceRegistry(source_key=key,name='巨潮公开法定报告｜本地个人研究摘录',policy_json=canonical(POLICY));db.add(source);db.flush()
    entry_key=bundle['ticker']+':reviewed-originals'
    item=db.scalar(select(InformationItem).where(InformationItem.workspace_id==workspace_id,InformationItem.source_id==source.id,InformationItem.entry_key==entry_key).with_for_update())
    if not item:
        item=InformationItem(workspace_id=workspace_id,source_id=source.id,entry_key=entry_key,title=bundle['issuer']+'｜三年财报原始科目',content_kind='dataset');db.add(item);db.flush()
    item.summary_text=f"{len(bundle['documents'])}份发行人法定报告、{len(bundle['facts'])}项核对科目；完整口径仍有缺项。"
    item.publication_json=canonical({'date':None,'precision':'unknown','meaning':'各报告披露日逐份保留，仅日期精度，不伪造发布时间'})
    item.reading_metadata_json=canonical({'data_mode':'real_public','material_type':'original_statements','license':POLICY['license'],
        'attribution':bundle['issuer']+'；巨潮资讯公开法定披露','source_observed_at':max(d['observed_at'] for d in bundle['documents']),
        'normalization_status':'reviewed_originals_partial','change_notice':'原文仅本机个人研究；展示换算为元，普通股等未确认口径不猜值'})
    item.body_state='available';item.body_url=None
    content={**bundle,'documents':[{k:v for k,v in d.items() if k!='observed_at'} for d in bundle['documents']]}
    readable='\n\n'.join(d['key']+' | '+d['url']+'\n'+'\n\n'.join(f"PDF第{p['number']}页\n"+p['text'] for p in d['pages']) for d in bundle['documents'])
    revision=observe(db,item,{'readable_text':readable,'raw_capture':{'report_type':'reviewed_original_statements',**content},'source_policy':POLICY})
    if not db.scalar(select(ItemCompanyLink.id).where(ItemCompanyLink.item_id==item.id,ItemCompanyLink.company_id==company.id)):
        db.add(ItemCompanyLink(item_id=item.id,company_id=company.id,status='accepted',label_text=company.name,relevance=1,confidence=1));db.flush()
    ref={'synthetic':False,'source_revision_id':revision.id,'hash':revision.content_hash,'item_id':item.id,'locator':'raw_capture.facts','issuer_original':True}
    observation={**content,'evidence':[ref],'standard_metrics_eligible':False}
    h=digest(observation)
    prior=db.scalar(select(ResearchInput).where(ResearchInput.workspace_id==workspace_id,ResearchInput.input_key=='financial_observations:'+bundle['ticker'],ResearchInput.content_hash==h))
    reused=prior is not None
    if not prior:
        # Actual acquisition date is used conservatively; disclosure dates remain date precision in documents.
        at=max(datetime.fromisoformat(d['observed_at']) for d in bundle['documents'])
        prior=ResearchInput(workspace_id=workspace_id,company_id=company.id,input_key='financial_observations:'+bundle['ticker'],kind='financial_observations',payload_json=canonical(observation),content_hash=h,effective_at=at,published_at=at,synthetic=False)
        db.add(prior);db.flush();record(db,workspace_id,None,'research.issuer_originals_imported','research_input',prior.id,{'hash':h,'facts':len(bundle['facts'])})
    return {'input_id':prior.id,'item_id':item.id,'revision_id':revision.id,'facts':len(bundle['facts']),'reused':reused}
