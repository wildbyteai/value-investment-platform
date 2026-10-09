"""R7 资讯采集定时器 + Skill: schedules, search-enabled chat per vendor, run → ingest → score, API."""
import json
import os
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.domains.news import agent, collector, llm

UTC = timezone.utc
ITEMS = {'items': [
    {'title': '合成甲制造获得海外大额订单', 'summary': '订单金额约 12 亿元。', 'url': 'https://example.com/n1',
     'source': '公司公告', 'published_at': '2026-10-08 09:30', 'company': '合成甲制造（600001.SH）', 'category': '制造'},
    {'title': '没有链接的条目也收', 'summary': 'x', 'url': 'not-a-url', 'published_at': '2026-10-08'},
    {'title': '', 'summary': '空标题丢弃'},
]}


def provider(mode, base='https://api.example.com/v1'):
    return llm.ProviderConfig('p', 'P', base, 'm', 'VIP_TEST_LLM_KEY', {}, mode)


def ok(content=None, **message):
    msg = {'role': 'assistant', 'content': content, **message}
    return httpx.Response(200, json={'choices': [{'message': msg, 'finish_reason': 'tool_calls' if message.get('tool_calls') else 'stop'}]})


# ---------------------------------------------------------------- schedule

def test_daily_schedule_in_shanghai_time():
    s = collector.validate_schedule({'type': 'daily', 'times': ['08:30', '17:00'], 'weekdays': [1, 2, 3, 4, 5]})
    # Thu 2026-10-08 07:00 Shanghai = Wed 23:00 UTC
    after = datetime(2026, 10, 7, 23, 0, tzinfo=UTC)
    assert collector.next_run(s, after) == datetime(2026, 10, 8, 0, 30, tzinfo=UTC)
    # Fri 17:00 Shanghai passed → next Monday 08:30
    assert collector.next_run(s, datetime(2026, 10, 9, 9, 0, tzinfo=UTC)) == datetime(2026, 10, 12, 0, 30, tzinfo=UTC)
    assert collector.describe_schedule(s) == '工作日 08:30、17:00'


def test_schedule_validation():
    with pytest.raises(Exception, match='HH:MM'):
        collector.validate_schedule({'type': 'daily', 'times': ['8:3']})
    with pytest.raises(Exception, match='不能少于'):
        collector.validate_schedule({'type': 'interval', 'minutes': 10})
    s = collector.validate_schedule({'type': 'interval', 'minutes': 180})
    assert collector.describe_schedule(s) == '每 3 小时'
    assert collector.validate_schedule({'type': 'daily', 'times': ['09:00']})['weekdays'] == [1, 2, 3, 4, 5, 6, 7]


# ---------------------------------------------------------------- vendor search modes

def test_qwen_enable_search(monkeypatch):
    monkeypatch.setenv('VIP_TEST_LLM_KEY', 'k')
    seen = {}

    def handler(req):
        seen['body'] = json.loads(req.content)
        return ok('{"items":[]}')
    r = agent.chat(provider('qwen_enable_search'), [{'role': 'user', 'content': 'x'}], transport=httpx.MockTransport(handler))
    assert r.content == '{"items":[]}'
    assert seen['body']['enable_search'] is True and seen['body']['search_options']['forced_search'] is True
    assert 'tools' not in seen['body']


def test_zhipu_web_search_tool(monkeypatch):
    monkeypatch.setenv('VIP_TEST_LLM_KEY', 'k')
    seen = {}

    def handler(req):
        seen['body'] = json.loads(req.content)
        return ok('{"items":[]}')
    agent.chat(provider('zhipu_web_search'), [{'role': 'user', 'content': 'x'}], transport=httpx.MockTransport(handler))
    tool = seen['body']['tools'][0]
    assert tool['type'] == 'web_search' and tool['web_search']['enable'] is True
    assert tool['web_search']['search_recency_filter'] == 'oneDay'


def test_kimi_search_loop_uses_same_key(monkeypatch):
    monkeypatch.setenv('VIP_TEST_LLM_KEY', 'kimi-key')
    calls = []

    def handler(req):
        body = json.loads(req.content)
        calls.append((req.url.path, req.headers['authorization'], body))
        if req.url.path.endswith('/tools/search_pro'):
            return httpx.Response(200, json={'search_results': [{'title': 'T', 'url': 'https://e.com/1', 'site_name': 'E',
                                                                 'date': '2026-10-08', 'chunks': [{'text': '正文', 'score': 1}]}]})
        if not any(m['role'] == 'tool' for m in body['messages']):
            return ok(None, tool_calls=[{'id': 'c1', 'type': 'function', 'function': {
                'name': 'web_search', 'arguments': json.dumps({'query': '合成甲制造 订单', 'start_date': '2026-10-07'})}}])
        return ok(json.dumps(ITEMS, ensure_ascii=False))
    r = agent.chat(provider('kimi_search', 'https://api.moonshot.cn/v1'), [{'role': 'user', 'content': 'x'}],
                   transport=httpx.MockTransport(handler))
    assert r.searches == ['合成甲制造 订单'] and r.rounds == 2
    paths = [c[0] for c in calls]
    assert paths == ['/v1/chat/completions', '/v1/tools/search_pro', '/v1/chat/completions']
    assert {c[1] for c in calls} == {'Bearer kimi-key'}
    assert calls[1][2]['text_query'] == '合成甲制造 订单' and calls[1][2]['time_window'] == {'start': '2026-10-07'}
    tool_msg = [m for m in calls[2][2]['messages'] if m['role'] == 'tool'][0]
    assert json.loads(tool_msg['content'])['results'][0]['text'] == '正文'


def test_openai_responses_web_search(monkeypatch):
    monkeypatch.setenv('VIP_TEST_LLM_KEY', 'oa-key')
    seen = {}

    def handler(req):
        seen['path'], seen['auth'], seen['body'] = req.url.path, req.headers['authorization'], json.loads(req.content)
        return httpx.Response(200, json={'status': 'completed', 'output': [
            {'type': 'web_search_call', 'status': 'completed', 'action': {'type': 'search', 'query': '合成甲制造 订单'}},
            {'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': '{"items":', 'annotations': []},
                                                                 {'type': 'output_text', 'text': '[]}'}]}]})
    r = agent.chat(provider('openai_web_search', 'https://api.openai.com/v1'),
                   [{'role': 'system', 'content': 'S'}, {'role': 'user', 'content': 'U'}], transport=httpx.MockTransport(handler))
    assert seen['path'] == '/v1/responses' and seen['auth'] == 'Bearer oa-key'
    assert seen['body']['tools'] == [{'type': 'web_search'}] and seen['body']['tool_choice'] == 'required'
    assert seen['body']['instructions'] == 'S' and seen['body']['input'] == [{'role': 'user', 'content': 'U'}]
    assert 'temperature' not in seen['body'] and seen['body']['reasoning'] == {'effort': 'max'}
    assert r.content == '{"items":[]}' and r.searches == ['合成甲制造 订单']
    empty = lambda req: httpx.Response(200, json={'status': 'incomplete', 'output': []})
    with pytest.raises(llm.LlmError, match='截断'):
        agent.chat(provider('openai_web_search'), [{'role': 'user', 'content': 'U'}], transport=httpx.MockTransport(empty))


def test_chat_errors(monkeypatch):
    monkeypatch.delenv('VIP_TEST_LLM_KEY', raising=False)
    with pytest.raises(llm.LlmError, match='未配置模型密钥'):
        agent.chat(provider('qwen_enable_search'), [])
    monkeypatch.setenv('VIP_TEST_LLM_KEY', 'k')
    with pytest.raises(llm.LlmError, match='HTTP 401'):
        agent.chat(provider('none'), [], transport=httpx.MockTransport(lambda r: httpx.Response(401, json={'error': {'message': 'bad key'}})))
    loop = lambda r: ok(None, tool_calls=[{'id': 'c', 'function': {'name': 'web_search', 'arguments': '{}'}}]) if 'chat' in r.url.path else httpx.Response(200, json={})
    with pytest.raises(llm.LlmError, match='轮内没有给出结果'):
        agent.chat(provider('kimi_search'), [{'role': 'user', 'content': 'x'}], transport=httpx.MockTransport(loop))


def test_parse_items():
    recs = collector.parse_items('好的：\n```json\n' + json.dumps(ITEMS, ensure_ascii=False) + '\n```')
    assert [r.title for r in recs] == ['合成甲制造获得海外大额订单', '没有链接的条目也收']
    assert recs[0].company_hint == '合成甲制造（600001.SH）' and recs[0].published_at.hour == 9 and recs[1].url is None
    with pytest.raises(llm.LlmError):
        collector.parse_items('今天没有新闻')
    with pytest.raises(llm.LlmError, match='items'):
        collector.parse_items('{"foo": 1}')


def test_skill_goes_into_system_prompt():
    from app.models.news import AgentSkill, CollectorTask
    task = CollectorTask(prompt='采集创新药公司动态')
    skill = AgentSkill(name='创新药日报', body='1. 先查港交所公告\n2. 再查医药魔方', enabled=True)
    msgs = collector.build_messages(task, skill, datetime(2026, 10, 8, 0, 30, tzinfo=UTC))
    assert '2026-10-08 08:30' in msgs[0]['content'] and '先查港交所公告' in msgs[0]['content']
    assert msgs[1] == {'role': 'user', 'content': '采集创新药公司动态'}
    skill.enabled = False
    assert '先查港交所公告' not in collector.build_messages(task, skill, datetime.now(UTC))[0]['content']


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


QWEN = {'provider_key': 'qwen', 'name': '通义千问', 'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'model': 'qwen-plus', 'api_key_env': 'VIP_TEST_LLM_KEY', 'search_mode': 'qwen_enable_search'}


def test_skill_crud_and_versions(env):
    c, ws, _ = env
    body = {'skill_key': 'pharma-daily', 'name': '创新药日报', 'description': '按公司清单逐个查', 'body': '1. 查公告'}
    assert c.post('/api/admin/skills', headers=h(ws, 'viewer@demo'), json=body).status_code == 403
    r = c.post('/api/admin/skills', headers=h(ws, 'data@demo'), json=body)
    assert r.status_code == 200 and r.json()['version'] == 1
    assert c.post('/api/admin/skills', headers=h(ws, 'data@demo'), json=body).status_code == 409
    sid = r.json()['id']
    same = c.put(f'/api/admin/skills/{sid}', headers=h(ws, 'data@demo'), json={**body, 'description': '改说明'}).json()
    assert same['version'] == 1
    bumped = c.put(f'/api/admin/skills/{sid}', headers=h(ws, 'data@demo'), json={**body, 'body': '1. 查公告\n2. 查新闻'}).json()
    assert bumped['version'] == 2
    assert [s['skill_key'] for s in c.get('/api/admin/skills', headers=h(ws, 'data@demo')).json()] == ['pharma-daily']


def test_collector_requires_search_model(env):
    c, ws, _ = env
    plain = c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'),
                   json={**QWEN, 'provider_key': 'plain', 'search_mode': 'none'}).json()
    r = c.post('/api/admin/collectors', headers=h(ws, 'data@demo'), json={
        'name': 'x', 'prompt': 'y', 'provider_id': plain['id'], 'schedule': {'type': 'daily', 'times': ['08:30']}})
    assert r.status_code == 422 and '联网' in r.text
    opts = c.get('/api/admin/collectors/options', headers=h(ws, 'data@demo')).json()
    assert [p['search_mode'] for p in opts['providers']] == ['none'] and opts['min_interval_minutes'] == 60
    listing = c.get('/api/admin/llm-providers', headers=h(ws, 'admin@demo')).json()
    assert 'kimi_search' in listing['search_modes'] and 'anthropic_web_search' in listing['search_modes']
    assert {p['provider_key']: p['search_mode'] for p in listing['presets']}['qwen'] == 'qwen_enable_search'


def test_collector_run_ingests_scores_and_records(env, monkeypatch):
    c, ws, Session = env
    monkeypatch.setenv('VIP_TEST_LLM_KEY', 'k')
    monkeypatch.delenv('VIP_DEEPSEEK_API_KEY', raising=False)
    pid = c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'), json=QWEN).json()['id']
    sid = c.get('/api/admin/skills', headers=h(ws, 'data@demo')).json()[0]['id']
    r = c.post('/api/admin/collectors', headers=h(ws, 'data@demo'), json={
        'name': '制造业早报', 'prompt': '采集合成甲制造今天的动态', 'provider_id': pid, 'skill_id': sid,
        'schedule': {'type': 'daily', 'times': ['08:30'], 'weekdays': [1, 2, 3, 4, 5]}})
    assert r.status_code == 200, r.text
    task = r.json()
    assert task['schedule_text'] == '工作日 08:30' and task['search_mode'] == 'qwen_enable_search' and task['next_run_at']
    assert c.delete(f'/api/admin/skills/{sid}', headers=h(ws, 'data@demo')).status_code == 409

    seen = {}

    def handler(req):
        body = json.loads(req.content)
        if body['messages'][1]['content'].startswith('关注公司名单'):   # the follow-up company linking call
            return ok(json.dumps({'links': [{'company': '合成甲制造', 'ticker': '600001.SH', 'relevance': 0.9,
                                             'impact': 0.5, 'rationale': '大额订单'}]}, ensure_ascii=False))
        seen['body'] = body
        return ok(json.dumps(ITEMS, ensure_ascii=False))
    with Session() as s:
        from app.models.news import CollectorTask
        t = s.get(CollectorTask, task['id'])
        run = collector.run_task(s, ws, t, transport=httpx.MockTransport(handler))
        s.commit()
    assert run['status'] == 'succeeded' and run['items_found'] == 2 and run['skill_version'] == 2
    assert run['stats']['new_items'] == 2 and run['stats']['scoring']['ai_scored'] == 2
    assert seen['body']['enable_search'] is True and '查新闻' in seen['body']['messages'][0]['content']
    events = c.get('/api/news/events', headers=h(ws, 'viewer@demo')).json()
    main = next(e for e in events if e['title'] == '合成甲制造获得海外大额订单')
    assert main['links'][0]['company_id'] == '00000000-0000-4000-8000-000000000001'
    detail = c.get(f"/api/news/events/{main['id']}", headers=h(ws, 'viewer@demo')).json()
    assert detail['items'][0]['feed'] == '制造业早报'
    runs = c.get(f"/api/admin/collectors/{task['id']}/runs", headers=h(ws, 'data@demo')).json()
    assert runs[0]['status'] == 'succeeded'
    listed = c.get('/api/admin/collectors', headers=h(ws, 'data@demo')).json()[0]
    assert listed['last_status'].startswith('成功') and listed['next_run_at'] == task['next_run_at']


def test_failed_run_is_recorded_not_raised(env, monkeypatch):
    c, ws, Session = env
    monkeypatch.setenv('VIP_TEST_LLM_KEY', 'k')
    task = c.get('/api/admin/collectors', headers=h(ws, 'data@demo')).json()[0]
    with Session() as s:
        from app.models.news import CollectorTask
        run = collector.run_task(s, ws, s.get(CollectorTask, task['id']),
                                 transport=httpx.MockTransport(lambda r: ok('今天没找到')))
        s.commit()
    assert run['status'] == 'failed' and 'JSON' in run['error'] and run['output_excerpt'] == '今天没找到'


def test_run_due_claims_each_task_once(env, monkeypatch):
    c, ws, Session = env
    monkeypatch.setenv('VIP_TEST_LLM_KEY', 'k')
    from app.models.news import CollectorRun, CollectorTask
    with Session() as s:
        t = s.scalars(select(CollectorTask)).first()
        t.next_run_at = datetime(2026, 10, 8, 0, 30, tzinfo=UTC)  # Thu 08:30 Shanghai
        s.commit()
        before = len(s.scalars(select(CollectorRun)).all())
    now = datetime(2026, 10, 8, 0, 33, tzinfo=UTC)
    out = collector.run_due(Session, now=now, transport=httpx.MockTransport(lambda r: ok('{"items":[]}')))
    assert [o['status'] for o in out] == ['succeeded']
    assert collector.run_due(Session, now=now) == []          # already moved forward
    with Session() as s:
        t = s.scalars(select(CollectorTask)).first()
        assert t.next_run_at == datetime(2026, 10, 9, 0, 30, tzinfo=UTC)
        runs = s.scalars(select(CollectorRun)).all()
        assert len(runs) == before + 1 and [r.trigger for r in runs].count('schedule') == 1


def test_disable_clears_next_run(env):
    c, ws, _ = env
    task = c.get('/api/admin/collectors', headers=h(ws, 'data@demo')).json()[0]
    body = {k: task[k] for k in ('name', 'prompt', 'provider_id', 'skill_id', 'schedule')}
    r = c.put(f"/api/admin/collectors/{task['id']}", headers=h(ws, 'data@demo'), json={**body, 'enabled': False}).json()
    assert r['enabled'] is False and r['next_run_at'] is None
