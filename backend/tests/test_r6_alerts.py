"""R6 监控告警: only balls inside the strike zone alert; in-app + e-mail delivery."""
import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.domains.monitoring import service
from app.models.monitoring import Alert, Notification
from app.domains.monitoring.policy import sender_address
from app.domains.strategy import zone_service

A_ID = '00000000-0000-4000-8000-000000000001'


def row(zone, security='sec-a', ticker='600001.SH', market='CN_A'):
    return {'company_id': A_ID, 'company': '合成甲制造', 'industry_key': 'manufacturing', 'security_id': security,
            'ticker': ticker, 'market': market, 'zone': zone, 'label': {'sweet': '甜区', 'edge': '边角球', 'outside': '区外'}[zone],
            'margin_of_safety': '0.35', 'checks': [{'key': 'circle', 'label': '能力圈', 'passed': True, 'detail': 'ok'},
                                                   {'key': 'business', 'label': '好生意', 'passed': True, 'detail': 'ok'},
                                                   {'key': 'margin', 'label': '安全边际', 'passed': zone == 'sweet', 'detail': '35%'}]}


class FakeMailer:
    def __init__(self, configured=True, fail=False):
        self.configured, self.fail, self.sent = configured, fail, []

    def send(self, to, subject, body):
        if self.fail:
            raise ConnectionError('down')
        self.sent.append((to, subject, body))


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
        from app.models.company import Security
        secs = {x.market: x.id for x in s.scalars(select(Security).where(Security.company_id == A_ID)).all()}
    with engine.connect() as conn:
        ws = str(conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one())
    with TestClient(app) as c:
        yield c, ws, Session, secs
    Base.metadata.drop_all(bind=engine)


def h(ws, login):
    return {'X-Vip-Login': login, 'X-Vip-Workspace': ws}


def test_sender_defaults_to_admin_address():
    assert sender_address() == 'admin@bytewatcher.xyz'


def test_zone_scan_baseline_then_enter_and_exit(env, monkeypatch):
    c, ws, Session, secs = env
    assert c.put('/api/notifications/settings', headers=h(ws, 'research@demo'),
                 json={'email': 'r@example.com', 'email_enabled': True, 'inapp_enabled': True}).status_code == 200
    assert c.put('/api/notifications/settings', headers=h(ws, 'research@demo'), json={'email': 'bad'}).status_code == 422
    seq = iter([[row('edge', secs['CN_A']), row('outside', secs['HK'], '0001.HK', 'HK')],
                [row('sweet', secs['CN_A']), row('outside', secs['HK'], '0001.HK', 'HK')],
                [row('sweet', secs['CN_A']), row('outside', secs['HK'], '0001.HK', 'HK')],
                [row('edge', secs['CN_A']), row('outside', secs['HK'], '0001.HK', 'HK')]])
    monkeypatch.setattr(zone_service, 'evaluate_workspace', lambda db, w, at: next(seq))
    results = []
    with Session() as s:
        for _ in range(4):
            results.append(service.scan_zones(s, ws)); s.commit()
        alerts = s.scalars(select(Alert).where(Alert.workspace_id == ws).order_by(Alert.created_at)).all()
        assert [r['baseline'] for r in results] == [2, 0, 0, 0]          # first look is silent
        assert [a.kind for a in alerts] == ['zone_enter', 'zone_exit']
        assert alerts[0].title == '进入甜区：合成甲制造 600001.SH'
        deliveries = s.scalars(select(Notification).where(Notification.alert_id == alerts[0].id)).all()
        by_channel = sorted((n.channel, n.status) for n in deliveries)
        assert ('email', 'pending') in by_channel and ('inapp', 'unread') in by_channel
        assert len([n for n in deliveries if n.channel == 'inapp']) == 3  # researcher, strategy_manager, system_admin


def test_email_delivery_skip_fail_send(env):
    _, ws, Session, _ = env
    with Session() as s:
        assert service.deliver_emails(s, FakeMailer(fail=True))['failed'] == 2
        s.commit()
        mailer = FakeMailer()
        assert service.deliver_emails(s, mailer)['sent'] == 2
        s.commit()
        to, subject, body = mailer.sent[0]
        assert to == 'r@example.com' and subject.startswith('【价投宝】') and '不构成交易指令' in body
        assert service.deliver_emails(s, mailer)['sent'] == 0           # never sent twice


def test_unconfigured_smtp_marks_skipped(env):
    _, ws, Session, secs = env
    with Session() as s:
        alert = service._create_alert(s, ws, kind='zone_enter', zone='sweet', row=row('sweet', secs['CN_A']),
                                      title='t', body='b', dedupe_key='manual-test')
        assert service._create_alert(s, ws, kind='zone_enter', zone='sweet', row=row('sweet', secs['CN_A']),
                                     title='t', body='b', dedupe_key='manual-test') is None
        assert service.deliver_emails(s, FakeMailer(configured=False))['skipped'] == 1
        n = s.scalar(select(Notification).where(Notification.alert_id == alert.id, Notification.channel == 'email'))
        assert n.status == 'skipped' and 'SMTP' in n.last_error
        s.rollback()


TITLES = {0.7: '合成甲制造获得海外大额长期订单', 0.1: '合成甲制造董事会例行换届完成', -0.9: '合成甲制造主要工厂突发停产检修'}


def _confirmed_link(c, ws, Session, impact):
    from app.domains.news import service as news
    from app.domains.news.normalize import Record
    with Session() as s:
        feed = news.ensure_feed(s, ws, f'feed-{impact}')
        news.ingest(s, ws, feed, [Record(title=TITLES[impact], summary='合成甲制造（600001.SH）',
                                         published_at=datetime.now(timezone.utc))])
        news.score_events(s, ws)  # no key -> rule link
        s.commit()
    event = next(e for e in c.get('/api/news/events', headers=h(ws, 'viewer@demo')).json() if e['title'] == TITLES[impact])
    return event['links'][0]['id'], event['id']


def test_confirmed_news_alerts_only_inside_zone(env, monkeypatch):
    c, ws, Session, secs = env
    monkeypatch.delenv('VIP_DEEPSEEK_API_KEY', raising=False)
    zones = {'value': [row('sweet', secs['CN_A']), row('outside', secs['HK'], '0001.HK', 'HK')]}
    monkeypatch.setattr(zone_service, 'evaluate_company', lambda db, w, cid, at: zones['value'])
    link_id, event_id = _confirmed_link(c, ws, Session, 0.7)
    r = c.post(f'/api/news/links/{link_id}/review', headers=h(ws, 'research@demo'), json={'action': 'confirm', 'impact': 0.7})
    assert r.status_code == 200 and r.json()['alerts'] == 1           # only the A-share is in the sweet spot
    alerts = c.get('/api/alerts', headers=h(ws, 'viewer@demo')).json()
    hit = next(a for a in alerts if a['kind'] == 'news_hit')
    assert hit['event_id'] == event_id and hit['title'].startswith('甜区利好：合成甲制造 600001.SH') and hit['zone_label'] == '甜区'
    # weak impact: confirmed but not a ball worth swinging at
    weak_id, _ = _confirmed_link(c, ws, Session, 0.1)
    assert c.post(f'/api/news/links/{weak_id}/review', headers=h(ws, 'research@demo'), json={'action': 'confirm', 'impact': 0.1}).json()['alerts'] == 0
    # strong impact but company outside the zone
    zones['value'] = [row('outside', secs['CN_A'])]
    out_id, _ = _confirmed_link(c, ws, Session, -0.9)
    assert c.post(f'/api/news/links/{out_id}/review', headers=h(ws, 'research@demo'), json={'action': 'confirm', 'impact': -0.9}).json()['alerts'] == 0
    # re-scanning never duplicates
    with Session() as s:
        zones['value'] = [row('sweet', secs['CN_A'])]
        again = service.scan_news(s, ws, link_ids=[link_id]); s.commit()
        assert again['alerts'] == 0


def test_inbox_read_and_permissions(env):
    c, ws, _, _ = env
    box = c.get('/api/notifications', headers=h(ws, 'research@demo')).json()
    assert box['unread'] >= 2 and box['items'][0]['alert']['title']
    first = box['items'][0]['id']
    assert c.post(f'/api/notifications/{first}/read', headers=h(ws, 'strat@demo')).status_code == 404  # not theirs
    assert c.post(f'/api/notifications/{first}/read', headers=h(ws, 'research@demo')).json()['marked'] == 1
    assert c.post('/api/notifications/read-all', headers=h(ws, 'research@demo')).json()['marked'] == box['unread'] - 1
    assert c.get('/api/notifications', headers=h(ws, 'research@demo')).json()['unread'] == 0
    assert c.get('/api/notifications', headers=h(ws, 'viewer@demo')).json()['unread'] == 0       # viewers are not recipients
    assert c.post('/api/alerts/scan', headers=h(ws, 'viewer@demo')).status_code == 403
    admin = c.get('/api/admin/notify', headers=h(ws, 'admin@demo')).json()
    assert admin['sender'] == 'admin@bytewatcher.xyz' and admin['smtp_configured'] is False
    assert any(r['email'] == 'r@example.com' for r in admin['recipients'])
    assert c.get('/api/admin/notify', headers=h(ws, 'data@demo')).status_code == 403


def test_scan_endpoint_runs_real_zone_service(env):
    c, ws, _, _ = env
    r = c.post('/api/alerts/scan', headers=h(ws, 'strat@demo'))
    assert r.status_code == 200, r.text
    assert set(r.json()) == {'zones', 'news', 'email'}


def test_major_negative_on_edge_and_hard_risk_veto(env, monkeypatch):
    c, ws, Session, secs = env
    zones = {'value': [row('edge', secs['CN_A'])]}
    monkeypatch.setattr(zone_service, 'evaluate_company', lambda db, w, cid, at: zones['value'])
    TITLES[-0.6] = '合成甲制造遭遇监管立案调查'
    link_id, _ = _confirmed_link(c, ws, Session, -0.6)
    r = c.post(f'/api/news/links/{link_id}/review', headers=h(ws, 'research@demo'), json={'action': 'confirm', 'impact': -0.6})
    assert r.json()['alerts'] == 1
    assert any(a['title'].startswith('边角球利空') for a in c.get('/api/alerts', headers=h(ws, 'viewer@demo')).json())
    vetoed = row('outside', secs['HK'], '0001.HK', 'HK')
    vetoed['checks'][1] = {'key': 'business', 'label': '好生意', 'passed': False, 'detail': '硬风险一票否决：confirmed_fraud'}
    seq = iter([[row('edge', secs['HK'], '0001.HK', 'HK')], [vetoed]])
    monkeypatch.setattr(zone_service, 'evaluate_workspace', lambda db, w, at: next(seq))
    with Session() as s:
        s.query(service.StrikeZoneState).filter_by(workspace_id=ws, security_id=secs['HK']).delete()
        service.scan_zones(s, ws); stats = service.scan_zones(s, ws); s.commit()
        assert stats['alerts'] == 1
        assert s.scalar(select(Alert).where(Alert.kind == 'hard_risk')).title == '硬风险否决：合成甲制造 0001.HK'
