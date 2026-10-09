"""Explicit real daily import; no startup fetch or historic backfill."""
import argparse
import json
import hashlib
from pathlib import Path
from sqlalchemy import select
from app.db import SessionLocal
from app.models.identity import Workspace
from app.models.intake import InformationItem, SourceRegistry
from app.domains.market_data.baostock_source import capture_daily, import_snapshots, ROOT, validate
from app.domains.platform.data_mode import real_item

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--capture',action='store_true')
    parser.add_argument('--snapshot',action='append',default=[])
    args=parser.parse_args()
    if args.capture==bool(args.snapshot):raise SystemExit('Choose either --capture or explicit --snapshot files')
    snapshots=[]
    if args.capture:snapshots=capture_daily()
    else:
        root=(ROOT/'raw-data/baostock').resolve()
        for filename in args.snapshot:
            path=Path(filename).resolve()
            if path.parent!=root or path.suffix!='.json' or path.stat().st_size>2_000_000:raise SystemExit('Only bounded project BaoStock snapshots are accepted')
            raw=path.read_bytes();payload=json.loads(raw);validate(payload)
            snapshots.append({'path':str(path),'hash':hashlib.sha256(raw).hexdigest(),'payload':payload})
    with SessionLocal() as db:
        workspaces=db.scalars(select(Workspace)).all()
        ws=next((w for w in workspaces if any(real_item(db,it,w.id) for it in db.scalars(select(InformationItem).where(InformationItem.workspace_id==w.id)).all())),None)
        if ws is None:raise SystemExit('Initialize real company research first; fixture seed is prohibited here')
        run=import_snapshots(db,ws.id,snapshots);db.commit()
        print(json.dumps({'run_id':run.id,'status':run.status,'results':json.loads(run.output_json)},ensure_ascii=False))
