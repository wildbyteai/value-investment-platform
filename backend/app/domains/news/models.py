"""资讯雷达 tables: feed → item → event → event-company link, plus model providers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class NewsFeed(Base):
    """One source of news: a daily Excel upload channel, an RSS URL, ..."""
    __tablename__ = 'news_feed'
    __table_args__ = (UniqueConstraint('workspace_id', 'feed_key', name='uq_news_feed_key'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    feed_key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False, default='excel_upload')  # excel_upload | rss
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    schedule: Mapped[str | None] = mapped_column(String(60), nullable=True)  # e.g. "daily 08:30"
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default='{}')
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class NewsEvent(Base):
    """A real-world happening; several items from different feeds collapse into one event."""
    __tablename__ = 'news_event'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default='')
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(500), nullable=False)
    first_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_status: Mapped[str] = mapped_column(String(30), nullable=False, default='pending')  # pending | scored | rule_only | failed
    ai_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ai_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class NewsItem(Base):
    """One normalized row from one feed."""
    __tablename__ = 'news_item'
    __table_args__ = (UniqueConstraint('workspace_id', 'content_hash', name='uq_news_item_hash'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    feed_id: Mapped[str] = mapped_column(ForeignKey('news_feed.id'), nullable=False)
    event_id: Mapped[str] = mapped_column(ForeignKey('news_event.id'), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default='')
    source_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    company_hint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class NewsEventCompany(Base):
    """Which company an event touches, how closely (relevance 0..1) and how hard (impact -1..1)."""
    __tablename__ = 'news_event_company'
    __table_args__ = (UniqueConstraint('event_id', 'company_label', name='uq_news_event_company'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey('news_event.id'), nullable=False, index=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey('company.id'), nullable=True)
    company_label: Mapped[str] = mapped_column(String(200), nullable=False)
    ticker_hint: Mapped[str | None] = mapped_column(String(60), nullable=True)
    relevance: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    impact: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default='')
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='proposed')  # proposed | confirmed | rejected
    proposed_by: Mapped[str] = mapped_column(String(120), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class LlmProvider(Base):
    """An OpenAI-compatible chat model. The API key is read from an environment variable,
    never stored in the database."""
    __tablename__ = 'llm_provider'
    __table_args__ = (UniqueConstraint('workspace_id', 'provider_key', name='uq_llm_provider_key'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    api_key_env: Mapped[str] = mapped_column(String(120), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    options_json: Mapped[str] = mapped_column(Text, nullable=False, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())
