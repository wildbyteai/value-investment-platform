"""Scheduled jobs: ``python -m app.jobs news`` (cron, e.g. every morning 08:30 Asia/Shanghai).

Runs every enabled RSS feed in every workspace, then scores pending events.
``python -m app.jobs alerts`` (e.g. every 30 min in trading hours, and after the close):
scans strike-zone changes and confirmed news in every workspace, then sends e-mails.
"""
import argparse

from sqlalchemy import select

from app.core.uow import unit_of_work
from app.db import SessionLocal


def news() -> list[dict]:
    from app.domains.news import service
    from app.domains.news.models import NewsFeed
    out = []
    with SessionLocal() as db:
        feeds = db.scalars(select(NewsFeed).where(NewsFeed.enabled.is_(True), NewsFeed.kind == 'rss')).all()
        workspaces = sorted({f.workspace_id for f in feeds})
        for feed in feeds:
            with unit_of_work(db):
                out.append({'feed': feed.feed_key, **service.run_feed(db, feed.workspace_id, feed)})
        for ws in workspaces:
            with unit_of_work(db):
                out.append({'workspace': ws, 'scoring': service.score_events(db, ws, limit=100)})
    return out


def alerts() -> list[dict]:
    from app.domains.monitoring import service
    from app.domains.monitoring.mailer import SmtpMailer
    from app.models.identity import Workspace
    out = []
    with SessionLocal() as db:
        for ws in db.scalars(select(Workspace.id)).all():
            with unit_of_work(db):
                out.append({'workspace': ws, **service.scan_all(db, ws, SmtpMailer())})
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('job', choices=['news', 'alerts'])
    args = parser.parse_args()
    for line in {'news': news, 'alerts': alerts}[args.job]():
        print(line)
