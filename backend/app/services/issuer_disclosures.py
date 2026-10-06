"""Finite issuer announcements with original local PDF evidence; no quote inference."""
import json
import re
from datetime import date, datetime, timezone
from urllib.parse import urlsplit
from sqlalchemy import select, text, func
from app.models.company import Company, Security, ItemCompanyLink
from app.models.intake import InformationItem, SourceRegistry
from app.services.issuer_reports import TARGETS, SECURITY_CURRENCIES, POLICY
from app.services.transactions import canonical, digest, record
from app.services.item_history import observe

SOURCE_POLICY = {**POLICY, 'evidence_category': 'issuer_original'}
ISSUER_ALIASES = {'09969.HK': ('诺诚健华医药有限公司','諾誠健華醫藥有限公司')}


def validate(snapshot):
    ticker=snapshot.get('ticker');issuer=snapshot.get('issuer')
    if ticker not in TARGETS or issuer!=TARGETS[ticker]:raise ValueError('公告发行人不匹配')
    url=urlsplit(snapshot['url'])
    if url.scheme!='https' or url.netloc!='static.cninfo.com.cn' or not re.fullmatch(r'/finalpage/\d{4}-\d{2}-\d{2}/\d+\.PDF',url.path):raise ValueError('公告来源不匹配')
    observed=datetime.fromisoformat(snapshot['observed_at']);day=date.fromisoformat(snapshot['disclosure_date'])
    if observed.tzinfo is None or observed>datetime.now(timezone.utc) or day>observed.date():raise ValueError('公告时间不合法')
    if not re.fullmatch('[0-9a-f]{64}',snapshot['pdf_sha256']):raise ValueError('公告PDF hash缺失')
    pages=snapshot['pages'];numbers=[p['number'] for p in pages]
    if not 1<=snapshot['page_count']<=30 or not pages or len(set(numbers))!=len(numbers) or any(type(n)!=int or not 1<=n<=snapshot['page_count'] for n in numbers):raise ValueError('公告页数或页码不合法')
    if sum(len(p['text']) for p in pages)>200000 or any(not isinstance(p['text'],str) or not p['text'].strip() for p in pages):raise ValueError('公告原文不可读或超限')
    if snapshot.get('text_parser','pypdf_layout') not in ('pypdf_layout','pdfplumber_0.11.9'):raise ValueError('公告解析版本不支持')
    aliases=ISSUER_ALIASES.get(ticker,(issuer,))
    if not any(name in ''.join(p['text'].split()) for p in pages for name in aliases):raise ValueError('公告正文发行人无法核验')
    if not isinstance(snapshot.get('title'),str) or not 1<=len(snapshot['title'])<=180:raise ValueError('公告标题缺失')


def import_snapshot(db,workspace_id,snapshot):
    validate(snapshot)
    from app.services import data_mode
    actual=db.execute(text('SELECT current_database(),inet_server_addr()::text')).one()
    if actual[0]!='vip_v0001_local' and not (actual[0]=='vip_v0001_test' and data_mode.fixture_mode()):raise ValueError('未核验公告数据库')
    if actual[1] not in ('127.0.0.1/32','::1/128'):raise ValueError('未核验本机公告数据库')
    company=db.scalar(select(Company).where(Company.name==snapshot['issuer']))
    if not company:raise ValueError('公告公司未登记')
    data_mode.require_company(db,company.id,workspace_id)
    if not db.scalar(select(Security.id).where(Security.company_id==company.id,Security.ticker==snapshot['ticker'],Security.currency==SECURITY_CURRENCIES[snapshot['ticker']])):raise ValueError('公告证券归属不匹配')
    source_key='cninfo-bounded-issuer-disclosures'
    db.execute(select(func.pg_advisory_xact_lock(int(digest({'source':source_key})[:15],16))))
    source=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key==source_key))
    if source and json.loads(source.policy_json)!=SOURCE_POLICY:raise ValueError('公告来源政策已改变或撤销')
    if not source:
        source=SourceRegistry(source_key=source_key,name='发行人公开公告｜本机个人研究',policy_json=canonical(SOURCE_POLICY));db.add(source);db.flush()
    item=db.scalar(select(InformationItem).where(InformationItem.workspace_id==workspace_id,InformationItem.source_id==source.id,InformationItem.entry_key==snapshot['url']).with_for_update())
    if not item:
        item=InformationItem(workspace_id=workspace_id,source_id=source.id,entry_key=snapshot['url'],title=snapshot['title'],content_kind='article');db.add(item);db.flush()
    previous=item.current_revision_id
    item.title=snapshot['title'];item.summary_text='发行人原始公告；保留披露日期与固定原文，不将公告自动转换为评分或行情。'
    item.publication_json=canonical({'date':snapshot['disclosure_date'],'precision':'day','meaning':'来源披露目录日期，确切发布时间未核验'})
    item.reading_metadata_json=canonical({'data_mode':'real_public','material_type':'issuer_disclosure','attribution':snapshot['issuer']+'；巨潮公开披露','license':SOURCE_POLICY['license'],'source_observed_at':snapshot['observed_at']})
    item.body_state='available';item.body_url=snapshot['url']
    content={k:v for k,v in snapshot.items() if k!='observed_at'}
    readable=snapshot['url']+'\n\n'+'\n\n'.join(f"PDF第{p['number']}页\n"+p['text'] for p in snapshot['pages'])
    revision=observe(db,item,{'readable_text':readable,'raw_capture':content,'source_policy':SOURCE_POLICY})
    if not db.scalar(select(ItemCompanyLink.id).where(ItemCompanyLink.item_id==item.id,ItemCompanyLink.company_id==company.id)):
        db.add(ItemCompanyLink(item_id=item.id,company_id=company.id,status='accepted',label_text=company.name,relevance=1,confidence=1));db.flush()
    if previous!=revision.id:record(db,workspace_id,None,'research.issuer_disclosure_imported','information_item',item.id,{'revision_id':revision.id,'pdf_sha256':snapshot['pdf_sha256']})
    return {'item_id':item.id,'revision_id':revision.id,'hash':revision.content_hash,'reused':previous==revision.id}
