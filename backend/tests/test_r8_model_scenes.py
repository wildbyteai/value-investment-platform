"""R8 按场景配置模型 + 页面保存的加密 API Key（ADR 0015）。

Covers: scene config, AES-GCM round trip / context binding / rotation, missing master key,
key precedence (page > env), the key never coming back from the API / audit / OpenAPI,
scene resolution order, requires_search validation, permissions, collectors following the
资讯采集 scene when their own model is empty, and preset install without a model.
"""
import base64
import json
import os
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core import secret_box
from app.core.errors import Invalid
from app.domains.news import collector, collector_presets, llm, model_scenes, service

ROOT = Path(__file__).resolve().parents[2]
MASTER = base64.b64encode(b'm' * 32).decode()
OTHER = base64.b64encode(b'o' * 32).decode()
PAGE_KEY = 'sk-page-SECRET-abcd1234WXYZ'
ENV_KEY = 'sk-env-key-0000'


def ok(content):
    return httpx.Response(200, json={'choices': [{'message': {'role': 'assistant', 'content': content}, 'finish_reason': 'stop'}]})


# ---------------------------------------------------------------- config & crypto (no database)

def test_scene_config_maps_real_code_paths():
    scenes = model_scenes.scenes()
    keys = [s['key'] for s in scenes]
    assert keys == ['news_collect', 'news_analysis'] and len(set(keys)) == len(keys)
    collect = model_scenes.scene('news_collect')
    assert collect['requires_search'] is True and model_scenes.scene('news_analysis')['requires_search'] is False
    for s in scenes:
        assert s['label'] and s['description'] and s['code_paths']
        for path in s['code_paths']:
            assert (ROOT / path.split(' ')[0]).is_file(), path
    with pytest.raises(Invalid):
        model_scenes.scene('company_analysis')   # no code path yet → not a scene


def test_encrypt_round_trip_and_context_binding(monkeypatch):
    monkeypatch.setenv('VIP_SECRET_KEY', MASTER)
    monkeypatch.delenv('VIP_SECRET_KEY_PREVIOUS', raising=False)
    a = secret_box.encrypt(PAGE_KEY, 'llm_provider:1')
    b = secret_box.encrypt(PAGE_KEY, 'llm_provider:1')
    assert a != b and a.startswith('v1:') and PAGE_KEY not in a          # fresh nonce, no plaintext
    assert secret_box.decrypt(a, 'llm_provider:1') == PAGE_KEY
    with pytest.raises(secret_box.SecretBoxError):
        secret_box.decrypt(a, 'llm_provider:2')                          # copied onto another row
    monkeypatch.setenv('VIP_SECRET_KEY', OTHER)
    with pytest.raises(secret_box.SecretBoxError, match='无法用当前 VIP_SECRET_KEY 解密'):
        secret_box.decrypt(a, 'llm_provider:1')
    # rotation: new key current, old key previous → still readable, re-encrypt moves it over
    monkeypatch.setenv('VIP_SECRET_KEY_PREVIOUS', MASTER)
    rotated = secret_box.reencrypt(a, 'llm_provider:1')
    monkeypatch.delenv('VIP_SECRET_KEY_PREVIOUS')
    assert secret_box.decrypt(rotated, 'llm_provider:1') == PAGE_KEY


def test_missing_or_bad_master_key(monkeypatch):
    monkeypatch.delenv('VIP_SECRET_KEY', raising=False)
    assert not secret_box.available() and 'VIP_SECRET_KEY' in secret_box.problem()
    with pytest.raises(Invalid, match='系统未配置 VIP_SECRET_KEY'):
        secret_box.encrypt(PAGE_KEY, 'x')
    monkeypatch.setenv('VIP_SECRET_KEY', 'too-short')
    with pytest.raises(Invalid, match='格式不对'):
        secret_box.encrypt(PAGE_KEY, 'x')
    monkeypatch.setenv('VIP_SECRET_KEY', 'q' * 43)  # urlsafe base64 of 32 bytes (openssl/python both accepted)
    assert secret_box.available()


def test_page_key_wins_over_env_and_falls_back(monkeypatch):
    monkeypatch.setenv('VIP_SECRET_KEY', MASTER)
    monkeypatch.setenv('VIP_TEST_LLM_KEY', ENV_KEY)
    cipher = secret_box.encrypt(PAGE_KEY, 'llm_provider:r1')
    cfg = llm.ProviderConfig('p', 'P', 'https://api.example.com/v1', 'm', 'VIP_TEST_LLM_KEY',
                             api_key_ciphertext=cipher, row_id='r1')
    assert cfg.api_key == PAGE_KEY and cfg.key_source == 'page' and PAGE_KEY not in repr(cfg) and cipher not in repr(cfg)
    env_only = llm.ProviderConfig('p', 'P', 'https://api.example.com/v1', 'm', 'VIP_TEST_LLM_KEY')
    assert env_only.api_key == ENV_KEY and env_only.key_source == 'env'
    page_only = llm.ProviderConfig('p', 'P', 'https://api.example.com/v1', 'm', None, api_key_ciphertext=cipher, row_id='r1')
    assert page_only.api_key == PAGE_KEY and page_only.blocked is None
    # master key gone: the env key still works, the page key reports why it is unusable
    monkeypatch.delenv('VIP_SECRET_KEY')
    assert cfg.api_key == ENV_KEY and cfg.key_source == 'env' and 'VIP_SECRET_KEY' in cfg.key_problem
    assert page_only.api_key == '' and 'VIP_SECRET_KEY' in page_only.missing_key_message
    # the host allowlist still applies to page keys
    monkeypatch.setenv('VIP_SECRET_KEY', MASTER)
    evil = llm.ProviderConfig('p', 'P', 'https://attacker.example.net/v1', 'm', None, api_key_ciphertext=cipher, row_id='r1')
    assert evil.blocked and evil.api_key == '' and evil.key_source == 'none'


def test_master_key_cannot_be_used_as_a_model_key(monkeypatch):
    from app.core.secret_guard import key_env_problem
    monkeypatch.setenv('VIP_SECRET_KEY', MASTER)
    for name in ('VIP_SECRET_KEY', 'VIP_SECRET_KEY_PREVIOUS'):
        assert key_env_problem(name)
        cfg = llm.ProviderConfig('p', 'P', 'https://api.example.com/v1', 'm', name)
        assert cfg.api_key == '' and cfg.blocked


# ---------------------------------------------------------------- DB + API

@pytest.fixture(scope='module')
def env():
    from app.db import Base
    from app.main import app
    from services_companies import seed_companies
    engine = create_engine(os.environ['VIP_DB_URL'], future=True)
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    from scripts_seed import seed
    seed()
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        seed_companies(s); s.commit()
    with engine.connect() as conn:
        ws = str(conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one())
    with TestClient(app) as c:
        yield c, ws, Session
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _keys(monkeypatch):
    monkeypatch.setenv('VIP_SECRET_KEY', MASTER)
    monkeypatch.delenv('VIP_SECRET_KEY_PREVIOUS', raising=False)
    monkeypatch.delenv('VIP_TEST_LLM_KEY', raising=False)
    monkeypatch.delenv('VIP_DEEPSEEK_API_KEY', raising=False)


def h(ws, login):
    return {'X-Vip-Login': login, 'X-Vip-Workspace': ws}


QWEN = {'provider_key': 'qwen', 'name': '通义千问', 'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'model': 'qwen-plus', 'search_mode': 'qwen_enable_search', 'is_default': False}
PLAIN = {'provider_key': 'plain', 'name': '普通模型', 'base_url': 'https://api.example.com/v1', 'model': 'm-plain',
         'api_key_env': 'VIP_TEST_LLM_KEY', 'search_mode': 'none', 'is_default': True}


def _ids(c, ws):
    return {p['provider_key']: p['id'] for p in c.get('/api/admin/llm-providers', headers=h(ws, 'admin@demo')).json()['providers']}


def test_scene_endpoints_need_model_configure(env):
    c, ws, _ = env
    for login in ('viewer@demo', 'data@demo', 'research@demo'):
        assert c.get('/api/admin/model-scenes', headers=h(ws, login)).status_code == 403
        r = c.put('/api/admin/model-scenes', headers=h(ws, login), json={'bindings': []})
        assert r.status_code == 403 and r.json()['error']['code'] == 'forbidden'
        assert c.delete('/api/admin/llm-providers/x/api-key', headers=h(ws, login)).status_code == 403
    assert c.get('/api/admin/model-scenes', headers=h(ws, 'admin@demo')).status_code == 200


def test_resolution_starts_at_builtin(env):
    c, ws, Session = env
    view = c.get('/api/admin/model-scenes', headers=h(ws, 'admin@demo')).json()
    assert [i['source'] for i in view['items']] == ['builtin', 'builtin']
    collect = view['items'][0]
    assert collect['effective']['id'] is None and '不能联网' in collect['problem']
    with Session() as s:
        assert service.resolve_provider(s, ws).provider_key == 'deepseek'


def test_saving_key_without_master_key_is_refused(env, monkeypatch):
    c, ws, Session = env
    monkeypatch.delenv('VIP_SECRET_KEY')
    r = c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'), json={**QWEN, 'api_key': PAGE_KEY})
    assert r.status_code == 422 and '系统未配置 VIP_SECRET_KEY' in r.json()['error']['message']
    assert PAGE_KEY not in r.text
    assert _ids(c, ws) == {}                                   # nothing written
    # env keys keep working without a master key
    monkeypatch.setenv('VIP_TEST_LLM_KEY', ENV_KEY)
    r = c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'), json=PLAIN)
    assert r.status_code == 200 and r.json()['key_source'] == 'env' and r.json()['key_configured']
    listing = c.get('/api/admin/llm-providers', headers=h(ws, 'admin@demo')).json()
    assert listing['secret_key_ready'] is False and 'VIP_SECRET_KEY' in listing['secret_key_problem']


def test_page_key_is_write_only(env):
    c, ws, Session = env
    r = c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'), json={**QWEN, 'api_key': f'  {PAGE_KEY} '})
    assert r.status_code == 200, r.text
    out = r.json()
    assert PAGE_KEY not in r.text and 'api_key' not in out
    assert out['key_source'] == 'page' and out['key_hint'] == '••••WXYZ' and out['api_key_env'] is None and out['key_configured']
    listing = c.get('/api/admin/llm-providers', headers=h(ws, 'admin@demo'))
    assert PAGE_KEY not in listing.text and listing.json()['secret_key_ready'] is True
    # editing without a key keeps the saved one
    keep = c.put(f"/api/admin/llm-providers/{out['id']}", headers=h(ws, 'admin@demo'), json={**QWEN, 'name': '千问'}).json()
    assert keep['key_source'] == 'page' and keep['name'] == '千问'
    with Session() as s:
        stored = s.execute(text("SELECT api_key_ciphertext, api_key_hint FROM llm_provider WHERE id=:i"), {'i': out['id']}).one()
        audit = s.execute(text('SELECT action, detail_json FROM audit_log')).all()
        outbox = s.execute(text('SELECT payload_json FROM outbox')).scalars().all()
    assert stored[0].startswith('v1:') and PAGE_KEY not in stored[0] and stored[1] == 'WXYZ'
    assert all(PAGE_KEY not in row.detail_json and 'abcd1234' not in row.detail_json for row in audit)
    assert all(PAGE_KEY not in p for p in outbox)
    saved = [json.loads(d) for a, d in audit if a == 'admin.llm_provider.saved']
    assert saved[-2]['api_key_replaced'] is True and saved[-1]['api_key_replaced'] is False
    for path in ('/api/admin/model-scenes', '/api/admin/collectors/options', '/openapi.json'):
        assert PAGE_KEY not in c.get(path, headers=h(ws, 'admin@demo')).text


def test_openapi_marks_key_write_only(env):
    c, _, _ = env
    prop = c.get('/openapi.json').json()['components']['schemas']['ProviderIn']['properties']['api_key']
    assert prop['writeOnly'] is True and 'example' not in json.dumps(prop) and 'examples' not in prop


def test_page_key_is_what_gets_sent(env, monkeypatch):
    c, ws, Session = env
    monkeypatch.setenv('VIP_TEST_LLM_KEY', ENV_KEY)
    pid = _ids(c, ws)['qwen']
    seen = []

    def handler(req):
        seen.append(req.headers['Authorization'])
        return ok('{"links":[]}')
    with Session() as s:
        from app.models.news import LlmProvider
        row = s.get(LlmProvider, pid)
        cfg = model_scenes.provider_config(row)
        llm.propose_links(cfg, '事件', [], transport=httpx.MockTransport(handler))
    assert seen == [f'Bearer {PAGE_KEY}']


def test_short_key_and_host_change(env):
    c, ws, _ = env
    pid = _ids(c, ws)['qwen']
    r = c.put(f'/api/admin/llm-providers/{pid}', headers=h(ws, 'admin@demo'), json={**QWEN, 'api_key': 'abc'})
    assert r.status_code == 422 and 'abc' not in r.json()['error']['message']
    moved = {**QWEN, 'base_url': 'https://api.example.com/v1'}
    r = c.put(f'/api/admin/llm-providers/{pid}', headers=h(ws, 'admin@demo'), json=moved)
    assert r.status_code == 422 and '重新填写 API Key' in r.json()['error']['message']


def test_scene_validation(env):
    c, ws, _ = env
    ids = _ids(c, ws)
    r = c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'),
              json={'bindings': [{'scene': 'news_collect', 'provider_id': ids['plain']}]})
    assert r.status_code == 422 and '需要能联网的模型' in r.json()['error']['message']
    r = c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'), json={'bindings': [{'scene': 'company_analysis'}]})
    assert r.status_code == 422
    r = c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'),
              json={'bindings': [{'scene': 'news_analysis'}, {'scene': 'news_analysis'}]})
    assert r.status_code == 422
    r = c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'),
              json={'bindings': [{'scene': 'news_analysis', 'provider_id': 'no-such'}]})
    assert r.status_code == 422


def test_resolution_order(env, monkeypatch):
    c, ws, Session = env
    monkeypatch.setenv('VIP_TEST_LLM_KEY', ENV_KEY)
    ids = _ids(c, ws)
    # workspace default (plain, is_default) before any binding
    view = c.get('/api/admin/model-scenes', headers=h(ws, 'admin@demo')).json()
    assert [(i['source'], i['effective']['id']) for i in view['items']] == [('workspace_default', ids['plain'])] * 2
    r = c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'),
              json={'bindings': [{'scene': 'news_collect', 'provider_id': ids['qwen']},
                                 {'scene': 'news_analysis', 'provider_id': ids['qwen']}]})
    assert r.status_code == 200, r.text
    items = {i['key']: i for i in r.json()['items']}
    assert items['news_collect']['source'] == 'scene' and items['news_collect']['effective']['key_source'] == 'page'
    assert items['news_collect']['problem'] is None
    with Session() as s:
        assert service.resolve_provider(s, ws).model == 'qwen-plus'
    # a binding cannot be broken from the provider form
    r = c.put(f"/api/admin/llm-providers/{ids['qwen']}", headers=h(ws, 'admin@demo'), json={**QWEN, 'enabled': False})
    assert r.status_code == 422 and '正在使用' in r.json()['error']['message']
    r = c.put(f"/api/admin/llm-providers/{ids['qwen']}", headers=h(ws, 'admin@demo'), json={**QWEN, 'search_mode': 'none'})
    assert r.status_code == 422 and '联网' in r.json()['error']['message']
    # a binding to a model that got disabled anyway falls back to the workspace default
    with Session() as s:
        s.execute(text('UPDATE llm_provider SET enabled=false WHERE id=:i'), {'i': ids['qwen']}); s.commit()
        assert service.resolve_provider(s, ws).model == 'm-plain'
    view = c.get('/api/admin/model-scenes', headers=h(ws, 'admin@demo')).json()
    assert view['items'][1]['source'] == 'workspace_default' and '已停用' in view['items'][1]['problem']
    with Session() as s:
        s.execute(text('UPDATE llm_provider SET enabled=true WHERE id=:i'), {'i': ids['qwen']}); s.commit()
    # PUT replaces: leaving news_analysis out resets it to the default
    r = c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'),
              json={'bindings': [{'scene': 'news_collect', 'provider_id': ids['qwen']}]}).json()
    assert [i['source'] for i in r['items']] == ['scene', 'workspace_default']
    with Session() as s:
        actions = s.execute(text("SELECT detail_json FROM audit_log WHERE action='admin.model_scene.saved'")).scalars().all()
    assert len(actions) == 2 and json.loads(actions[-1])['changed'] == {'news_analysis': {'from': ids['qwen'], 'to': None}}


def test_collector_without_model_follows_scene(env):
    c, ws, Session = env
    ids = _ids(c, ws)
    body = {'name': '跟随场景', 'prompt': '采集合成甲制造动态', 'schedule': {'type': 'daily', 'times': ['08:30']}}
    r = c.post('/api/admin/collectors', headers=h(ws, 'data@demo'), json=body)
    assert r.status_code == 200, r.text
    task = r.json()
    assert task['provider_id'] is None and task['follows_scene'] is True and task['provider'].endswith('· qwen-plus')
    opts = c.get('/api/admin/collectors/options', headers=h(ws, 'data@demo')).json()
    assert opts['scene']['provider_id'] == ids['qwen'] and opts['scene']['source'] == 'scene'
    own = c.post('/api/admin/collectors', headers=h(ws, 'data@demo'), json={**body, 'name': '单独模型', 'provider_id': ids['qwen']}).json()
    assert own['follows_scene'] is False

    seen = []

    def handler(req):
        b = json.loads(req.content)
        seen.append((req.headers['Authorization'], b.get('enable_search'), b['model']))
        return ok('{"items":[]}')
    from app.models.news import CollectorTask
    with Session() as s:
        run = collector.run_task(s, ws, s.get(CollectorTask, task['id']), transport=httpx.MockTransport(handler))
        s.commit()
    assert run['status'] == 'succeeded', run
    assert seen == [(f'Bearer {PAGE_KEY}', True, 'qwen-plus')] and run['model'].endswith('/qwen-plus')
    assert PAGE_KEY not in json.dumps(run)
    # unbinding the scene: the collector now resolves to the non-search default and fails clearly (recorded, not raised)
    c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'), json={'bindings': []})
    with Session() as s:
        run = collector.run_task(s, ws, s.get(CollectorTask, task['id']), transport=httpx.MockTransport(handler))
        s.commit()
    assert run['status'] == 'failed' and '联网' in run['error'] and len(seen) == 1
    r = c.post('/api/admin/collectors', headers=h(ws, 'data@demo'), json={**body, 'name': '另一个'})
    assert r.status_code == 422 and '资讯采集' in r.json()['error']['message']
    c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'),
          json={'bindings': [{'scene': 'news_collect', 'provider_id': ids['qwen']}]})


def test_preset_install_without_model_follows_scene(env, capsys):
    c, ws, Session = env
    r = c.post('/api/admin/collectors/presets/install', headers=h(ws, 'data@demo'), json={'keys': ['global-policy']})
    assert r.status_code == 200, r.text
    assert r.json()['follows_scene'] is True and r.json()['provider_id'] is None and len(r.json()['created']) == 1
    from app import admin_cli
    admin_cli.main(['install-collector-presets', '--workspace', ws, '--only', 'ai-chip-storage'])
    assert '使用场景“资讯采集”的模型' in capsys.readouterr().out
    tasks = {t['name']: t for t in c.get('/api/admin/collectors', headers=h(ws, 'data@demo')).json()}
    preset_names = [t['name'] for t in collector_presets.presets()['tasks'] if t['key'] in ('global-policy', 'ai-chip-storage')]
    assert all(tasks[n]['provider_id'] is None and tasks[n]['follows_scene'] for n in preset_names)
    with Session() as s:
        detail = s.execute(text("SELECT detail_json FROM audit_log WHERE action='admin.collector.presets_installed'")).scalars().all()
    assert all(json.loads(d)['follows_scene'] is True for d in detail)


def test_clear_saved_key(env, monkeypatch):
    c, ws, Session = env
    pid = _ids(c, ws)['qwen']
    r = c.delete(f'/api/admin/llm-providers/{pid}/api-key', headers=h(ws, 'admin@demo'))
    assert r.status_code == 200 and r.json()['key_source'] == 'none' and r.json()['key_hint'] is None
    with Session() as s:
        row = s.execute(text('SELECT api_key_ciphertext FROM llm_provider WHERE id=:i'), {'i': pid}).scalar()
        cleared = s.execute(text("SELECT detail_json FROM audit_log WHERE action='admin.llm_provider.key_cleared'")).scalars().all()
    assert row is None and json.loads(cleared[0])['had_saved_key'] is True
    assert c.delete('/api/admin/llm-providers/nope/api-key', headers=h(ws, 'admin@demo')).status_code == 404


def test_rotate_secret_key_cli(env, monkeypatch, capsys):
    c, ws, Session = env
    pid = _ids(c, ws)['qwen']
    c.put(f'/api/admin/llm-providers/{pid}', headers=h(ws, 'admin@demo'), json={**QWEN, 'api_key': PAGE_KEY})
    monkeypatch.setenv('VIP_SECRET_KEY', OTHER)
    monkeypatch.setenv('VIP_SECRET_KEY_PREVIOUS', MASTER)
    from app import admin_cli
    admin_cli.main(['rotate-secret-key'])
    assert '重新加密 1 个' in capsys.readouterr().out
    monkeypatch.delenv('VIP_SECRET_KEY_PREVIOUS')
    from app.models.news import LlmProvider
    with Session() as s:
        assert model_scenes.provider_config(s.get(LlmProvider, pid)).api_key == PAGE_KEY
