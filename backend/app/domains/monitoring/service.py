"""监控告警: only balls that land in the strike zone raise an alert.

Sources of balls:
- ``scan_zones``: a security enters (or leaves) the sweet spot since the last scan.
  The first observation of a security is a silent baseline.
  A confirmed hard risk that throws a sweet/edge security out is its own alert.
- ``scan_news``: a human-confirmed news link with enough relevance and impact hits a
  company whose security is in the sweet spot right now, or a major negative event
  (impact ≤ -0.5) hits one on the edge.

Each alert fans out to in-app notifications and e-mails for the configured roles.
Alerts are idempotent through ``dedupe_key``. Never commits.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.core.errors import NotFound
from app.models.monitoring import Alert, Notification, NotificationSetting, StrikeZoneState
from app.domains.monitoring.policy import policy
from app.models.news import NewsEvent, NewsEventCompany
from app.domains.strategy import strike_zone, zone_service
from app.models.identity import Membership, User
from app.domains.platform.transactions import canonical, record

ZONE_LABEL = strike_zone.LABELS


def _checks_text(row) -> str:
    return '\n'.join(f"- {c['label']}：{'✓' if c['passed'] else '✗' if c['passed'] is False else '？'} {c['detail']}" for c in row['checks'])


def _create_alert(db, workspace_id, *, kind, zone, row, title, body, dedupe_key, severity='high', event_id=None, link_id=None):
    if db.scalar(select(Alert.id).where(Alert.workspace_id == workspace_id, Alert.dedupe_key == dedupe_key)):
        return None
    alert = Alert(workspace_id=workspace_id, kind=kind, severity=severity, zone=zone, company_id=row['company_id'],
                  security_id=row.get('security_id'), event_id=event_id, link_id=link_id, title=title[:500],
                  body=body, dedupe_key=dedupe_key)
    db.add(alert)
    db.flush()
    fan_out(db, alert)
    record(db, workspace_id, None, f'alert.{kind}', 'alert', alert.id, {'zone': zone, 'dedupe_key': dedupe_key})
    return alert


def recipients(db, workspace_id) -> list[tuple[User, NotificationSetting | None]]:
    roles = policy()['recipient_roles']
    users = db.scalars(select(User).join(Membership, Membership.user_id == User.id).where(
        Membership.workspace_id == workspace_id, Membership.role.in_(roles)).distinct().order_by(User.login)).all()
    settings = {s.user_id: s for s in db.scalars(select(NotificationSetting).where(NotificationSetting.workspace_id == workspace_id)).all()}
    return [(u, settings.get(u.id)) for u in users]


def fan_out(db, alert: Alert) -> int:
    n = 0
    for user, setting in recipients(db, alert.workspace_id):
        if setting is None or setting.inapp_enabled:
            db.add(Notification(workspace_id=alert.workspace_id, alert_id=alert.id, user_id=user.id, channel='inapp', status='unread'))
            n += 1
        if setting is not None and setting.email_enabled and setting.email:
            db.add(Notification(workspace_id=alert.workspace_id, alert_id=alert.id, user_id=user.id, channel='email',
                                status='pending', address=setting.email))
            n += 1
    db.flush()
    return n


# ------------------------------------------------------------------ zone changes

def scan_zones(db, workspace_id, at: datetime | None = None) -> dict:
    at = at or datetime.now(timezone.utc)
    cfg = policy()['zone_change']
    rows = zone_service.evaluate_workspace(db, workspace_id, at)
    states = {s.security_id: s for s in db.scalars(select(StrikeZoneState).where(StrikeZoneState.workspace_id == workspace_id)).all()}
    stats = {'securities': len(rows), 'baseline': 0, 'changed': 0, 'alerts': 0}
    for row in rows:
        state = states.get(row['security_id'])
        detail = canonical({'checks': row['checks'], 'margin_of_safety': row['margin_of_safety']})
        if state is None:
            db.add(StrikeZoneState(workspace_id=workspace_id, security_id=row['security_id'], zone=row['zone'],
                                   detail_json=detail, observed_at=at))
            stats['baseline'] += 1
            if not cfg['initial_baseline_notify']:
                continue
            previous = None
        else:
            previous = state.zone
            state.detail_json, state.observed_at = detail, at
            if previous == row['zone']:
                continue
            state.zone = row['zone']
        stats['changed'] += 1
        name = f"{row['company']} {row['ticker']}"
        vetoed = row['zone'] == strike_zone.OUTSIDE and any(c['key'] == 'business' and '硬风险' in c['detail'] for c in row['checks'])
        if vetoed and previous in cfg['hard_risk_from']:
            alert = _create_alert(db, workspace_id, kind='hard_risk', zone=row['zone'], row=row,
                                  title=f"硬风险否决：{name}",
                                  body=f"{name} 出现已确认硬风险，从{ZONE_LABEL[previous]}直接出区。\n{_checks_text(row)}",
                                  dedupe_key=f"risk:{row['security_id']}:{at.date().isoformat()}")
        elif row['zone'] in cfg['notify_on_enter']:
            alert = _create_alert(db, workspace_id, kind='zone_enter', zone=row['zone'], row=row,
                                  title=f"进入{ZONE_LABEL[row['zone']]}：{name}",
                                  body=f"{name} 从{ZONE_LABEL.get(previous, '未观察')}进入{ZONE_LABEL[row['zone']]}。\n{_checks_text(row)}",
                                  dedupe_key=f"zone:{row['security_id']}:{row['zone']}:{at.date().isoformat()}")
        elif previous in cfg['notify_on_exit_from']:
            alert = _create_alert(db, workspace_id, kind='zone_exit', zone=row['zone'], row=row, severity='medium',
                                  title=f"离开{ZONE_LABEL[previous]}：{name}",
                                  body=f"{name} 从{ZONE_LABEL[previous]}变为{ZONE_LABEL[row['zone']]}。\n{_checks_text(row)}",
                                  dedupe_key=f"zone-exit:{row['security_id']}:{previous}:{at.date().isoformat()}")
        else:
            alert = None
        stats['alerts'] += 1 if alert else 0
    db.flush()
    return stats


# ------------------------------------------------------------------ news hits

def _news_candidates(db, workspace_id, at, link_ids=None):
    cfg = policy()['news_hit']
    q = (select(NewsEventCompany, NewsEvent).join(NewsEvent, NewsEvent.id == NewsEventCompany.event_id)
         .where(NewsEvent.workspace_id == workspace_id, NewsEventCompany.status == 'confirmed',
                NewsEventCompany.company_id.is_not(None)))
    if link_ids:
        q = q.where(NewsEventCompany.id.in_(link_ids))
    else:
        q = q.where(NewsEventCompany.reviewed_at >= at - timedelta(days=cfg['lookback_days']))
    for link, event in db.execute(q).all():
        if link.relevance is None or link.impact is None:
            continue
        if Decimal(str(link.relevance)) < Decimal(cfg['minimum_relevance']) or abs(Decimal(str(link.impact))) < Decimal(cfg['minimum_abs_impact']):
            continue
        yield link, event


def scan_news(db, workspace_id, at: datetime | None = None, link_ids=None) -> dict:
    at = at or datetime.now(timezone.utc)
    cfg = policy()['news_hit']
    zones, negative_zones, major_negative = cfg['zones'], cfg['major_negative_zones'], Decimal(cfg['major_negative_impact'])
    stats = {'links': 0, 'in_zone': 0, 'alerts': 0}
    for link, event in _news_candidates(db, workspace_id, at, link_ids):
        stats['links'] += 1
        try:
            rows = zone_service.evaluate_company(db, workspace_id, link.company_id, at)
        except NotFound:
            continue
        impact = Decimal(str(link.impact))
        for row in rows:
            in_zone = row['zone'] in zones
            major_bad = row['zone'] in negative_zones and impact <= major_negative
            if not (in_zone or major_bad):
                continue  # 区外的球、边角球的一般消息只记录在资讯雷达，不告警
            stats['in_zone'] += 1
            direction = '利好' if impact > 0 else '利空'
            name = f"{row['company']} {row['ticker']}"
            alert = _create_alert(
                db, workspace_id, kind='news_hit', zone=row['zone'], row=row, event_id=event.id, link_id=link.id,
                severity='high', title=f"{ZONE_LABEL[row['zone']]}{direction}：{name}｜{event.title}",
                body=(f"事件：{event.title}\n{event.summary[:600]}\n\n关联度 {Decimal(str(link.relevance)):.2f}，"
                      f"影响分 {impact:+.2f}（{direction}）。{link.rationale}\n\n{name} 当前在{ZONE_LABEL[row['zone']]}：\n{_checks_text(row)}"),
                dedupe_key=f"news:{link.id}:{row['security_id']}")
            stats['alerts'] += 1 if alert else 0
    db.flush()
    return stats


# ------------------------------------------------------------------ delivery

def email_text(alert: Alert) -> tuple[str, str]:
    prefix = policy()['email']['subject_prefix']
    return f'{prefix}{alert.title}'[:300], alert.body + '\n\n——\n价投宝 监控告警。研究提醒，不构成交易指令。'


def deliver_emails(db, mailer, limit=100) -> dict:
    max_attempts = policy()['email']['max_attempts']
    rows = db.scalars(select(Notification).where(Notification.channel == 'email', Notification.status.in_(('pending', 'failed')),
                                                 Notification.attempts < max_attempts).order_by(Notification.created_at).limit(limit)
                      .with_for_update(skip_locked=True)).all()
    stats = {'sent': 0, 'failed': 0, 'skipped': 0}
    for n in rows:
        if not mailer.configured:
            n.status, n.last_error = 'skipped', '未配置 SMTP（VIP_SMTP_HOST）'
            stats['skipped'] += 1
            continue
        alert = db.get(Alert, n.alert_id)
        subject, body = email_text(alert)
        n.attempts += 1
        try:
            mailer.send(n.address, subject, body)
            n.status, n.sent_at, n.last_error = 'sent', datetime.now(timezone.utc), None
            stats['sent'] += 1
        except Exception as exc:  # network/auth errors are retried up to max_attempts
            n.status, n.last_error = 'failed', type(exc).__name__
            stats['failed'] += 1
    db.flush()
    return stats


def scan_all(db, workspace_id, mailer, at=None) -> dict:
    return {'zones': scan_zones(db, workspace_id, at), 'news': scan_news(db, workspace_id, at),
            'email': deliver_emails(db, mailer)}


# ------------------------------------------------------------------ reads & inbox

def alert_dict(a: Alert, names: dict) -> dict:
    return {'id': a.id, 'kind': a.kind, 'severity': a.severity, 'zone': a.zone, 'zone_label': ZONE_LABEL.get(a.zone, a.zone),
            'company_id': a.company_id, 'company': names.get(a.company_id), 'security_id': a.security_id,
            'event_id': a.event_id, 'title': a.title, 'body': a.body, 'created_at': a.created_at.isoformat()}


def list_alerts(db, workspace_id, limit=50) -> list[dict]:
    from app.domains.news.service import company_names
    names = company_names(db)
    rows = db.scalars(select(Alert).where(Alert.workspace_id == workspace_id).order_by(Alert.created_at.desc()).limit(limit)).all()
    out = []
    for a in rows:
        d = alert_dict(a, names)
        d['deliveries'] = dict(db.execute(select(Notification.status, func.count()).where(
            Notification.alert_id == a.id, Notification.channel == 'email').group_by(Notification.status)).all())
        out.append(d)
    return out


def inbox(db, workspace_id, user_id, limit=50) -> dict:
    from app.domains.news.service import company_names
    names = company_names(db)
    rows = db.execute(select(Notification, Alert).join(Alert, Alert.id == Notification.alert_id).where(
        Notification.workspace_id == workspace_id, Notification.user_id == user_id, Notification.channel == 'inapp')
        .order_by(Notification.created_at.desc()).limit(limit)).all()
    unread = db.scalar(select(func.count()).select_from(Notification).where(
        Notification.workspace_id == workspace_id, Notification.user_id == user_id,
        Notification.channel == 'inapp', Notification.status == 'unread'))
    return {'unread': unread, 'items': [{'id': n.id, 'status': n.status, 'read_at': n.read_at.isoformat() if n.read_at else None,
                                         'alert': alert_dict(a, names)} for n, a in rows]}


def mark_read(db, workspace_id, user_id, notification_id=None) -> int:
    q = select(Notification).where(Notification.workspace_id == workspace_id, Notification.user_id == user_id,
                                   Notification.channel == 'inapp', Notification.status == 'unread')
    if notification_id:
        q = q.where(Notification.id == notification_id)
    rows = db.scalars(q).all()
    if notification_id and not rows:
        exists = db.scalar(select(Notification.id).where(Notification.id == notification_id, Notification.user_id == user_id,
                                                         Notification.workspace_id == workspace_id))
        if not exists:
            raise NotFound('没有该通知')
    now = datetime.now(timezone.utc)
    for n in rows:
        n.status, n.read_at = 'read', now
    db.flush()
    return len(rows)


def get_setting(db, workspace_id, user_id) -> NotificationSetting:
    s = db.scalar(select(NotificationSetting).where(NotificationSetting.workspace_id == workspace_id, NotificationSetting.user_id == user_id))
    if s is None:
        s = NotificationSetting(workspace_id=workspace_id, user_id=user_id, email=None, email_enabled=True, inapp_enabled=True)
        db.add(s)
        db.flush()
    return s
