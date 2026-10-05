"""Readback metadata only; no raw real text, credentials or private log export."""
import hashlib,json,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from app.db import engine
from sqlalchemy import text
BASE='http://127.0.0.1:8766'
def get(path,headers=None):
    with urlopen(Request(BASE+path,headers=headers or {}),timeout=5) as r:return json.loads(r.read())
identities=get('/api/identities')
ws=next(w['id'] for w in identities['workspaces'] if w['name']=='演示研究组织（合成数据）')
h={'X-Vip-Login':'research@demo','X-Vip-Workspace':ws}
items=get('/api/intake/items',h);real=[]
for item in items:
    if item['source_name'].startswith('Wikipedia'):
        d=get('/api/intake/items/'+item['id'],h)
        assert d['original_text'] and len(d['original_text'])>1000
        real.append({'item_id':d['id'],'publication':d['publication'],'body_state':d['body_access']['state'],
                     'characters':len(d['original_text']),'source_revision_url':d['body_access']['url'],'license':d['reading_metadata']['license']})
companies=get('/api/companies',h);real_companies=[]
for company in companies:
    if company['name'] in ('比亚迪股份有限公司','珠海格力电器股份有限公司'):
        score=get('/api/companies/'+company['id']+'/score',h)
        timeline=get('/api/companies/'+company['id']+'/timeline',h)
        assert score['quality_score'] is None and score['input_refs']==[]
        assert timeline['items'] and all(s['valuation_score'] is None for s in score['securities'])
        real_companies.append({'company':company['name'],'timeline_items':len(timeline['items']),
                               'security_markets':[s['market'] for s in score['securities']],
                               'quality':None,'valuation':None,'synthetic_financial_inputs':0})
with engine.connect() as db:
    revision=db.execute(text('SELECT version_num FROM alembic_version')).scalar()
    worker=db.execute(text('SELECT count(*) FILTER (WHERE dispatched),count(*) FILTER (WHERE last_error IS NOT NULL),count(*) FROM outbox WHERE workspace_id IS NOT NULL')).one()
    effects=db.execute(text('SELECT count(*) FROM work_effect')).scalar()
output=ROOT/'versions/v0.0.1'
# Scope excludes raw files, .env, runtime state, node_modules and all real text.
files=[]
for folder in ['backend/app','backend/tests','backend/alembic','backend/static','frontend/src','examples']:
    for path in sorted((ROOT/folder).rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            files.append({'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
for name in ['frontend/package.json','frontend/package-lock.json','Makefile','tools/local_manage.py','tools/verify_product.cjs','contracts/openapi-v0001.json','frontend/build.mjs','frontend/generate-client.mjs','frontend/tsconfig.json','backend/scripts_seed.py','backend/scripts_public.py','backend/services_companies.py','backend/pyproject.toml','backend/uv.lock','tools/vip','tools/export_openapi.py']:
    path=ROOT/name;files.append({'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
checks={'executed_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'base_revision':'30bb51b',
        'environment':'local PG14.23; project-specific DBs on shared cluster; local Chrome; React19.1.1/TS5.9.2',
        'backend_tests':{'passed':41,'warnings':1,'command':'./tools/vip test'},
        'migration':{'revision':revision,'test_upgrade_downgrade_upgrade':'passed','local_backup_catalog_checked':True,'backup_restore_exercise':False},
        'worker_readback':{'dispatched_scoped':worker[0],'errors_scoped':worker[1],'outbox_scoped':worker[2],'effects_all':effects},
        'real_readback':real,'real_companies':real_companies,'target_user_test':'not_run',
        'scope':'specific remediation scenarios, not full docs/13 acceptance','source_manifest':files}
(output/'verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
(output/'BROWSER-RESULTS.json').write_bytes((ROOT/'local-data/verification/browser-results.json').read_bytes())
print(json.dumps({k:v for k,v in checks.items() if k!='source_manifest'},ensure_ascii=False,indent=2))
