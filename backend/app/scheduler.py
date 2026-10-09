"""One long-running process instead of host cron, for the Docker deployment.

    python -m app.scheduler

* every 5 minutes: ``collect`` (each 采集定时器 keeps its own schedule; this only checks who is due)
* every 15 minutes: ``alerts``
* daily at VIP_NEWS_AT (default 08:30 Asia/Shanghai): ``news`` (RSS feeds + AI scoring)

A failing job is logged and retried at its next slot; it never stops the loop. Overlapping
instances are safe (collectors are claimed with SKIP LOCKED), but run only one anyway.
"""
import logging
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app import jobs

log = logging.getLogger('vip.scheduler')
TZ = ZoneInfo('Asia/Shanghai')
EVERY = {'collect': timedelta(minutes=5), 'alerts': timedelta(minutes=15)}


def _daily_next(now: datetime, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(':'))
    at = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return at if at > now else at + timedelta(days=1)


def _run(name: str) -> None:
    try:
        result = getattr(jobs, name)()
        log.info('%s ok: %s item(s)', name, len(result))
    except Exception:  # keep the loop alive
        log.exception('%s failed', name)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
    news_at = os.environ.get('VIP_NEWS_AT', '08:30')
    now = datetime.now(TZ)
    due = {'collect': now, 'alerts': now + timedelta(minutes=1), 'news': _daily_next(now, news_at)}
    log.info('scheduler started; news daily at %s Asia/Shanghai', news_at)
    while True:
        now = datetime.now(TZ)
        for name, at in sorted(due.items(), key=lambda kv: kv[1]):
            if at <= now:
                _run(name)
                due[name] = _daily_next(datetime.now(TZ), news_at) if name == 'news' else now + EVERY[name]
        time.sleep(max(1.0, min((at - datetime.now(TZ)).total_seconds() for at in due.values())))


if __name__ == '__main__':
    main()
