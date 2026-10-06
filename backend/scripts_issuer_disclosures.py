"""Explicit local PDF verification before an optional append-only import."""
import argparse,hashlib,json
from pathlib import Path
from pypdf import PdfReader
from app.db import SessionLocal
from app.services.issuer_disclosures import validate,import_snapshot

def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--workspace',required=True);p.add_argument('--write',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parents[1]/'raw-data/cninfo-announcements'
    path=Path(a.snapshot).resolve()
    if path.parent!=root.resolve() or path.stat().st_size>1000000:raise SystemExit('公告快照超出本机范围')
    s=json.loads(path.read_text());validate(s)
    key=s['key']
    if not __import__('re').fullmatch('[A-Za-z0-9_-]{1,80}',key):raise SystemExit('原件标识不合法')
    pdf=root/(key+'.pdf')
    if pdf.stat().st_size>5000000 or hashlib.sha256(pdf.read_bytes()).hexdigest()!=s['pdf_sha256']:raise SystemExit('公告PDF hash不匹配')
    if s.get('text_parser')=='pdfplumber_0.11.9':
        import pdfplumber
        with pdfplumber.open(pdf) as reader:
            matched=len(reader.pages)==s['page_count'] and all(reader.pages[p['number']-1].extract_text()==p['text'] for p in s['pages'])
    else:
        reader=PdfReader(pdf)
        matched=len(reader.pages)==s['page_count'] and all(reader.pages[p['number']-1].extract_text(extraction_mode='layout')==p['text'] for p in s['pages'])
    if not matched:raise SystemExit('公告原文页不匹配')
    if not a.write:print(json.dumps({'validated':True,'written':False}));return
    with SessionLocal() as db:
        result=import_snapshot(db,a.workspace,s);db.commit();print(json.dumps(result))

if __name__=='__main__':main()
