"""Opt-in internal sealing; never automatically enabled by dev/start."""
import argparse,json
from sqlalchemy import text
from app.db import SessionLocal
from app.domains.strategy.sealing_service import WorkerContext,install_artifacts,schedule
from app.domains.strategy.seal_worker import run_one


def main():
    parser=argparse.ArgumentParser(description='正式封存内部worker，仅处理指定已批准挂牌/日历')
    parser.add_argument('--prepare-artifacts',action='store_true')
    parser.add_argument('--workspace');parser.add_argument('--release');parser.add_argument('--security');parser.add_argument('--session-id')
    parser.add_argument('--seal-id');args=parser.parse_args()
    context=WorkerContext('local-strategy-seal',frozenset({'strategy.seal'}))
    with SessionLocal() as db:
        actual=db.execute(text('SELECT current_database(),inet_server_addr()::text')).one()
        if actual[0] not in ('vip_v0001_local','vip_v0001_test') or actual[1] not in ('127.0.0.1/32','::1/128'):raise SystemExit('Refusing unverified project database/server')
        if not db.execute(text("SELECT to_regclass('evaluation_seal')")).scalar():raise SystemExit('Formal sealing migration is not installed')
        if args.prepare_artifacts:
            install_artifacts(db,context);db.commit();print(json.dumps({'prepared':True}));return
        seal_id=args.seal_id
        if not seal_id:
            if not all((args.workspace,args.release,args.security,args.session_id)):parser.error('需要固定workspace/release/security/批准session-id或既有seal-id')
            row=schedule(db,context,args.workspace,args.release,args.security,args.session_id);db.commit();seal_id=row.id
    print(json.dumps(run_one(SessionLocal,context,seal_id),ensure_ascii=False))

if __name__=='__main__':main()
