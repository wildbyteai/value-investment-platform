"""R7 预置采集定时器包：配置合法、导入幂等、权限、只接受能联网的模型、命令行导入。"""
import os
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.domains.news import collector, collector_presets

CFG = collector_presets.presets()
KEYS = [t['key'] for t in CFG['tasks']]


# ---------------------------------------------------------------- config (no database)

def test_preset_config_is_valid():
    assert CFG['schema_version'] and CFG['policy_key'] == 'news-collector-presets' and CFG['version'] >= 1
    assert re.fullmatch(r'[a-z0-9_\-]+', CFG['skill']['skill_key'])
    assert len(KEYS) == 6 and len(set(KEYS)) == 6
    assert len({t['name'] for t in CFG['tasks']}) == 6
    times = []
    for t in CFG['tasks']:
        s = collector.validate_schedule(t['schedule'])
        assert s['type'] == 'daily' and s['weekdays'] == [1, 2, 3, 4, 5, 6, 7]
        times += s['times']
        assert 0 < len(t['prompt']) <= 20000 and len(t['name']) <= 200
    # staggered, all started by 07:00 so every run finishes before 07:30 Shanghai
    assert len(set(times)) == len(times) and max(times) < '07:30' and min(times) >= '06:00'


@pytest.mark.parametrize('banned', ['D:\\', 'D:/', 'Excel', 'excel', '.xlsx', 'openpyxl', 'pandas', 'lark-cli', '飞书',
                                    '执行完成后', '汇报：'])
def test_prompts_have_no_local_file_or_push_steps(banned):
    texts = [CFG['skill']['body']] + [t['prompt'] for t in CFG['tasks']]
    assert not any(banned in x for x in texts)


def test_company_list_codes():
    prompt = next(t['prompt'] for t in CFG['tasks'] if t['key'] == 'key-pharma-companies')
    for code in ['688428.SH', '09969.HK', '688235.SH', '06160.HK', 'ONC', '03696.HK', '01801.HK', '02595.HK',
                 '01177.HK', '03692.HK']:
        assert code in prompt
    assert '02585' not in prompt and 'BGNE' not in prompt and '四家' not in prompt
    assert all(c in prompt for c in ['研发布局', '上市', '临床', '论文', '其他'])


def test_shared_rules_live_in_the_skill_once():
    body = CFG['skill']['body']
    assert '24 小时' in body and '链接' in body and '编造' in body and '空列表' in body
    for t in CFG['tasks']:
        assert '不得编造来源' not in t['prompt']


# ---------------------------------------------------------------- DB + API

@pytest.fixture(scope='module')
def env():
    from app.db import Base
    from app.main import app
    engine = create_engine(os.environ['VIP_DB_URL'], future=True)
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    from scripts_seed import seed
    seed()
    Session = sessionmaker(bind=engine, future=True)
    with engine.connect() as conn:
        ws = str(conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one())
    with TestClient(app) as c:
        yield c, ws, Session
    Base.metadata.drop_all(bind=engine)


def h(ws, login):
    return {'X-Vip-Login': login, 'X-Vip-Workspace': ws}


QWEN = {'provider_key': 'qwen', 'name': '通义千问', 'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'model': 'qwen-plus', 'api_key_env': 'VIP_TEST_LLM_KEY', 'search_mode': 'qwen_enable_search'}


def test_presets_need_admin_permission(env):
    c, ws, _ = env
    assert c.get('/api/admin/collectors/presets', headers=h(ws, 'viewer@demo')).status_code == 403
    r = c.post('/api/admin/collectors/presets/install', headers=h(ws, 'viewer@demo'), json={'provider_id': 'x'})
    assert r.status_code == 403 and r.json()['error']['code'] == 'forbidden'


def test_install_rejects_non_search_or_unknown(env):
    c, ws, _ = env
    plain = c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'),
                   json={**QWEN, 'provider_key': 'plain', 'search_mode': 'none'}).json()
    r = c.post('/api/admin/collectors/presets/install', headers=h(ws, 'data@demo'), json={'provider_id': plain['id']})
    assert r.status_code == 422 and '联网' in r.json()['error']['message']
    r = c.post('/api/admin/collectors/presets/install', headers=h(ws, 'data@demo'), json={'provider_id': 'no-such-model'})
    assert r.status_code == 422
    pid = c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'), json=QWEN).json()['id']
    r = c.post('/api/admin/collectors/presets/install', headers=h(ws, 'data@demo'), json={'provider_id': pid, 'keys': ['nope']})
    assert r.status_code == 422 and 'nope' in r.json()['error']['message']
    # nothing was written by the rejected calls
    assert c.get('/api/admin/collectors', headers=h(ws, 'data@demo')).json() == []
    assert c.get('/api/admin/skills', headers=h(ws, 'data@demo')).json() == []


def test_install_is_idempotent(env):
    c, ws, Session = env
    pid = next(p['id'] for p in c.get('/api/admin/collectors/options', headers=h(ws, 'data@demo')).json()['providers']
               if p['search_mode'] == 'qwen_enable_search')
    listing = c.get('/api/admin/collectors/presets', headers=h(ws, 'data@demo')).json()
    assert listing['total'] == 6 and not any(i['installed'] for i in listing['items']) and not listing['skill']['installed']
    assert listing['items'][0]['schedule_text'] == '每天 06:00'
    assert c.get('/api/admin/collectors/presets?limit=2&offset=1', headers=h(ws, 'data@demo')).json()['items'][0]['key'] == KEYS[1]

    first = c.post('/api/admin/collectors/presets/install', headers=h(ws, 'data@demo'),
                   json={'provider_id': pid, 'keys': ['key-pharma-companies']})
    assert first.status_code == 200, first.text
    assert first.json()['skill_created'] is True and [x['key'] for x in first.json()['created']] == ['key-pharma-companies']

    second = c.post('/api/admin/collectors/presets/install', headers=h(ws, 'data@demo'), json={'provider_id': pid}).json()
    assert second['skill_created'] is False and second['skill_id'] == first.json()['skill_id']
    assert len(second['created']) == 5 and [x['key'] for x in second['skipped']] == ['key-pharma-companies']

    third = c.post('/api/admin/collectors/presets/install', headers=h(ws, 'data@demo'), json={'provider_id': pid}).json()
    assert third['created'] == [] and len(third['skipped']) == 6

    tasks = c.get('/api/admin/collectors', headers=h(ws, 'data@demo')).json()
    assert len(tasks) == 6 and {t['skill'] for t in tasks} == {'每日资讯采集通用规则'}
    assert sorted(t['schedule']['times'][0] for t in tasks) == ['06:00', '06:10', '06:20', '06:30', '06:40', '06:50']
    assert all(t['enabled'] and t['next_run_at'] and t['provider_id'] == pid for t in tasks)
    skills = c.get('/api/admin/skills', headers=h(ws, 'data@demo')).json()
    assert [(s['skill_key'], s['used_by']) for s in skills] == [('daily-news-common', 6)]
    listing = c.get('/api/admin/collectors/presets', headers=h(ws, 'data@demo')).json()
    assert all(i['installed'] and i['task_id'] for i in listing['items']) and listing['skill']['installed']

    from app.models.audit import AuditLog
    with Session() as s:
        actions = s.scalars(select(AuditLog.action).where(AuditLog.workspace_id == ws)).all()
    assert actions.count('admin.collector.presets_installed') == 3
    assert actions.count('admin.collector.saved') == 6 and actions.count('admin.skill.saved') == 1


def test_installed_collector_builds_messages_with_skill(env):
    _, ws, Session = env
    from datetime import datetime, timezone
    from app.models.news import AgentSkill, CollectorTask
    with Session() as s:
        task = s.scalar(select(CollectorTask).where(CollectorTask.workspace_id == ws, CollectorTask.name == '企业家访谈'))
        skill = s.get(AgentSkill, task.skill_id)
        msgs = collector.build_messages(task, skill, datetime(2026, 10, 9, 22, 50, tzinfo=timezone.utc))
    assert '每日资讯采集通用规则' in msgs[0]['content'] and '宁缺毋滥' in msgs[0]['content']
    assert '价值：★★★★' in msgs[1]['content']


def test_cli_install_skips_existing(env, capsys):
    _, ws, _ = env
    from app import admin_cli
    admin_cli.main(['install-collector-presets', '--workspace', ws, '--provider', 'qwen', '--actor', 'data@demo'])
    out = capsys.readouterr().out
    assert '已存在' in out and out.count('跳过') == 6
    with pytest.raises(SystemExit, match='联网'):
        admin_cli.main(['install-collector-presets', '--workspace', ws, '--provider', 'plain'])
