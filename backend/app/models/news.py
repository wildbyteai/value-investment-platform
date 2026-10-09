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
    """An OpenAI-compatible chat model. The API key is either saved on the page (AES-GCM
    ciphertext under the server master key ``VIP_SECRET_KEY``, never returned by the API) or
    read from the environment variable ``api_key_env``; the page-saved key wins."""
    __tablename__ = 'llm_provider'
    __table_args__ = (UniqueConstraint('workspace_id', 'provider_key', name='uq_llm_provider_key'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    api_key_env: Mapped[str | None] = mapped_column(String(120), nullable=True)
    api_key_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_key_hint: Mapped[str | None] = mapped_column(String(8), nullable=True)  # last 4 characters only
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    options_json: Mapped[str] = mapped_column(Text, nullable=False, default='{}')
    # How the model reaches the web: one of app.domains.news.agent.SEARCH_MODES (none, qwen_enable_search, …)
    search_mode: Mapped[str] = mapped_column(String(30), nullable=False, default='none', server_default='none')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class LlmSceneBinding(Base):
    """Which model a workspace uses for one scene (config/model-scenes-v1.json). No row means
    the scene follows the workspace default model, then the built-in default."""
    __tablename__ = 'llm_scene_binding'
    __table_args__ = (UniqueConstraint('workspace_id', 'scene_key', name='uq_llm_scene_binding'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    scene_key: Mapped[str] = mapped_column(String(60), nullable=False)
    provider_id: Mapped[str] = mapped_column(ForeignKey('llm_provider.id'), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class AgentSkill(Base):
    """A reusable procedure (markdown steps) the model follows when a collector runs."""
    __tablename__ = 'agent_skill'
    __table_args__ = (UniqueConstraint('workspace_id', 'skill_key', name='uq_agent_skill_key'),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    skill_key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default='')
    body: Mapped[str] = mapped_column(Text, nullable=False, default='')
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class CollectorTask(Base):
    """A scheduled news collector: prompt + model (+ optional skill) on a schedule.

    Each collector writes into its own ``news_feed`` (kind ``agent``) so items stay attributable."""
    __tablename__ = 'collector_task'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[str | None] = mapped_column(ForeignKey('llm_provider.id'), nullable=True)
    skill_id: Mapped[str | None] = mapped_column(ForeignKey('agent_skill.id'), nullable=True)
    feed_id: Mapped[str] = mapped_column(ForeignKey('news_feed.id'), nullable=False)
    # schedule: {"type": "daily", "times": ["08:30"], "weekdays": [1..7]} | {"type": "interval", "minutes": 120}
    schedule_json: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class CollectorRun(Base):
    """One execution of a collector, kept for troubleshooting."""
    __tablename__ = 'collector_run'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    task_id: Mapped[str] = mapped_column(ForeignKey('collector_task.id'), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(20), nullable=False)  # schedule | manual
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='running')  # running | succeeded | failed
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    search_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    skill_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    skill_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stats_json: Mapped[str] = mapped_column(Text, nullable=False, default='{}')
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    output_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default='')
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
