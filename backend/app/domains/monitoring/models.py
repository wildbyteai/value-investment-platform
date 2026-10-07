"""监控告警 tables."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StrikeZoneState(Base):
    """Last observed zone per security, so a scan can tell what changed."""
    __tablename__ = 'strike_zone_state'
    __table_args__ = (UniqueConstraint('workspace_id', 'security_id', name='uq_strike_zone_state'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    security_id: Mapped[str] = mapped_column(ForeignKey('security.id'), nullable=False)
    zone: Mapped[str] = mapped_column(String(20), nullable=False)
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default='{}')
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Alert(Base):
    """A ball that landed in (or left) the strike zone."""
    __tablename__ = 'alert'
    __table_args__ = (UniqueConstraint('workspace_id', 'dedupe_key', name='uq_alert_dedupe'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)  # news_hit | zone_enter | zone_exit
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default='high')
    zone: Mapped[str] = mapped_column(String(20), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey('company.id'), nullable=False)
    security_id: Mapped[str | None] = mapped_column(ForeignKey('security.id'), nullable=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey('news_event.id'), nullable=True)
    link_id: Mapped[str | None] = mapped_column(ForeignKey('news_event_company.id'), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class Notification(Base):
    """One delivery of one alert to one person on one channel."""
    __tablename__ = 'notification'
    __table_args__ = (UniqueConstraint('alert_id', 'user_id', 'channel', name='uq_notification_delivery'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    alert_id: Mapped[str] = mapped_column(ForeignKey('alert.id'), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('app_user.id'), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # inapp | email
    status: Mapped[str] = mapped_column(String(20), nullable=False)   # inapp: unread|read  email: pending|sent|failed|skipped
    address: Mapped[str | None] = mapped_column(String(320), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class NotificationSetting(Base):
    """Per person: where to email alerts and which channels are on."""
    __tablename__ = 'notification_setting'
    __table_args__ = (UniqueConstraint('workspace_id', 'user_id', name='uq_notification_setting'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey('app_user.id'), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    inapp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())
