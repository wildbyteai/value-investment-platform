"""GET-only business readback. Emits shareable counts/status/hash, never raw source text."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8766'


def read(path, workspace='', login='research@demo'):
    request = Request(BASE + path, headers={'X-Vip-Login': login, 'X-Vip-Workspace': workspace})
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, None


def main():
    status, identities = read('/api/identities')
    assert status == 200 and identities['data_mode'] == 'real_public'
    ws = next(w['id'] for w in identities['workspaces'] if w['has_real_data'])
    status, companies = read('/api/companies', ws)
    assert status == 200 and companies
    status, items = read('/api/intake/items', ws)
    assert status == 200 and items
    readable = 0
    for item in items:
        status, detail = read('/api/intake/items/' + item['id'], ws)
        assert status == 200
        assert detail.get('original_text') and detail.get('revision')
        status, fixed = read('/api/intake/items/' + item['id'] + '?revision_id=' + detail['revision']['id'], ws)
        assert status == 200 and fixed['original_text'] == detail['original_text']
        assert fixed['revision']['hash'] == detail['revision']['hash']
        readable += 1
    scores = []
    for company in companies:
        status, score = read('/api/companies/' + company['id'] + '/score', ws)
        assert status == 200 and score['data_mode'] == 'real_public'
        status, catalog = read('/api/judgments/catalog/' + company['id'], ws)
        assert status == 200 and catalog
        scores.append({'company_id': company['id'], 'quality_unknown': score['quality_score'] is None,
                       'coverage': score['coverage_exact'], 'rubric_count': len(catalog),
                       'securities': [{'market': s['market'], 'valuation_unknown': s['valuation_score'] is None,
                                       'price_final': s['price_final']} for s in score['securities']]})
    status, runs = read('/api/research/runs', ws)
    assert status == 200
    hashes = []
    for run in runs[:2]:
        status, detail = read('/api/research/runs/' + run['id'], ws)
        assert status == 200 and detail['manifest_hash'] == run['manifest_hash']
        hashes.append({'status': detail['status'], 'manifest_hash': detail['manifest_hash']})
    ops_status, tasks = read('/api/worker/tasks', ws, 'admin@demo')
    source_status, sources = read('/api/worker/sources', ws, 'admin@demo')
    forbidden, _ = read('/api/intake/items', ws, 'admin@demo')
    assert ops_status == source_status == 200 and forbidden == 403
    assert all(set(s) == {'id', 'source_key', 'status'} for s in sources)
    empty = next(w['id'] for w in identities['workspaces'] if not w['has_real_data'])
    status, empty_companies = read('/api/companies', empty)
    assert status == 200 and empty_companies == []
    files = ['backend/app/domains/companies/judgment_authoring.py', 'backend/app/domains/companies/scoring_service.py',
             'backend/app/domains/strategy/strategy_service.py', 'backend/app/domains/companies/decision_service.py',
             'backend/app/domains/platform/worker_service.py', 'backend/app/domains/news/item_history.py',
             'backend/app/domains/companies/research_pipeline.py', 'backend/app/api/intake.py',
             'backend/app/api/judgments.py', 'backend/app/api/strategy.py', 'backend/app/api/collab.py',
             'frontend/src/app.tsx', 'frontend/src/judgments.tsx', 'frontend/src/template.tsx',
             'frontend/src/ui.tsx', 'frontend/src/client.ts', 'frontend/src/style.css',
             'backend/static/app.js', 'backend/static/app.css', 'contracts/openapi-v0001.json',
             'frontend/src/api-schema.ts', 'backend/tests/test_ux18.py', 'tools/verify_ux18_readonly.py']
    print(json.dumps({'checked_at': datetime.now(timezone.utc).isoformat(), 'mode': 'GET_only',
                      'data_mode': 'real_public', 'companies': len(companies), 'items': len(items),
                      'readable_bodies': readable, 'scores': scores, 'saved_runs': len(runs),
                      'history_readback': hashes, 'ops': {'tasks': len(tasks), 'sources': len(sources),
                      'research_access_status': forbidden}, 'empty_workspace_companies': 0,
                      'source_sha256': {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in files}},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
