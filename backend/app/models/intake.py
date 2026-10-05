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


class SourceRegistry(Base):
    __tablename__ = "source_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # license/fetch/store/analyze/export policy
    policy_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class InformationItem(Base):
    __tablename__ = "information_item"
    __table_args__ = (
        UniqueConstraint("workspace_id", "source_id", "entry_key", name="uq_item_source_entry"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    current_revision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("source_registry.id"), nullable=False)
    entry_key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reading_metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    publication_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    origin_locator_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())
    # body acquisition state: no_locator / available / not_acquired / restricted
    body_state: Mapped[str] = mapped_column(String(40), nullable=False, default="no_locator")
    body_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    refs: Mapped[list[ItemSourceRef]] = relationship(back_populates="item", cascade="all, delete-orphan")


class ItemSourceRef(Base):
    __tablename__ = "item_source_ref"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    item_id: Mapped[str] = mapped_column(ForeignKey("information_item.id"), nullable=False)
    reference_key: Mapped[str] = mapped_column(String(40), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    locator_kind: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    source_locator_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # access state: available / not_acquired / restricted
    access_state: Mapped[str] = mapped_column(String(40), nullable=False, default="not_acquired")

    item: Mapped[InformationItem] = relationship(back_populates="refs")
