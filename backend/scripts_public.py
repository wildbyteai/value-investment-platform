"""Explicit bounded real import; never part of server startup or synthetic seed."""
import argparse
import json
import os
from sqlalchemy import select
from app.db import SessionLocal
from app.models.identity import Workspace
from app.domains.companies.real_source import import_public

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--enable-wikimedia',action='store_true',required=True)
    args=parser.parse_args()
    os.environ['VIP_REAL_SOURCE_ENABLED']='1'
    with SessionLocal() as db:
        workspace=db.scalar(select(Workspace).where(Workspace.name=='演示研究组织（合成数据）'))
        if not workspace: raise SystemExit('Seed mock identities before import')
        run=import_public(db,workspace.id)
        db.commit()
        print(json.dumps({'run_id':run.id,'status':run.status,'results':json.loads(run.output_json)},ensure_ascii=False))
        if run.status!='completed': raise SystemExit(1)
