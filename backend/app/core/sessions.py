"""Server-side sessions behind an HttpOnly cookie, plus sign-in throttling."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.config import get_settings
from app.models.identity import AuthSession, LoginAttempt, User

COOKIE = 'vip_session'
# Throttle: per account and per client address, inside a sliding window.
WINDOW = timedelta(minutes=15)
MAX_FAILS_PER_LOGIN = 5
MAX_FAILS_PER_IP = 20


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def throttled(db, login: str, ip: str | None, now: datetime) -> bool:
    since = now - WINDOW
    fails = select(func.count()).select_from(LoginAttempt).where(LoginAttempt.success.is_(False), LoginAttempt.created_at >= since)
    if db.scalar(fails.where(LoginAttempt.login == login)) >= MAX_FAILS_PER_LOGIN:
        return True
    return bool(ip) and db.scalar(fails.where(LoginAttempt.ip == ip)) >= MAX_FAILS_PER_IP


def note_attempt(db, login: str, ip: str | None, success: bool, now: datetime) -> None:
    db.add(LoginAttempt(login=login[:120], ip=ip, success=success, created_at=now))
    db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < now - timedelta(days=30)))


def create(db, user: User, ip: str | None, user_agent: str | None, now: datetime) -> str:
    s = get_settings()
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=_digest(token), user_id=user.id, created_at=now, last_seen_at=now,
                       expires_at=now + timedelta(hours=s.session_max_hours), ip=ip, user_agent=(user_agent or '')[:300]))
    db.execute(delete(AuthSession).where(AuthSession.expires_at < now))
    return token


def resolve(db, token: str | None, now: datetime | None = None) -> User | None:
    if not token:
        return None
    now = now or datetime.now(timezone.utc)
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == _digest(token)))
    if row is None:
        return None
    idle = timedelta(minutes=get_settings().session_idle_minutes)
    if row.expires_at <= now or row.last_seen_at + idle <= now:
        db.delete(row)
        db.commit()
        return None
    user = db.get(User, row.user_id)
    if user is None or user.disabled:
        return None
    if now - row.last_seen_at > timedelta(minutes=1):
        row.last_seen_at = now
        db.commit()
    return user


def revoke(db, token: str | None) -> None:
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == _digest(token)))


def revoke_user(db, user_id: str, keep_token: str | None = None) -> None:
    q = delete(AuthSession).where(AuthSession.user_id == user_id)
    if keep_token:
        q = q.where(AuthSession.token_hash != _digest(keep_token))
    db.execute(q)


def set_cookie(response, token: str) -> None:
    s = get_settings()
    response.set_cookie(COOKIE, token, max_age=s.session_max_hours * 3600, httponly=True, secure=s.cookie_secure,
                        samesite='strict', path='/')


def clear_cookie(response) -> None:
    s = get_settings()
    response.delete_cookie(COOKIE, path='/', httponly=True, secure=s.cookie_secure, samesite='strict')
