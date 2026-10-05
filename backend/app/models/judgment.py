from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JudgmentSlot(Base):
    """A stable business question (e.g. impact of one item on one company dimension)."""

    __tablename__ = "judgment_slot"
    __table_args__ = (UniqueConstraint("slot_key", name="uq_slot_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slot_key: Mapped[str] = mapped_column(String(250), nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("company.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)  # impact / rubric / risk
    dimension: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # effective revision pointer
    effective_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    generation: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())

    revisions: Mapped[list[JudgmentRevision]] = relationship(back_populates="slot")


class JudgmentRevision(Base):
    __tablename__ = "judgment_revision"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slot_id: Mapped[str] = mapped_column(ForeignKey("judgment_slot.id"), nullable=False)
    # auto / human
    author_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    decision: Mapped[str] = mapped_column(String(20), nullable=False)  # accepted / rejected / pending
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())

    slot: Mapped[JudgmentSlot] = relationship(back_populates="revisions")
