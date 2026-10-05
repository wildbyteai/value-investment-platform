"""Explicit free local financial capture/import; no normal-start network access."""
import argparse
import hashlib
import json
from pathlib import Path
from sqlalchemy import select
from app.db import SessionLocal
from app.models.identity import Workspace
from app.models.intake import InformationItem
from app.services.data_mode import real_item
from app.services.baostock_financial import ROOT,capture,validate,import_snapshots

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--capture',action='store_true')
    parser.add_argument('--capture-only',action='store_true')
    parser.add_argument('--snapshot',action='append',default=[])
    args=parser.parse_args()
    if args.capture==bool(args.snapshot) or (args.capture_only and not args.capture):raise SystemExit('Choose --capture [--capture-only] or explicit --snapshot files')
    snapshots=[]
    if args.capture:snapshots=capture()
    else:
        directory=(ROOT/'raw-data/baostock-financial').resolve()
        for filename in args.snapshot:
            path=Path(filename).resolve()
            if path.parent!=directory or path.suffix!='.json' or path.stat().st_size>2_000_000:raise SystemExit('Only bounded project financial snapshots accepted')
            raw=path.read_bytes();payload=json.loads(raw);validate(payload)
            snapshots.append({'path':str(path),'hash':hashlib.sha256(raw).hexdigest(),'payload':payload})
    if args.capture_only:
        print(json.dumps([{'path':s['path'],'hash':s['hash'],'rows':len(validate(s['payload']))} for s in snapshots],ensure_ascii=False))
    else:
        with SessionLocal() as db:
            ws=next((w for w in db.scalars(select(Workspace)).all() if any(real_item(db,it,w.id) for it in db.scalars(select(InformationItem).where(InformationItem.workspace_id==w.id)).all())),None)
            if ws is None:raise SystemExit('Initialize real company research first; no synthetic seed here')
            run=import_snapshots(db,ws.id,snapshots);db.commit()
            print(json.dumps({'run_id':run.id,'status':run.status,'results':json.loads(run.output_json)},ensure_ascii=False))
