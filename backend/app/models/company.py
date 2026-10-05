from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
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


class Company(Base):
    __tablename__ = "company"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    industry_key: Mapped[str] = mapped_column(String(80), nullable=False, default="manufacturing")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())

    securities: Mapped[list[Security]] = relationship(back_populates="company")


class Security(Base):
    __tablename__ = "security"
    __table_args__ = (UniqueConstraint("market", "ticker", name="uq_security_market_ticker"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), nullable=False)
    market: Mapped[str] = mapped_column(String(20), nullable=False)  # CN_A / HK
    ticker: Mapped[str] = mapped_column(String(30), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())

    company: Mapped[Company] = relationship(back_populates="securities")


class ItemCompanyLink(Base):
    """A proposed/accepted association between an information item and a company."""

    __tablename__ = "item_company_link"
    __table_args__ = (
        UniqueConstraint("item_id", "company_id", name="uq_link_item_company"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    item_id: Mapped[str] = mapped_column(ForeignKey("information_item.id"), nullable=False)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("company.id"), nullable=True)
    label_text: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # accepted / ambiguous / no_link
    relevance: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class EconomicFact(Base):
    """Deduplicated real-world fact shared across items/events."""

    __tablename__ = "economic_fact"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(ForeignKey("company.id"), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())
