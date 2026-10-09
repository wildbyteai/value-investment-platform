"""R9 内置模型预设（config/model-presets-v1.json）+ Claude / 豆包联网方式。

Covers: the preset config is the single source (frontend has no hardcoded list), every preset's
search_mode exists and its host is on the API-key allowlist, scenes that need search have a
search-capable preset, anthropic_web_search request/response parsing (key only in x-api-key,
never in errors or logs, pause_turn continuation), doubao_web_search reusing the Responses
parser, and GET /api/admin/llm-presets (permission + content).
"""
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core import secret_guard
from app.domains.news import agent, llm, model_presets, model_scenes
from app.domains.news.collector_policy import policy as collector_policy

ROOT = Path(__file__).resolve().parents[2]
CFG = model_presets.config()
PRESETS = model_presets.presets()
SECRET = 'sk-ant-SECRET-key-9876'


# ---------------------------------------------------------------- config (no database)

def test_preset_config_is_valid():
    assert CFG['schema_version'] and CFG['policy_key'] == 'model-presets' and CFG['version'] >= 1 and CFG['verified_on']
    keys = [p['provider_key'] for p in PRESETS]
    assert len(keys) == len(set(keys))
    assert {'openai', 'claude', 'gemini', 'deepseek', 'qwen', 'zhipu', 'kimi', 'doubao'} <= set(keys)
    modes = collector_policy()['search_modes']
    assert set(modes) == set(agent.SEARCH_MODES)          # config and code agree on the modes
    for p in PRESETS:
        assert all(p[k] for k in model_presets.FIELDS), p
        assert p['search_mode'] in modes and modes[p['search_mode']]['label']
        assert urlsplit(p['base_url']).scheme == 'https' and not p['base_url'].endswith('/')
        assert secret_guard.key_env_problem(p['api_key_env']) is None
        assert p['doc_url'].startswith('https://')


def test_every_preset_host_is_allowlisted(monkeypatch):
    monkeypatch.delenv('VIP_LLM_ALLOWED_HOSTS', raising=False)
    hosts = secret_guard.allowed_llm_hosts()
    for p in PRESETS:
        assert secret_guard.base_url_problem(p['base_url']) is None, p['base_url']
    for host in ('api.openai.com', 'api.anthropic.com', 'generativelanguage.googleapis.com', 'api.deepseek.com',
                 'dashscope.aliyuncs.com', 'open.bigmodel.cn', 'api.moonshot.cn', 'ark.cn-beijing.volces.com'):
        assert host in hosts
    assert secret_guard.base_url_problem('https://attacker.example.net/v1')


def test_scenes_needing_search_have_search_presets():
    searchable = [p for p in PRESETS if p['search_mode'] != 'none']
    for s in model_scenes.scenes():
        if s['requires_search']:
            assert searchable, s['key']
    # vendors whose OpenAI-compatible endpoint has no web search must not claim one
    by_key = {p['provider_key']: p['search_mode'] for p in PRESETS}
    assert by_key['deepseek'] == 'none' and by_key['gemini'] == 'none'
    assert by_key['claude'] == 'anthropic_web_search' and by_key['doubao'] == 'doubao_web_search'
    assert by_key['openai'] == 'openai_web_search'


def test_frontend_has_no_hardcoded_presets():
    src = (ROOT / 'frontend/src/pages/settings.tsx').read_text(encoding='utf-8')
    assert '/api/admin/llm-presets' in src
    for host in ('api.deepseek.com', 'dashscope.aliyuncs.com', 'api.anthropic.com', 'api.moonshot.cn'):
        assert host not in src


# ---------------------------------------------------------------- Claude: anthropic_web_search

def claude(base='https://api.anthropic.com/v1'):
    return llm.ProviderConfig('claude', 'Claude', base, 'claude-sonnet-5-5', 'VIP_ANTHROPIC_API_KEY', {}, 'anthropic_web_search')


def test_anthropic_web_search_request_and_parsing(monkeypatch, caplog):
    monkeypatch.setenv('VIP_ANTHROPIC_API_KEY', SECRET)
    seen = []

    def handler(req):
        seen.append((req.url.path, dict(req.headers), json.loads(req.content)))
        return httpx.Response(200, json={'role': 'assistant', 'stop_reason': 'end_turn', 'content': [
            {'type': 'text', 'text': '我先搜索一下。'},
            {'type': 'server_tool_use', 'id': 's1', 'name': 'web_search', 'input': {'query': '合成甲制造 订单'}},
            {'type': 'web_search_tool_result', 'tool_use_id': 's1', 'content': [
                {'type': 'web_search_result', 'url': 'https://e.com/1', 'title': 'T', 'encrypted_content': 'x'}]},
            {'type': 'text', 'text': '{"items":'},
            {'type': 'text', 'text': '[]}', 'citations': [{'type': 'web_search_result_location', 'url': 'https://e.com/1'}]}]})
    with caplog.at_level(logging.DEBUG):
        r = agent.chat(claude(), [{'role': 'system', 'content': 'S'}, {'role': 'user', 'content': 'U'}],
                       transport=httpx.MockTransport(handler))
    path, headers, body = seen[0]
    assert path == '/v1/messages'
    assert headers['x-api-key'] == SECRET and 'authorization' not in headers
    assert headers['anthropic-version'] == '2023-06-01'
    tool = body['tools'][0]
    assert tool['type'].startswith('web_search_') and tool['name'] == 'web_search' and tool['max_uses'] >= 1
    assert body['system'] == 'S' and body['messages'] == [{'role': 'user', 'content': 'U'}]
    assert body['model'] == 'claude-sonnet-5-5' and body['max_tokens'] > 0 and 'temperature' not in body
    assert r.content == '{"items":[]}' and r.searches == ['合成甲制造 订单'] and r.rounds == 1
    assert SECRET not in caplog.text and SECRET not in repr(claude())


def test_anthropic_pause_turn_is_continued(monkeypatch):
    monkeypatch.setenv('VIP_ANTHROPIC_API_KEY', SECRET)
    bodies = []
    first = [{'type': 'server_tool_use', 'id': 's1', 'name': 'web_search', 'input': {'query': 'q1'}},
             {'type': 'web_search_tool_result', 'tool_use_id': 's1', 'content': []}]

    def handler(req):
        bodies.append(json.loads(req.content))
        if len(bodies) == 1:
            return httpx.Response(200, json={'stop_reason': 'pause_turn', 'content': first})
        return httpx.Response(200, json={'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': '{"items":[]}'}]})
    r = agent.chat(claude(), [{'role': 'user', 'content': 'U'}], transport=httpx.MockTransport(handler))
    assert r.rounds == 2 and r.content == '{"items":[]}' and r.searches == ['q1']
    assert bodies[1]['messages'] == [{'role': 'user', 'content': 'U'}, {'role': 'assistant', 'content': first}]


def test_anthropic_errors_never_echo_the_key(monkeypatch):
    monkeypatch.setenv('VIP_ANTHROPIC_API_KEY', SECRET)
    bad = lambda req: httpx.Response(401, json={'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}})
    with pytest.raises(llm.LlmError, match='HTTP 401') as exc:
        agent.chat(claude(), [{'role': 'user', 'content': 'U'}], transport=httpx.MockTransport(bad))
    assert SECRET not in str(exc.value)
    empty = lambda req: httpx.Response(200, json={'stop_reason': 'max_tokens', 'content': []})
    with pytest.raises(llm.LlmError, match='截断'):
        agent.chat(claude(), [{'role': 'user', 'content': 'U'}], transport=httpx.MockTransport(empty))
    # a base URL outside the allowlist never receives the key
    with pytest.raises(llm.LlmError, match='安全检查'):
        agent.chat(claude('https://attacker.example.net/v1'), [{'role': 'user', 'content': 'U'}],
                   transport=httpx.MockTransport(lambda req: pytest.fail('request must not be sent')))


# ---------------------------------------------------------------- 豆包: doubao_web_search

def test_doubao_web_search_reuses_responses_parser(monkeypatch):
    monkeypatch.setenv('VIP_ARK_API_KEY', 'ark-key')
    seen = {}

    def handler(req):
        seen['path'], seen['auth'], seen['body'] = req.url.path, req.headers['authorization'], json.loads(req.content)
        return httpx.Response(200, json={'status': 'completed', 'output': [
            {'type': 'reasoning', 'summary': []},
            {'type': 'web_search_call', 'status': 'completed', 'action': {'type': 'search', 'query': 'AI 新闻', 'queries': ['AI 新闻']}},
            {'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': '{"items":[]}', 'annotations': []}]}]})
    p = llm.ProviderConfig('doubao', '豆包', 'https://ark.cn-beijing.volces.com/api/v3', 'doubao-seed-2-1-pro-260628',
                           'VIP_ARK_API_KEY', {}, 'doubao_web_search')
    r = agent.chat(p, [{'role': 'system', 'content': 'S'}, {'role': 'user', 'content': 'U'}], transport=httpx.MockTransport(handler))
    assert seen['path'] == '/api/v3/responses' and seen['auth'] == 'Bearer ark-key'
    body = seen['body']
    assert body['tools'] == [{'type': 'web_search', 'sources': ['doubao']}] and body['max_tool_calls'] >= 1
    assert 'instructions' not in body and body['input'][0] == {'role': 'system', 'content': 'S'}
    assert 'reasoning' not in body and 'tool_choice' not in body
    assert r.content == '{"items":[]}' and r.searches == ['AI 新闻']


# ---------------------------------------------------------------- API (database)

@pytest.fixture(scope='module')
def env():
    from app.db import Base
    from app.main import app
    engine = create_engine(os.environ['VIP_DB_URL'], future=True)
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    from scripts_seed import seed
    seed()
    with engine.connect() as conn:
        ws = str(conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one())
    with TestClient(app) as c:
        yield c, ws
    Base.metadata.drop_all(bind=engine)


def h(ws, login):
    return {'X-Vip-Login': login, 'X-Vip-Workspace': ws}


def test_presets_api(env):
    c, ws = env
    assert c.get('/api/admin/llm-presets', headers=h(ws, 'viewer@demo')).status_code == 403
    r = c.get('/api/admin/llm-presets', headers=h(ws, 'admin@demo'))
    assert r.status_code == 200
    data = r.json()
    assert data['version'] == CFG['version'] and data['items'] == PRESETS
    assert data['search_modes']['anthropic_web_search'] and data['search_modes']['doubao_web_search']
    assert 'api_key' not in json.dumps(data).replace('api_key_env', '')
    # the providers listing serves the same presets (one source)
    assert c.get('/api/admin/llm-providers', headers=h(ws, 'admin@demo')).json()['presets'] == PRESETS


def test_preset_can_be_saved_as_is(env):
    c, ws = env
    for p in PRESETS:
        body = {k: p[k] for k in ('provider_key', 'name', 'base_url', 'model', 'api_key_env', 'search_mode')}
        r = c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'), json={**body, 'provider_key': 'preset-' + p['provider_key']})
        assert r.status_code == 200, (p['provider_key'], r.text)
        assert r.json()['blocked'] is None and r.json()['search_mode'] == p['search_mode']
