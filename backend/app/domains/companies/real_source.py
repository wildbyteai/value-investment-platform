"""Bounded, opt-in Wikimedia text ingestion. No images or external model calls."""
from app.core.paths import REPO_ROOT
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from sqlalchemy import select, text
from app.models.company import Company, Security, ItemCompanyLink
from app.models.intake import SourceRegistry, InformationItem, ItemSourceRef
from app.models.audit import IngestionRun
from app.domains.platform.transactions import canonical, digest, record
from app.domains.news.item_history import observe

ROOT=REPO_ROOT
RAW_DIR=ROOT/'raw-data'
POLICY={'license':'CC-BY-SA-4.0','license_url':'https://creativecommons.org/licenses/by-sa/4.0/',
        'basis':'https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use#7._Licensing_of_Content',
        'fetch':'Wikimedia public API, max 2 revision requests per run, no media',
        'store':'local attributed text snapshot','analyze':'local deterministic text conversion only',
        'export':'disabled; reuse requires attribution, change notice and share-alike',
        'external_model':False,'text_only':True}
TARGETS=[{'title':'BYD Company','name':'比亚迪股份有限公司','securities':[('CN_A','002594.SZ','CNY'),('HK','01211.HK','HKD')]},
         {'title':'Gree Electric','name':'珠海格力电器股份有限公司','securities':[('CN_A','000651.SZ','CNY')]}]


def source_enabled(): return os.environ.get('VIP_REAL_SOURCE_ENABLED')=='1'


def record_raw(payload, label):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',label): raise ValueError('Invalid raw label')
    RAW_DIR.mkdir(parents=True,exist_ok=True)
    content_hash=hashlib.sha256(payload).hexdigest()
    path=RAW_DIR/f'{label}-{content_hash}.json'
    if not path.exists(): path.write_bytes(payload)
    return {'sha256':content_hash,'bytes':len(payload),'stored':True,'path':str(path)}


def request_revision(title, end):
    query={'action':'query','format':'json','prop':'revisions','titles':title,'rvprop':'timestamp|ids|content',
           'rvslots':'main','rvstart':end.isoformat(),'rvend':(end-timedelta(days=30)).isoformat(),'rvlimit':1}
    url='https://en.wikipedia.org/w/api.php?'+urlencode(query)
    request=Request(url,headers={'User-Agent':'ValueInvestmentLocalResearch/0.0.1 (bounded text reader)'})
    with urlopen(request,timeout=25) as response:
        raw=response.read(2_000_001)
    if len(raw)>2_000_000: raise ValueError('Source payload exceeds 2 MB bound')
    return json.loads(raw),raw,url


def readable_text(raw):
    value=re.sub(r'<!--.*?-->|<ref\b[^>]*>.*?</ref>|<ref\b[^>]*/>', '',raw,flags=re.S)
    for _ in range(30):
        clean=re.sub(r'\{\{[^{}]*\}\}', '',value)
        if clean==value: break
        value=clean
    value=re.sub(r'\[\[(?:File|Image|Category):[^\]]*\]\]', '',value,flags=re.I)
    value=re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]',r'\2',value)
    value=re.sub(r'\[\[([^\]]+)\]\]',r'\1',value)
    value=re.sub(r"'{2,}",'',value)
    value=re.sub(r'<[^>]*>','',value)
    return value.strip()


def import_public(db,workspace_id,actor_id=None,fetch=request_revision,end=None):
    if not source_enabled(): raise ValueError('Real source is disabled; explicit enable required')
    actual=db.execute(text('SELECT current_database(), inet_server_addr()::text')).one()
    if actual[0]!='vip_v0001_local' or actual[1] not in ('127.0.0.1/32','::1/128'):
        raise ValueError('Real import requires verified project local database')
    end=end or datetime.now(timezone.utc)
    source=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key=='wikimedia-en-text'))
    if source is None:
        source=SourceRegistry(source_key='wikimedia-en-text',name='Wikipedia 英文百科（真实公开资料）',policy_json=canonical(POLICY))
        db.add(source);db.flush()
    if json.loads(source.policy_json).get('revoked'): raise ValueError('Source rights revoked')
    run=IngestionRun(workspace_id=workspace_id,source_key=source.source_key,status='running',note='2 companies, 30 days, text only')
    db.add(run);db.flush();results=[]
    for target in TARGETS:
        try:
            # Each item has its own transaction savepoint; no successful row is
            # discarded because the second request fails. No blind retries.
            with db.begin_nested():
                payload,raw,url=fetch(target['title'],end)
                if payload.get('error'): raise ValueError(payload['error']['code'])
                page=next(iter(payload['query']['pages'].values()));revisions=page.get('revisions',[])
                if not revisions: raise ValueError('NO_REVISION_WITHIN_30_DAYS')
                rev=revisions[0];published=datetime.fromisoformat(rev['timestamp'].replace('Z','+00:00'))
                if not end-timedelta(days=30)<=published<=end: raise ValueError('REVISION_OUTSIDE_WINDOW')
                if page['title']!=target['title']: raise ValueError('Unexpected identity')
                original=rev['slots']['main']['*'];body=readable_text(original)
                raw_info=record_raw(raw,target['title'].replace(' ','_'))
                company=db.scalar(select(Company).where(Company.name==target['name']))
                if company is None:
                    company=Company(name=target['name'],industry_key='manufacturing');db.add(company);db.flush()
                for market,ticker,currency in target['securities']:
                    if not db.scalar(select(Security).where(Security.company_id==company.id,Security.ticker==ticker)):
                        db.add(Security(company_id=company.id,market=market,ticker=ticker,currency=currency))
                entry_key=str(rev['revid'])
                item=db.scalar(select(InformationItem).where(InformationItem.workspace_id==workspace_id,
                           InformationItem.source_id==source.id,InformationItem.entry_key==entry_key).with_for_update())
                if item is None:
                    item=InformationItem(workspace_id=workspace_id,source_id=source.id,entry_key=entry_key,
                        title=target['name']+'｜真实公司资料',content_kind='article')
                    db.add(item);db.flush()
                revision_url=f'https://en.wikipedia.org/w/index.php?oldid={rev["revid"]}'
                item.summary_text=body[:600]
                item.publication_json=canonical({'date':published.date().isoformat(),'timestamp':rev['timestamp'],'precision':'instant',
                                                 'meaning':'百科修订时间，不是公司事件发生时间'})
                item.reading_metadata_json=canonical({'material_type':'company_profile','data_mode':'real_public',
                    'attribution':revision_url,'history_url':'https://en.wikipedia.org/w/index.php?title='+target['title'].replace(' ','_')+'&action=history',
                    'license':'CC-BY-SA-4.0','change_notice':'摘要截取并移除Wiki格式；非投资判断'})
                item.body_state='available';item.body_url=revision_url
                observe(db,item,{'original_text':original,'readable_text':body,'source_url':revision_url,
                    'revision_id':rev['revid'],'text_hash':hashlib.sha256(original.encode()).hexdigest(),'published':rev['timestamp'],
                    'license':POLICY})
                if not db.scalar(select(ItemCompanyLink).where(ItemCompanyLink.item_id==item.id,ItemCompanyLink.company_id==company.id)):
                    db.add(ItemCompanyLink(item_id=item.id,company_id=company.id,label_text=company.name,
                        status='accepted',relevance=1,confidence=1))
                results.append({'company':target['name'],'item_id':item.id,'revision_id':rev['revid'],'publication':rev['timestamp'],
                                'hash':raw_info['sha256'],'bytes':len(raw),'status':'imported','url':revision_url})
        except (ValueError,KeyError,StopIteration,OSError) as exc:
            results.append({'company':target['name'],'status':'failed','reason':type(exc).__name__+':'+str(exc)[:160]})
    run.status='completed' if all(r['status']=='imported' for r in results) else 'partial'
    run.input_manifest_hash=digest({'targets':[t['title'] for t in TARGETS],'end':end.isoformat(),'window_days':30,'policy':POLICY})
    run.output_json=canonical({'entries':results,'export':False,'model_called':False})
    record(db,workspace_id,actor_id,'ingestion.public_completed','ingestion_run',run.id,{'status':run.status,'entries':len(results)})
    db.flush()
    return run
