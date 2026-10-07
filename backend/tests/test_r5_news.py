"""R5 资讯雷达: normalize daily Excel, dedupe into events, AI/rule links, human review, admin."""
import io
import json
import os
from datetime import datetime
from decimal import Decimal

import httpx
import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.domains.news import llm
from app.domains.news.dedupe import same_event, similarity
from app.domains.news.normalize import feed_key_from_filename, parse_published, records_from_rows, records_from_rss

# Synthetic rows shaped like the human-run feeds (no real third-party content in Git).
DAILY = [
    ['合成行业每日动态 - 2026-09-30', None, None, None, None, None],
    ['序号', '标题', '核心内容摘要', '信息来源', '发布时间', '原文链接'],
    ['1', '合成甲制造发布新一代产品并上调全年指引', '合成甲制造（600001.SH）宣布新品，订单超预期。', '公司公告', '2026-09-30 08:15（北京时间）', 'https://example.com/a'],
    ['2', '行业协会发布月度数据', '整体需求平稳。', '协会', '2026-09-30', 'https://example.com/b'],
]
WATCH = [
    ['重点公司动态日报（2026-09-30）', None, None, None, None, None, None],
    ['监控窗口：2026-09-29 04:30 至 2026-09-30 04:30', None, None, None, None, None, None],
    ['序号', '公司（代码）', '信息类型', '标题/事件', '核心内容摘要', '发布时间', '简要解读'],
    ['◆ 合成甲制造（600001.SH / 0001.HK）', None, None, None, None, None, None],
    ['1', '600001.SH / 0001.HK', '经营', '合成甲制造发布新一代产品，上调全年指引', '同一事件的另一来源报道。', '2026-09-30', '利好'],
    [None] * 7,
    ['◆ 合成乙制造（600002.SH）', None, None, None, None, None, None],
    ['今日无重要动态（24小时窗口内未检索到高价值公告）', None, None, None, None, None, None],
]
INTERVIEW = [
    ['日期', '人物', '公司/头衔', '场合/来源', '演讲或采访核心内容摘要', '价值评级', '信息来源URL'],
    ['2026-09-29', '张三', '合成乙制造 董事长', '年度大会', '谈长期战略。', '★★★★☆', 'https://example.com/c'],
]


def xlsx(rows):
    wb = openpyxl.Workbook()
    for r in rows:
        wb.active.append(r)
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()


def test_header_detection_banners_and_placeholders():
    daily = records_from_rows(DAILY)
    assert [r.title for r in daily] == ['合成甲制造发布新一代产品并上调全年指引', '行业协会发布月度数据']
    assert daily[0].published_at.isoformat() == '2026-09-30T08:15:00+08:00'
    watch = records_from_rows(WATCH)
    assert len(watch) == 1 and watch[0].company_hint == '合成甲制造（600001.SH / 0001.HK）' and watch[0].note == '利好'
    interview = records_from_rows(INTERVIEW)
    assert interview[0].title == '张三｜年度大会' and interview[0].company_hint == '合成乙制造 董事长'
    assert records_from_rows([['没有表头'], ['x']]) == []


def test_feed_key_and_dates():
    assert feed_key_from_filename('创新药每日动态_2026-09-30.xlsx')[0] == '创新药每日动态'
    assert feed_key_from_filename('AI科技行业重要动态_20260930.xlsx')[0] == 'AI科技行业重要动态'
    assert parse_published('2026/9/3') .day == 3 and parse_published('无') is None


def test_dedupe_by_title_similarity_and_window():
    a, b = '合成甲制造发布新一代产品并上调全年指引', '合成甲制造发布新一代产品，上调全年指引'
    assert similarity(a, b) >= Decimal('0.45')
    d1, d2 = parse_published('2026-09-30'), parse_published('2026-10-10')
    assert same_event(a, d1, b, d1) and not same_event(a, d1, b, d2)
    assert not same_event(a, d1, '行业协会发布月度数据', d1)


def test_rss_and_atom():
    rss = '<rss><channel><item><title>合成甲制造中标</title><link>https://e.com/1</link><pubDate>Tue, 29 Sep 2026 10:00:00 +0800</pubDate><description>&lt;p&gt;大单&lt;/p&gt;</description></item></channel></rss>'
    r = records_from_rss(rss)[0]
    assert (r.title, r.summary, r.published_at.hour) == ('合成甲制造中标', '大单', 10)
    atom = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>T</title><link href="https://e.com/2"/><updated>2026-09-29T10:00:00Z</updated></entry></feed>'
    assert records_from_rss(atom)[0].url == 'https://e.com/2'


def test_parse_links_clamps_and_filters():
    content = '```json\n{"links":[{"company":"合成甲制造","ticker":"600001.SH","relevance":1.4,"impact":-3,"rationale":"主角"},{"company":"路人","relevance":0.1,"impact":0.2}]}\n```'
    links = llm.parse_links(content)
    assert [(l.company, l.relevance, l.impact) for l in links] == [('合成甲制造', Decimal('1.0000'), Decimal('-1.0000'))]
    with pytest.raises(llm.LlmError):
        llm.parse_links('not json')


def test_default_provider_is_deepseek_and_needs_key(monkeypatch):
    p = llm.default_provider()
    assert (p.provider_key, p.base_url, p.model) == ('deepseek', 'https://api.deepseek.com', 'deepseek-chat')
    monkeypatch.delenv(p.api_key_env, raising=False)
    with pytest.raises(llm.LlmError, match='未配置模型密钥'):
        llm.propose_links(p, 'x', [])


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


def upload(c, ws, login='data@demo', score='true'):
    files = [('files', ('合成行业每日动态_2026-09-30.xlsx', xlsx(DAILY))),
             ('files', ('重点公司动态_2026-09-30.xlsx', xlsx(WATCH)))]
    return c.post('/api/news/import', headers=h(ws, login), files=files, data={'score': score})


def test_import_dedupes_and_rule_links_without_key(env, monkeypatch):
    c, ws, _ = env
    monkeypatch.delenv('VIP_DEEPSEEK_API_KEY', raising=False)
    assert upload(c, ws, 'viewer@demo').status_code == 403
    r = upload(c, ws)
    assert r.status_code == 200, r.text
    body = r.json()
    assert [f['new_items'] for f in body['files']] == [2, 1]
    assert body['files'][1]['merged_into_events'] == 1          # same happening from two feeds
    assert body['scoring']['rule_only'] == 2 and '未配置模型密钥' in body['scoring']['error']
    again = upload(c, ws).json()
    assert [f['duplicate_items'] for f in again['files']] == [2, 1]
    events = c.get('/api/news/events', headers=h(ws, 'viewer@demo')).json()
    assert len(events) == 2
    main = next(e for e in events if e['item_count'] == 2)
    assert main['ai_status'] == 'rule_only'
    assert [l['company'] for l in main['links']] == ['合成甲制造']
    detail = c.get(f"/api/news/events/{main['id']}", headers=h(ws, 'viewer@demo')).json()
    assert {i['feed'] for i in detail['items']} == {'合成行业每日动态', '重点公司动态'}


def test_ai_scoring_through_openai_compatible_api(env, monkeypatch):
    c, ws, Session = env
    from app.domains.news import service
    from app.domains.news.models import NewsEvent
    monkeypatch.setenv('VIP_DEEPSEEK_API_KEY', 'test-key')
    seen = {}

    def handler(request):
        seen['url'] = str(request.url); seen['auth'] = request.headers['authorization']
        seen['body'] = json.loads(request.content)
        content = json.dumps({'links': [{'company': '合成甲制造', 'ticker': '600001.SH', 'relevance': 0.95, 'impact': 0.6, 'rationale': '新品与指引上调'},
                                        {'company': '名单外公司', 'relevance': 0.5, 'impact': -0.2, 'rationale': '竞品'}]}, ensure_ascii=False)
        return httpx.Response(200, json={'choices': [{'message': {'content': content}}]})

    with Session() as s:
        ids = [e.id for e in s.scalars(select(NewsEvent).where(NewsEvent.item_count == 2)).all()]
        stats = service.score_events(s, ws, event_ids=ids, transport=httpx.MockTransport(handler))
        s.commit()
    assert stats['ai_scored'] == 1 and stats['model'] == 'DeepSeek/deepseek-chat'
    assert seen['url'] == 'https://api.deepseek.com/chat/completions' and seen['auth'] == 'Bearer test-key'
    assert seen['body']['model'] == 'deepseek-chat' and '合成甲制造（600001.SH / 0001.HK）' in seen['body']['messages'][1]['content']
    event = c.get(f'/api/news/events/{ids[0]}', headers=h(ws, 'viewer@demo')).json()
    links = {l['company_label']: l for l in event['links']}
    assert links['合成甲制造']['relevance'] == 0.95 and links['合成甲制造']['impact'] == 0.6
    assert links['合成甲制造']['company_id'] == '00000000-0000-4000-8000-000000000001'
    assert links['名单外公司']['company_id'] is None
    assert event['impact_score'] == pytest.approx(0.57)


def test_human_review(env):
    c, ws, _ = env
    event = next(e for e in c.get('/api/news/events', headers=h(ws, 'viewer@demo')).json() if e['item_count'] == 2)
    links = {l['company_label']: l for l in event['links']}
    path = f"/api/news/links/{links['合成甲制造']['id']}/review"
    assert c.post(path, headers=h(ws, 'viewer@demo'), json={'action': 'confirm'}).status_code == 403
    r = c.post(path, headers=h(ws, 'research@demo'), json={'action': 'confirm', 'impact': 0.8})
    assert r.status_code == 200 and r.json()['status'] == 'confirmed' and r.json()['impact'] == 0.8
    assert c.post(path, headers=h(ws, 'research@demo'), json={'action': 'confirm'}).status_code == 409
    other = f"/api/news/links/{links['名单外公司']['id']}/review"
    assert c.post(other, headers=h(ws, 'research@demo'), json={'action': 'confirm'}).status_code == 422
    assert c.post(other, headers=h(ws, 'research@demo'), json={'action': 'reject'}).json()['status'] == 'rejected'
    needs = c.get('/api/news/events?status=needs_review', headers=h(ws, 'viewer@demo')).json()
    assert all(e['id'] != event['id'] for e in needs)
    by_company = c.get('/api/news/events?company_id=00000000-0000-4000-8000-000000000001', headers=h(ws, 'viewer@demo')).json()
    assert any(e['id'] == event['id'] for e in by_company)


def test_confirm_writes_audit_and_outbox(env):
    _, ws, Session = env
    from app.models.audit import AuditLog, Outbox
    with Session() as s:
        assert s.scalar(select(AuditLog).where(AuditLog.action == 'news.link.confirmed'))
        assert s.scalar(select(Outbox).where(Outbox.event_type == 'news.link.confirmed'))


def test_rss_feed_run(env):
    _, ws, Session = env
    from app.domains.news import service
    rss = '<rss><channel><item><title>合成乙制造签下长期大单</title><link>https://e.com/9</link><pubDate>Wed, 30 Sep 2026 09:00:00 +0800</pubDate></item></channel></rss>'
    with Session() as s:
        feed = service.ensure_feed(s, ws, 'rss-demo', 'RSS 演示', kind='rss', url='https://e.com/rss')
        ok = service.run_feed(s, ws, feed, transport=httpx.MockTransport(lambda r: httpx.Response(200, text=rss)))
        bad = service.run_feed(s, ws, feed, transport=httpx.MockTransport(lambda r: httpx.Response(500)))
        s.commit()
        assert ok['new_items'] == 1 and bad['error'].startswith('抓取失败') and feed.last_status == bad['error']


def test_admin_models_and_feeds(env):
    c, ws, _ = env
    body = {'provider_key': 'qwen', 'name': '通义千问', 'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'model': 'qwen-plus', 'api_key_env': 'VIP_QWEN_API_KEY', 'is_default': True}
    assert c.post('/api/admin/llm-providers', headers=h(ws, 'data@demo'), json=body).status_code == 403
    r = c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'), json=body)
    assert r.status_code == 200 and r.json()['key_configured'] is False
    assert c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'), json=body).status_code == 409
    assert c.post('/api/admin/llm-providers', headers=h(ws, 'admin@demo'), json={**body, 'provider_key': 'x', 'api_key_env': 'lower'}).status_code == 422
    listing = c.get('/api/admin/llm-providers', headers=h(ws, 'admin@demo')).json()
    assert listing['active'] == 'qwen' and listing['builtin_default']['provider_key'] == 'deepseek'
    from app.domains.news import service
    _, _, Session = env
    with Session() as s:
        assert service.resolve_provider(s, ws).model == 'qwen-plus'
    pid = r.json()['id']
    assert c.put(f'/api/admin/llm-providers/{pid}', headers=h(ws, 'admin@demo'), json={**body, 'enabled': False}).json()['enabled'] is False
    with Session() as s:
        assert service.resolve_provider(s, ws).provider_key == 'deepseek'
    f = c.post('/api/admin/news-feeds', headers=h(ws, 'data@demo'), json={'feed_key': 'rss-2', 'name': 'RSS 2', 'url': 'https://e.com/r'})
    assert f.status_code == 200
    assert any(x['feed_key'] == 'rss-2' for x in c.get('/api/news/feeds', headers=h(ws, 'viewer@demo')).json())
    assert any(s['key'] == 'news-rss' for s in c.get('/api/admin/sources', headers=h(ws, 'data@demo')).json())
