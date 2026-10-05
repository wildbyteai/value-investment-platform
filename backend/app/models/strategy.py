from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class StrategyVersion(Base):
    __tablename__ = "strategy_version"
    __table_args__ = (UniqueConstraint("workspace_id", "strategy_key", "version", name="uq_strategy_key_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    strategy_key: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rules_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    published: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class SecurityState(Base):
    __tablename__ = "security_state"
    __table_args__ = (UniqueConstraint("security_id", "strategy_id", name="uq_state_security_strategy"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    security_id: Mapped[str] = mapped_column(ForeignKey("security.id"), nullable=False)
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategy_version.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OUT")
    pending_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_confirmed: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_session: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class ChangeRecord(Base):
    """Immutable state transition / config change. delivery=0 (notification deferred)."""

    __tablename__ = "change_record"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    security_id: Mapped[str] = mapped_column(String(36), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evaluation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    session_label: Mapped[str] = mapped_column(String(40), nullable=False)
    from_status: Mapped[str] = mapped_column(String(30), nullable=False)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(String(120), nullable=False)
    delivery_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())
