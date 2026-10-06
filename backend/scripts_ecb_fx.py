"""Explicit capture or replay; default validates without database writes."""
import argparse,json
from datetime import date
from pathlib import Path
from app.services.ecb_fx import capture,validate,import_snapshot
from app.db import SessionLocal

def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--capture',action='store_true');group.add_argument('--snapshot')
    parser.add_argument('--start',type=date.fromisoformat);parser.add_argument('--end',type=date.fromisoformat)
    parser.add_argument('--workspace');parser.add_argument('--company',action='append');parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    if args.capture:
        if not args.start or not args.end:parser.error('capture requires --start and --end')
        path,snapshot=capture(args.start,args.end,Path(__file__).resolve().parents[1]/'raw-data/ecb')
    else:path=Path(args.snapshot);snapshot=json.loads(path.read_text())
    rows=validate(snapshot);result={'validated':True,'written':False,'days':len(rows),'snapshot':str(path)}
    if args.write:
        if not args.workspace or not args.company:parser.error('write requires --workspace and --company')
        with SessionLocal() as db:result.update(import_snapshot(db,args.workspace,args.company,snapshot));db.commit()
        result['written']=True
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
