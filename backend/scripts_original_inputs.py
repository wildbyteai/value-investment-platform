"""Explicit reviewed-original import, no fetching or fabricated missing fields."""
import argparse,json
from pathlib import Path
from sqlalchemy import select,text
from app.db import SessionLocal
from app.models.runtime import ResearchInput
from app.services import data_mode
from app.services.original_financials import normalize as financials
from app.services.hk_market import normalize_quote
from app.services.share_capital import normalize as share_capital, verify_originals
from app.services.transactions import canonical,digest,record
from datetime import datetime,timezone


def main():
    p=argparse.ArgumentParser(description='固定原始科目/港股快照；默认只校验不入库')
    p.add_argument('--snapshot',required=True);p.add_argument('--kind',choices=['financials','hk-price','share-capital'],required=True)
    p.add_argument('--workspace',required=True);p.add_argument('--company',required=True)
    p.add_argument('--write',action='store_true');a=p.parse_args();bundle=json.loads(Path(a.snapshot).read_text())
    payload=financials(bundle) if a.kind=='financials' else share_capital(bundle) if a.kind=='share-capital' else normalize_quote(bundle['quote'],bundle['source_policy'])
    with SessionLocal() as db:
        actual=db.execute(text('SELECT current_database(),inet_server_addr()::text')).one()
        if actual[0]!='vip_v0001_local' or actual[1] not in ('127.0.0.1/32','::1/128'):raise SystemExit('Refusing unverified real-public project database/server')
        data_mode.require_company(db,a.company,a.workspace)
        if not data_mode.real_evidence(db,payload['evidence'],a.workspace,a.company):raise SystemExit('Original revisions/rights/company links are not eligible')
        if a.kind=='share-capital':verify_originals(db,payload)
        if a.kind=='hk-price':
            from app.models.intake import SourceRegistry,InformationItem
            from app.models.runtime import ItemRevision
            for ref in bundle['quote']['evidence']:
                rev=db.get(ItemRevision,ref['source_revision_id']);item=db.get(InformationItem,rev.item_id)
                if json.loads(db.get(SourceRegistry,item.source_id).policy_json)!=bundle['source_policy']:raise SystemExit('Snapshot policy does not match registered source')
        summary={'validated':True,'written':False,'kind':a.kind,'hash':digest(payload),'evidence_count':len(payload['evidence'])}
        if a.write:
            if not db.execute(text("SELECT to_regclass('knowledge_entry')")).scalar():raise SystemExit('Knowledge-clock migration is required before original import')
            published=datetime.fromisoformat(bundle['published_at']);effective=datetime.fromisoformat(bundle['effective_at'])
            if published.tzinfo is None or effective.tzinfo is None:raise SystemExit('Source published/effective timestamps must have time zones')
            if a.kind=='share-capital':
                from zoneinfo import ZoneInfo
                now=datetime.now(timezone.utc)
                if (effective.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()!=payload['shares_as_of'] or
                    effective>now or published>now or published<effective):
                    raise SystemExit('Share balance effective/publication timestamps do not match the reviewed scope')
            key='financials' if a.kind=='financials' else 'share_capital:'+a.company+':'+payload['shares_as_of'] if a.kind=='share-capital' else 'price:'+payload['ticker']
            if a.kind=='share-capital':
                from sqlalchemy import func
                db.execute(select(func.pg_advisory_xact_lock(int(digest({'ws':a.workspace,'key':key})[:15],16))))
            prior=db.scalar(select(ResearchInput).where(ResearchInput.workspace_id==a.workspace,ResearchInput.input_key==key,ResearchInput.content_hash==digest(payload)))
            if prior:summary.update(written=True,input_id=prior.id,reused=True)
            else:
                row=ResearchInput(workspace_id=a.workspace,company_id=a.company,input_key=key,kind='financials' if a.kind=='financials' else 'share_capital' if a.kind=='share-capital' else 'price',payload_json=canonical(payload),content_hash=digest(payload),effective_at=effective,published_at=published,synthetic=False)
                db.add(row);db.flush();record(db,a.workspace,None,'research.original_imported','research_input',row.id,{'kind':a.kind,'hash':row.content_hash});db.commit();summary.update(written=True,input_id=row.id,reused=False)
        print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
