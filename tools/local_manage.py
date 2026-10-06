"""Scoped local processes and DB operations; no global kill/reset."""
import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BACKEND=ROOT/'backend';PYTHON=BACKEND/'.venv/bin/python';RUNTIME=ROOT/'.runtime'
sys.path.insert(0,str(BACKEND))


def database(test=False):
    from app.config import get_settings
    from sqlalchemy import create_engine,text
    from sqlalchemy.engine import make_url
    url=make_url(get_settings().db_url)
    name='vip_v0001_test' if test else 'vip_v0001_local'
    if test: url=url.set(database=name)
    if url.host not in ('127.0.0.1','localhost') or url.database!=name:
        raise SystemExit('Refusing unapproved DB target')
    with create_engine(url).connect() as c:
        actual=c.execute(text('SELECT current_database(),inet_server_addr()::text,inet_server_port()')).one()
        if actual[0]!=name or actual[1] not in ('127.0.0.1/32','::1/128'):
            raise SystemExit('Actual database/server mismatch')
        if test and c.execute(text("SELECT to_regclass('public.source_registry')")).scalar():
            if any(k!='local-fixture' for k in c.execute(text('SELECT source_key FROM source_registry')).scalars()):
                raise SystemExit('Non-synthetic test sources; refusing write')
    env=os.environ.copy();env['VIP_DB_URL']=url.render_as_string(hide_password=False)
    return url,env


def migrate(test=False):
    url,env=database(test)
    if not test:
        directory=ROOT/'local-data/backups';directory.mkdir(parents=True,exist_ok=True)
        output=directory/('pre-repair-'+time.strftime('%Y%m%d-%H%M%S')+'.dump')
        pg_env=env.copy();pg_env['PGPASSWORD']=url.password or ''
        subprocess.run(['pg_dump','-h',url.host,'-p',str(url.port or 5432),'-U',url.username,'-d',url.database,'-Fc','-f',str(output)],env=pg_env,check=True)
        if output.stat().st_size<100: raise SystemExit('Backup missing or invalid')
        subprocess.run(['pg_restore','--list',str(output)],stdout=subprocess.DEVNULL,check=True)
        print('Verified recoverable backup:',output)
    if test:
        # Explicit migration exercise resets only this verified disposable DB.
        from sqlalchemy import create_engine,text
        import app.models
        from app.db import Base
        test_engine=create_engine(url)
        Base.metadata.drop_all(test_engine)
        with test_engine.begin() as c:
            c.execute(text('DROP TABLE IF EXISTS alembic_version'))
    subprocess.run([str(BACKEND/'.venv/bin/alembic'),'upgrade','head'],cwd=BACKEND,env=env,check=True)
    if test:
        subprocess.run([str(BACKEND/'.venv/bin/alembic'),'downgrade','0007_collab'],cwd=BACKEND,env=env,check=True)
        subprocess.run([str(BACKEND/'.venv/bin/alembic'),'upgrade','head'],cwd=BACKEND,env=env,check=True)


def start(api_only=False):
    RUNTIME.mkdir(exist_ok=True)
    pidfile=RUNTIME/'processes.json'
    if pidfile.exists(): raise SystemExit('Process state exists; use status/stop first')
    port=int(os.environ.get('VIP_HTTP_PORT','8765'))
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1',port))==0:
            if 'VIP_HTTP_PORT' in os.environ: raise SystemExit('Requested port in use; existing process left untouched')
            port=8766
            with socket.socket() as alt:
                if alt.connect_ex(('127.0.0.1',port))==0: raise SystemExit('Both local ports in use; existing processes untouched')
            print('Port 8765 belongs to an existing process; using 8766')
    commands=[[str(PYTHON),'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],[str(PYTHON),'-m','app.worker']]
    if api_only: commands=commands[:1]
    processes=[]
    for index,cmd in enumerate(commands):
        log=open(RUNTIME/('api.log' if index==0 else 'worker.log'),'ab')
        p=subprocess.Popen(cmd,cwd=BACKEND,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        time.sleep(.3)
        if p.poll() is not None:
            for existing in processes: os.kill(existing['pid'],signal.SIGTERM)
            raise SystemExit('Process failed to start; inspect .runtime logs')
        signature=subprocess.check_output(['ps','-p',str(p.pid),'-o','lstart=,command='],text=True).strip()
        processes.append({'pid':p.pid,'signature':signature,'port':port})
    from urllib.request import urlopen
    healthy=False
    for _ in range(20):
        try:
            with urlopen(f'http://127.0.0.1:{port}/api',timeout=1) as response:
                healthy=json.loads(response.read()).get('name')=='value-investment-platform'
            if healthy: break
        except OSError: time.sleep(.2)
    if not healthy:
        for process in processes:
            try: os.kill(process['pid'],signal.SIGTERM)
            except ProcessLookupError: pass
        raise SystemExit('API did not become ready; inspect local logs')
    pidfile.write_text(json.dumps(processes))
    print('Started this project '+('API only' if api_only else 'API/worker')+':',[p['pid'] for p in processes],f'http://127.0.0.1:{port}')


def stop():
    pidfile=RUNTIME/'processes.json'
    if not pidfile.exists(): print('No managed project processes');return
    for process in json.loads(pidfile.read_text()):
        try:
            signature=subprocess.check_output(['ps','-p',str(process['pid']),'-o','lstart=,command='],text=True).strip()
        except subprocess.CalledProcessError: continue
        if signature!=process['signature']: raise SystemExit('PID reused/changed; refusing to signal')
        os.kill(process['pid'],signal.SIGTERM)
        for _ in range(30):
            try:
                current=subprocess.check_output(['ps','-p',str(process['pid']),'-o','lstart=,command='],text=True).strip()
            except subprocess.CalledProcessError:
                break
            if current!=process['signature']: break
            time.sleep(.1)
        else:
            raise SystemExit('Project process is still stopping; PID state retained')
    pidfile.unlink()
    print('Stopped only verified project PIDs')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['start','start-api','stop','migrate','migrate-test','seed-test'])
    args=parser.parse_args()
    if args.action=='start':start()
    elif args.action=='start-api':start(api_only=True)
    elif args.action=='stop':stop()
    elif args.action=='seed-test':
        _,env=database(True);env['VIP_DEMO_MODE']='true'
        subprocess.run([str(PYTHON),'scripts_seed.py'],cwd=BACKEND,env=env,check=True)
    else:migrate(args.action=='migrate-test')
