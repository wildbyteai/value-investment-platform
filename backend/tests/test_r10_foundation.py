"""R10a 资讯→公司匹配地基（ADR 0016）：推理强度映射、场景推荐配置、场景接口的推理强度、
新接口契约（权限 + 501 not_implemented）、采集定时器范围字段、权限键、占位接口签名。"""
import inspect
import json
import os
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.errors import Invalid
from app.domains.news import agent, llm, model_presets, model_scenes, reasoning

ROOT = Path(__file__).resolve().parents[2]
OPENAI = 'https://api.openai.com/v1'
DEEPSEEK = 'https://api.deepseek.com'


# ---------------------------------------------------------------- reasoning effort (no database)

def test_allowed_efforts_per_preset_and_model():
    assert reasoning.allowed_efforts(OPENAI, 'gpt-6-luna') == ['none', 'low', 'medium', 'high', 'xhigh', 'max']
    for model in ('gpt-6.1-sol', 'gpt-6-astra'):   # these do not accept none
        assert reasoning.allowed_efforts(OPENAI, model) == ['low', 'medium', 'high', 'xhigh', 'max']
    assert reasoning.allowed_efforts(DEEPSEEK, 'deepseek-flash') == ['none', 'low', 'high', 'max']
    assert reasoning.allowed_efforts(DEEPSEEK, 'deepseek-v4-pro') == ['none', 'low', 'high', 'max']
    assert reasoning.allowed_efforts('https://dashscope.aliyuncs.com/compatible-mode/v1', 'qwen3.7-plus') == []
    assert reasoning.allowed_efforts('https://api.example.com/v1', 'm') == []
    assert reasoning.allowed_efforts(None, None) == []


def test_chat_params_vendor_mapping():
    # OpenAI chat: reasoning_effort as is; none only where the model allows it
    assert reasoning.chat_params(OPENAI, 'gpt-6-luna', 'none') == {'reasoning_effort': 'none'}
    assert reasoning.chat_params(OPENAI, 'gpt-6.1-sol', 'none') == {}
    assert reasoning.chat_params(OPENAI, 'gpt-6.1-sol', 'xhigh') == {'reasoning_effort': 'xhigh'}
    # DeepSeek: low/high/max; medium→high, xhigh→max; none → thinking disabled
    assert reasoning.chat_params(DEEPSEEK, 'deepseek-flash', 'low') == {'reasoning_effort': 'low'}
    assert reasoning.chat_params(DEEPSEEK, 'deepseek-flash', 'medium') == {'reasoning_effort': 'high'}
    assert reasoning.chat_params(DEEPSEEK, 'deepseek-flash', 'xhigh') == {'reasoning_effort': 'max'}
    assert reasoning.chat_params(DEEPSEEK, 'deepseek-flash', 'max') == {'reasoning_effort': 'max'}
    assert reasoning.chat_params(DEEPSEEK, 'deepseek-flash', 'none') == {'thinking': {'type': 'disabled'}}
    # vendors without declared efforts, unknown values, and no effort: nothing is sent
    assert reasoning.chat_params('https://api.moonshot.cn/v1', 'kimi-k3', 'high') == {}
    assert reasoning.chat_params(OPENAI, 'gpt-6-luna', 'turbo') == {}
    assert reasoning.chat_params(OPENAI, 'gpt-6-luna', None) == {}


def test_responses_params():
    assert reasoning.responses_params(OPENAI, 'gpt-6-luna', 'high') == {'reasoning': {'effort': 'high'}}
    assert reasoning.responses_params(OPENAI, 'gpt-6-astra', 'none') == {}
    assert reasoning.responses_params('https://ark.cn-beijing.volces.com/api/v3', 'doubao', 'high') == {}
    # OpenAI reached through a proxy host (no preset): passed through as before ADR 0016
    assert reasoning.responses_params('https://proxy.example.com/v1', 'gpt-6-luna', 'max', assume_openai=True) == \
        {'reasoning': {'effort': 'max'}}
    assert reasoning.responses_params('https://proxy.example.com/v1', 'gpt-6-luna', 'max') == {}


def test_provider_effort_precedence():
    p = llm.ProviderConfig('p', 'P', OPENAI, 'gpt-6-luna', None, {'reasoning_effort': 'max'})
    assert p.effort == 'max'                      # older per-model option still honoured
    p.reasoning_effort = 'low'
    assert p.effort == 'low'                      # scene-resolved effort wins


def test_chat_completions_body_carries_mapped_effort(monkeypatch):
    monkeypatch.setenv('VIP_LLM_ALLOWED_HOSTS', 'api.deepseek.com')
    monkeypatch.setenv('VIP_DEEPSEEK_API_KEY', 'ds-key')
    seen = []

    def handler(req):
        seen.append(json.loads(req.content))
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"links":[]}'}}]})
    p = llm.ProviderConfig('deepseek', 'DeepSeek', DEEPSEEK, 'deepseek-flash', 'VIP_DEEPSEEK_API_KEY', {}, 'none')
    p.reasoning_effort = 'none'
    llm.propose_links(p, '事件', [], transport=httpx.MockTransport(handler))
    p.reasoning_effort = 'medium'
    agent.chat(p, [{'role': 'user', 'content': 'x'}], transport=httpx.MockTransport(handler))
    assert seen[0]['thinking'] == {'type': 'disabled'} and 'reasoning_effort' not in seen[0]
    assert seen[1]['reasoning_effort'] == 'high' and 'thinking' not in seen[1]


# ---------------------------------------------------------------- scene recommendations (config)

def test_scene_recommendations_are_valid():
    presets = {p['provider_key']: p for p in model_presets.config()['presets']}
    expected = {
        'news_collect': [('openai', 'gpt-6-luna', 'high'), ('openai', 'gpt-6.1-sol', 'medium')],
        'news_extract': [('deepseek', 'deepseek-flash', 'low'), ('openai', 'gpt-6-luna', 'low')],
        'news_reassess': [('deepseek', 'deepseek-flash', 'high'), ('deepseek', 'deepseek-v4-pro', 'high')],
        'company_digest': [('deepseek', 'deepseek-v4-pro', 'high'), ('openai', 'gpt-6.1-sol', 'high')],
        'zone_review': [('openai', 'gpt-6.1-sol', 'high'), ('deepseek', 'deepseek-v4-pro', 'max')],
    }
    for s in model_scenes.scenes():
        recs = [(r['preset'], r['model'], r['reasoning_effort']) for r in s['recommended']]
        assert recs == expected[s['key']], s['key']
        assert s['cost_note'] and all(r['why'] for r in s['recommended'])
        for preset, model, effort in recs:
            p = presets[preset]
            assert effort in reasoning.allowed_efforts(p['base_url'], model), (s['key'], model, effort)
            if s['requires_search']:
                assert p['search_mode'] != 'none', (s['key'], preset)   # DeepSeek cannot collect
    assert presets['deepseek']['model'] == 'deepseek-flash' and 'deepseek-v4-pro' in presets['deepseek']['note']
    assert presets['openai']['model'] == 'gpt-6-luna'
    assert 'reasoning_effort' not in json.loads((ROOT / 'config/news-collector-v1.json').read_text())['search_modes']['openai_web_search']


def test_recommended_effort_lookup():
    assert model_scenes.recommended_effort('news_collect', OPENAI, 'gpt-6-luna') == 'high'
    assert model_scenes.recommended_effort('news_collect', OPENAI, 'gpt-6.1-sol') == 'medium'
    assert model_scenes.recommended_effort('news_collect', OPENAI, 'gpt-6-astra') == 'high'   # same vendor, first entry
    assert model_scenes.recommended_effort('news_analysis', DEEPSEEK, 'deepseek-v4-pro') == 'low'  # old key works
    assert model_scenes.recommended_effort('zone_review', DEEPSEEK, 'deepseek-v4-pro') == 'max'
    assert model_scenes.recommended_effort('news_extract', 'https://api.example.com/v1', 'm') is None
    with pytest.raises(Invalid):
        model_scenes.recommended_effort('company_analysis', OPENAI, 'x')


def test_matching_interfaces_are_typed_stubs():
    from app.domains.news.matching import extract, jobs, resolve, stream, suggest, watchlist
    expected = {
        extract: ['parse_mentions', 'extract_mentions', 'rule_mentions', 'extract_event'],
        resolve: ['load_index', 'resolve_mention', 'resolve_event'],
        watchlist: ['list_watch', 'add_watch', 'update_watch', 'remove_watch', 'list_aliases', 'add_alias',
                    'delete_alias', 'seed_aliases'],
        suggest: ['suggested_companies', 'add_suggested'],
        stream: ['company_news', 'company_digest'],
        jobs: ['estimate', 'create_job', 'run_job', 'cancel_job', 'job_dict', 'list_jobs'],
    }
    for module, names in expected.items():
        for name in names:
            fn = getattr(module, name)
            assert fn.__doc__ or module.__doc__, name
            args = [None] * len([p for p in inspect.signature(fn).parameters.values()
                                 if p.default is inspect.Parameter.empty])
            with pytest.raises(NotImplementedError):
                fn(*args)
    assert resolve.MATCH_METHODS == ('ticker', 'alias', 'contains') and resolve.RULE_VERSION == 'resolve:v1'
    assert extract.RULE_EXTRACTOR == 'rule:v1' and jobs.JOB_KINDS == ('rematch', 'reassess')


def test_new_permissions():
    from app.domains.identity.permissions import permissions_for, role_permissions
    roles = role_permissions()
    for role in ('researcher', 'strategy_manager', 'data_admin', 'system_admin'):
        assert 'watchlist.manage' in roles[role], role
    assert 'watchlist.manage' not in roles['viewer']
    assert [r for r, perms in roles.items() if 'news.reassess' in perms] == ['data_admin', 'system_admin']
    assert 'news.reassess' not in permissions_for(['researcher', 'strategy_manager'])


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


def h(ws, login):
    return {'X-Vip-Login': login, 'X-Vip-Workspace': ws}


def _provider(c, ws, **over):
    body = {'provider_key': 'p', 'name': 'P', 'base_url': 'https://api.example.com/v1', 'model': 'm',
            'api_key_env': 'VIP_TEST_LLM_KEY', 'search_mode': 'none', **over}
    r = c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'), json=body)
    assert r.status_code in (200, 201), r.text
    return r.json()['id']


def test_model_scenes_api_reasoning_effort(env, monkeypatch):
    c, ws, Session = env
    monkeypatch.setenv('VIP_LLM_ALLOWED_HOSTS', 'api.deepseek.com,api.openai.com,api.example.com')
    ds = _provider(c, ws, provider_key='deepseek', name='DeepSeek', base_url=DEEPSEEK, model='deepseek-flash',
                   api_key_env='VIP_DEEPSEEK_API_KEY')
    sol = _provider(c, ws, provider_key='openai', name='OpenAI', base_url=OPENAI, model='gpt-6.1-sol',
                    api_key_env='VIP_OPENAI_API_KEY', search_mode='openai_web_search')
    plain = _provider(c, ws, provider_key='plain', name='Plain')
    view = c.get('/api/admin/model-scenes', headers=h(ws, 'admin@demo')).json()
    assert view['efforts'] == list(reasoning.EFFORTS)
    assert view['allowed_efforts_by_provider'] == {ds: ['none', 'low', 'high', 'max'],
                                                   sol: ['low', 'medium', 'high', 'xhigh', 'max'], plain: []}
    items = {i['key']: i for i in view['items']}
    assert list(items) == ['news_collect', 'news_extract', 'news_reassess', 'company_digest', 'zone_review']
    assert items['news_extract']['aliases'] == ['news_analysis'] and items['news_reassess']['status'] == 'planned'
    assert items['news_extract']['recommended'][0] == {
        'preset': 'deepseek', 'preset_name': 'DeepSeek', 'model': 'deepseek-flash', 'reasoning_effort': 'low',
        'why': items['news_extract']['recommended'][0]['why']}
    assert items['news_collect']['cost_note']
    # an effort the bound model does not allow is refused; none without a model too
    for bad, msg in (({'scene': 'news_extract', 'provider_id': ds, 'reasoning_effort': 'medium'}, '不支持推理强度 medium'),
                     ({'scene': 'news_collect', 'provider_id': sol, 'reasoning_effort': 'none'}, '不支持推理强度 none'),
                     ({'scene': 'news_extract', 'provider_id': plain, 'reasoning_effort': 'low'}, '不支持设置推理强度'),
                     ({'scene': 'news_extract', 'reasoning_effort': 'low'}, '需要指定模型')):
        r = c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'), json={'bindings': [bad]})
        assert r.status_code == 422 and msg in r.json()['error']['message'], r.text
    r = c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'),
              json={'bindings': [{'scene': 'news_extract', 'provider_id': ds, 'reasoning_effort': 'turbo'}]})
    assert r.status_code == 422
    # the old key is accepted and stored under the new one; duplicates through the alias are refused
    r = c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'),
              json={'bindings': [{'scene': 'news_analysis', 'provider_id': ds}, {'scene': 'news_extract', 'provider_id': ds}]})
    assert r.status_code == 422
    r = c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'),
              json={'bindings': [{'scene': 'news_analysis', 'provider_id': ds},
                                 {'scene': 'news_collect', 'provider_id': sol, 'reasoning_effort': 'xhigh'},
                                 {'scene': 'news_reassess', 'provider_id': ds, 'reasoning_effort': 'max'}]})
    assert r.status_code == 200, r.text
    items = {i['key']: i for i in r.json()['items']}
    ext = items['news_extract']
    assert ext['provider_id'] == ds and ext['reasoning_effort'] is None
    assert (ext['effective_reasoning_effort'], ext['effort_source']) == ('low', 'recommended')
    assert ext['allowed_efforts'] == ['none', 'low', 'high', 'max']
    col = items['news_collect']
    assert (col['reasoning_effort'], col['effective_reasoning_effort'], col['effort_source']) == ('xhigh', 'xhigh', 'scene')
    assert (items['news_reassess']['effective_reasoning_effort'], items['news_reassess']['effort_source']) == ('max', 'scene')
    with Session() as s:
        assert s.execute(text("SELECT count(*) FROM llm_scene_binding WHERE scene_key='news_analysis'")).scalar() == 0
        assert model_scenes.resolve(s, ws, 'news_analysis').reasoning_effort == 'low'
        assert model_scenes.resolve(s, ws, 'news_collect').reasoning_effort == 'xhigh'
        audit = json.loads(s.execute(text("SELECT detail_json FROM audit_log WHERE action='admin.model_scene.saved' "
                                          "ORDER BY created_at DESC LIMIT 1")).scalar())
    assert audit['efforts'] == {'news_collect': 'xhigh', 'news_reassess': 'max'}
    assert audit['changed']['news_collect']['reasoning_effort'] == {'from': None, 'to': 'xhigh'}
    # the request actually carries the scene effort (DeepSeek low for news_extract)
    monkeypatch.setenv('VIP_DEEPSEEK_API_KEY', 'ds-key')
    seen = []

    def handler(req):
        seen.append(json.loads(req.content))
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"links":[]}'}}]})
    from app.domains.news import service
    with Session() as s:
        assert service.resolve_provider(s, ws).effort == 'low'
        service.score_events(s, ws, transport=httpx.MockTransport(handler)); s.rollback()
    # presets expose the allowed efforts; providers list them per configured model
    presets = c.get('/api/admin/llm-presets', headers=h(ws, 'admin@demo')).json()['items']
    assert {p['provider_key']: p['reasoning_efforts'] for p in presets}['deepseek'] == ['none', 'low', 'high', 'max']
    providers = {p['id']: p for p in c.get('/api/admin/llm-providers', headers=h(ws, 'admin@demo')).json()['providers']}
    assert providers[sol]['reasoning_efforts'][0] == 'low' and providers[plain]['reasoning_efforts'] == []
    c.put('/api/admin/model-scenes', headers=h(ws, 'admin@demo'), json={'bindings': []})


STUBS = [
    ('get', '/api/watchlist/companies', None, 'research.read'),
    ('post', '/api/watchlist/companies', {'name': '合成新公司'}, 'watchlist.manage'),
    ('patch', '/api/watchlist/companies/w1', {'status': 'archived'}, 'watchlist.manage'),
    ('delete', '/api/watchlist/companies/w1', None, 'watchlist.manage'),
    ('get', '/api/companies/c1/aliases', None, 'research.read'),
    ('post', '/api/companies/c1/aliases', {'alias': 'BeOne', 'kind': 'en'}, 'watchlist.manage'),
    ('delete', '/api/companies/c1/aliases/a1', None, 'watchlist.manage'),
    ('get', '/api/companies/c1/news', None, 'research.read'),
    ('get', '/api/news/events/e1/mentions', None, 'research.read'),
    ('get', '/api/news/suggested-companies', None, 'research.read'),
    ('post', '/api/news/suggested-companies/add', {'name_norm': 'beone'}, 'watchlist.manage'),
    ('post', '/api/news/match-jobs/estimate', {'kind': 'rematch'}, 'watchlist.manage'),
    ('post', '/api/news/match-jobs', {'kind': 'rematch'}, 'watchlist.manage'),
    ('get', '/api/news/match-jobs', None, 'research.read'),
    ('get', '/api/news/match-jobs/j1', None, 'research.read'),
    ('post', '/api/news/match-jobs/j1/cancel', None, 'watchlist.manage'),
]


@pytest.mark.parametrize('method, path, body, perm', STUBS)
def test_contract_routes_answer_501_after_permission_checks(env, method, path, body, perm):
    c, ws, _ = env
    kw = {'json': body} if body is not None else {}
    denied = 'viewer@demo'
    if perm == 'watchlist.manage':
        r = getattr(c, method)(path, headers=h(ws, denied), **kw)
        assert r.status_code == 403 and r.json()['error']['code'] == 'forbidden', r.text
    r = getattr(c, method)(path, headers=h(ws, 'research@demo'), **kw)
    assert r.status_code == 501, r.text
    err = r.json()
    assert err['error']['code'] == 'not_implemented' and err['request_id'] and '计划在 R1' in err['error']['message']
    assert getattr(c, method)(path, headers={'X-Vip-Workspace': ws}, **kw).status_code == 401


def test_reassess_needs_news_reassess(env):
    c, ws, _ = env
    for path in ('/api/news/match-jobs', '/api/news/match-jobs/estimate'):
        r = c.post(path, headers=h(ws, 'research@demo'), json={'kind': 'reassess', 'date_from': '2026-10-01'})
        assert r.status_code == 403 and '重新研判' in r.json()['error']['message']
        assert c.post(path, headers=h(ws, 'data@demo'), json={'kind': 'reassess'}).status_code == 501
    r = c.post('/api/news/match-jobs', headers=h(ws, 'data@demo'),
               json={'kind': 'reassess', 'date_from': '2026-10-09', 'date_to': '2026-10-01'})
    assert r.status_code == 422
    r = c.post('/api/news/match-jobs', headers=h(ws, 'data@demo'), json={'kind': 'everything'})
    assert r.status_code == 422 and r.json()['error']['code'] == 'invalid'
    r = c.post('/api/watchlist/companies', headers=h(ws, 'research@demo'), json={'company_id': 'x', 'name': 'y'})
    assert r.status_code == 422


def test_openapi_contract_has_matching_schemas(env):
    c, ws, _ = env
    spec = c.get('/openapi.json').json()
    schemas = spec['components']['schemas']
    for name in ('WatchCompanyOut', 'WatchCompanyIn', 'AliasOut', 'MentionOut', 'MentionListOut', 'SuggestedCompanyOut',
                 'MatchJobIn', 'MatchJobOut', 'MatchEstimateOut', 'CompanyNewsOut', 'SceneOut', 'ScenesOut'):
        assert name in schemas, name
    assert set(schemas['MatchJobIn']['properties']) == {'kind', 'date_from', 'date_to', 'event_ids'}
    assert set(schemas['MatchEstimateOut']['properties']) == {'kind', 'events', 'estimated_calls'}
    assert {'reasoning_effort', 'recommended', 'allowed_efforts', 'cost_note'} <= set(schemas['SceneOut']['properties'])
    assert 'reasoning_effort' in schemas['SceneBindingIn']['properties']
    assert {'scope_kind', 'target_company_ids', 'industry'} <= set(schemas['CollectorIn']['properties'])
    assert '501' in spec['paths']['/api/news/match-jobs']['post']['responses']
    contract = json.loads((ROOT / 'contracts/openapi-v0001.json').read_text(encoding='utf-8'))
    assert set(contract['paths']) == set(spec['paths']), 'run make generate-client'


def test_collector_scope_fields(env, monkeypatch):
    c, ws, Session = env
    monkeypatch.setenv('VIP_TEST_LLM_KEY', 'k')
    qid = _provider(c, ws, provider_key='qwen', name='Q', search_mode='qwen_enable_search')
    with Session() as s:
        company = s.execute(text('SELECT id FROM company ORDER BY name LIMIT 1')).scalar()
    base = {'name': '定向', 'prompt': '采集合成公司动态', 'provider_id': qid, 'schedule': {'type': 'daily', 'times': ['08:30']}}
    r = c.post('/api/admin/collectors', headers=h(ws, 'data@demo'), json=base)
    assert r.status_code == 200 and (r.json()['scope_kind'], r.json()['target_company_ids']) == ('general', [])
    tid = r.json()['id']
    r = c.put(f'/api/admin/collectors/{tid}', headers=h(ws, 'data@demo'), json={**base, 'scope_kind': 'targeted'})
    assert r.status_code == 422 and '至少选择一家' in r.json()['error']['message']
    r = c.put(f'/api/admin/collectors/{tid}', headers=h(ws, 'data@demo'),
              json={**base, 'scope_kind': 'targeted', 'target_company_ids': ['no-such']})
    assert r.status_code == 422 and '不存在' in r.json()['error']['message']
    r = c.put(f'/api/admin/collectors/{tid}', headers=h(ws, 'data@demo'),
              json={**base, 'scope_kind': 'targeted', 'target_company_ids': [company, company], 'industry': '创新药'})
    assert r.status_code == 200 and r.json()['target_company_ids'] == [company] and r.json()['industry'] == '创新药'
    # an older client that does not send the scope keeps it
    r = c.put(f'/api/admin/collectors/{tid}', headers=h(ws, 'data@demo'), json={**base, 'name': '定向2'})
    assert r.status_code == 200 and r.json()['scope_kind'] == 'targeted' and r.json()['target_company_ids'] == [company]
    r = c.put(f'/api/admin/collectors/{tid}', headers=h(ws, 'data@demo'), json={**base, 'scope_kind': 'general'})
    assert r.json()['scope_kind'] == 'general' and r.json()['target_company_ids'] == []
