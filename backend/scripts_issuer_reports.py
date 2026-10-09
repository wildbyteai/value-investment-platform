"""Import a bounded locally verified PDF excerpt bundle, never download on start."""
import argparse,json,hashlib
from pathlib import Path
from pypdf import PdfReader
from app.db import SessionLocal
from app.domains.companies.issuer_reports import validate,import_bundle
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--workspace',required=True);p.add_argument('--write',action='store_true');a=p.parse_args()
    path=Path(a.snapshot).resolve();directory=(ROOT/'raw-data/cninfo-reports').resolve()
    if path.parent!=directory or path.stat().st_size>1500000:raise SystemExit('仅允许有界本机报告快照')
    bundle=json.loads(path.read_text());validate(bundle)
    for doc in bundle['documents']:
        pdf=(directory/(doc['key']+'.pdf')).resolve()
        if pdf.parent!=directory or not pdf.is_file() or pdf.stat().st_size>30000000 or hashlib.sha256(pdf.read_bytes()).hexdigest()!=doc['pdf_sha256']:raise SystemExit('本机原PDF hash不匹配')
        reader=PdfReader(pdf)
        if len(reader.pages)!=doc['page_count'] or any(reader.pages[page['number']-1].extract_text(extraction_mode='layout')!=page['text'] for page in doc['pages']):raise SystemExit('PDF原始页摘录不匹配')
    if not a.write:print(json.dumps({'validated':True,'written':False,'facts':len(bundle['facts'])}));return
    with SessionLocal() as db:
        result=import_bundle(db,a.workspace,bundle);db.commit();print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
