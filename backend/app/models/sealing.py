"""Versioned market context, database knowledge clock and durable unique seals."""
import uuid
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def uid(): return str(uuid.uuid4())


class KnowledgeEntry(Base):
    __tablename__='knowledge_entry'
    sequence: Mapped[int]=mapped_column(BigInteger,Identity(),primary_key=True)
    entity_type: Mapped[str]=mapped_column(String(60))
    entity_id: Mapped[str]=mapped_column(String(36))
    operation: Mapped[str]=mapped_column(String(10))
    snapshot_json: Mapped[str]=mapped_column(Text)
    sha256: Mapped[str]=mapped_column(String(64))
    recorded_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.clock_timestamp())


class SafetyGeneration(Base):
    __tablename__='safety_generation'
    key: Mapped[str]=mapped_column(String(40),primary_key=True)
    generation: Mapped[int]=mapped_column(BigInteger,default=0)


class InstalledArtifact(Base):
    __tablename__='installed_artifact'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    artifact_key: Mapped[str]=mapped_column(String(120))
    sha256: Mapped[str]=mapped_column(String(64))
    payload_json: Mapped[str]=mapped_column(Text)
    installed_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.clock_timestamp())
    __table_args__=(UniqueConstraint('artifact_key','sha256',name='uq_installed_artifact'),)


class PrimaryListing(Base):
    __tablename__='primary_listing'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    security_id: Mapped[str]=mapped_column(ForeignKey('security.id'),unique=True)
    exchange: Mapped[str]=mapped_column(String(30))
    currency: Mapped[str]=mapped_column(String(10))
    calendar_ref: Mapped[str]=mapped_column(String(120))
    close_policy_json: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.clock_timestamp())


class MarketSession(Base):
    __tablename__='market_session'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    calendar_ref: Mapped[str]=mapped_column(String(120))
    market_session: Mapped[str]=mapped_column(String(40))
    ordinal: Mapped[int]=mapped_column(Integer)
    previous_session: Mapped[str | None]=mapped_column(String(40),nullable=True)
    final_market_at: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    evidence_json: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.clock_timestamp())
    __table_args__=(UniqueConstraint('calendar_ref','market_session',name='uq_market_session'),)


class EvaluationSeal(Base):
    __tablename__='evaluation_seal'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    workspace_id: Mapped[str]=mapped_column(String(36))
    release_id: Mapped[str]=mapped_column(ForeignKey('strategy_version.id'))
    security_id: Mapped[str]=mapped_column(ForeignKey('security.id'))
    listing_id: Mapped[str]=mapped_column(ForeignKey('primary_listing.id'))
    market_session: Mapped[str]=mapped_column(String(40))
    mode: Mapped[str]=mapped_column(String(20),default='live')
    state: Mapped[str]=mapped_column(String(40),default='session_due')
    generation: Mapped[int]=mapped_column(Integer,default=0)
    fence: Mapped[int]=mapped_column(Integer,default=0)
    lease_owner: Mapped[str | None]=mapped_column(String(120),nullable=True)
    lease_until: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)
    manifest_id: Mapped[str | None]=mapped_column(String(36),nullable=True)
    evaluation_id: Mapped[str | None]=mapped_column(String(36),nullable=True)
    evaluation_as_of: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    knowledge_cutoff: Mapped[datetime]=mapped_column(DateTime(timezone=True))
    finalization_token: Mapped[str]=mapped_column(String(36),unique=True,default=uid)
    __table_args__=(UniqueConstraint('workspace_id','release_id','security_id','market_session','mode',name='uq_evaluation_seal'),)


class FrozenManifest(Base):
    __tablename__='frozen_manifest'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    seal_id: Mapped[str]=mapped_column(ForeignKey('evaluation_seal.id'))
    generation: Mapped[int]=mapped_column(Integer)
    manifest_json: Mapped[str]=mapped_column(Text)
    manifest_hash: Mapped[str]=mapped_column(String(64))
    snapshot_json: Mapped[str]=mapped_column(Text)
    snapshot_hash: Mapped[str]=mapped_column(String(64))
    safety_generation: Mapped[int]=mapped_column(BigInteger)
    frozen_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.clock_timestamp())
    __table_args__=(UniqueConstraint('seal_id','generation',name='uq_frozen_generation'),)
