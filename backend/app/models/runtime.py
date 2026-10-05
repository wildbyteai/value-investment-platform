"""Additional immutable inputs and durable execution state for the local slice."""
from datetime import datetime, timezone
import uuid
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, ForeignKey, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)


class CommandReceipt(Base):
    __tablename__ = 'command_receipt'
    __table_args__ = (UniqueConstraint('workspace_id', 'command_key', name='uq_command_receipt'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36))
    command_key: Mapped[str] = mapped_column(String(240))
    request_hash: Mapped[str] = mapped_column(String(64))
    response_json: Mapped[str] = mapped_column(Text)


class WorkEffect(Base):
    __tablename__ = 'work_effect'
    id: Mapped[str] = mapped_column(String(36), primary_key=True) # outbox logical identity
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResearchInput(Base):
    __tablename__ = 'research_input'
    __table_args__ = (UniqueConstraint('workspace_id', 'input_key', 'content_hash', name='uq_research_input'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36))
    company_id: Mapped[str] = mapped_column(ForeignKey('company.id'))
    input_key: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(40))
    payload_json: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    known_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class Evaluation(Base):
    __tablename__ = 'evaluation'
    __table_args__ = (UniqueConstraint('workspace_id', 'strategy_id', 'security_id', 'session', name='uq_evaluation_session'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36))
    strategy_id: Mapped[str] = mapped_column(ForeignKey('strategy_version.id'))
    security_id: Mapped[str] = mapped_column(ForeignKey('security.id'))
    session: Mapped[str] = mapped_column(String(40))
    manifest_json: Mapped[str] = mapped_column(Text)
    manifest_hash: Mapped[str] = mapped_column(String(64))
    result_json: Mapped[str] = mapped_column(Text)
    token: Mapped[str] = mapped_column(String(36), unique=True, default=uid)
    application_status: Mapped[str] = mapped_column(String(40))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TemplateRelease(Base):
    __tablename__ = 'template_release'
    __table_args__ = (UniqueConstraint('workspace_id', 'company_id', 'version', name='uq_template_release'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(String(36))
    company_id: Mapped[str] = mapped_column(ForeignKey('company.id'))
    version: Mapped[int] = mapped_column(Integer)
    config_json: Mapped[str] = mapped_column(Text)
    config_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ItemRevision(Base):
    __tablename__ = 'item_revision'
    __table_args__ = (UniqueConstraint('item_id','content_hash',name='uq_item_revision_hash'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    item_id: Mapped[str] = mapped_column(ForeignKey('information_item.id'))
    content_hash: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ItemObservation(Base):
    __tablename__ = 'item_observation'
    __table_args__ = (UniqueConstraint('item_id','sequence',name='uq_item_observation_sequence'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    item_id: Mapped[str] = mapped_column(ForeignKey('information_item.id'))
    revision_id: Mapped[str] = mapped_column(ForeignKey('item_revision.id'))
    sequence: Mapped[int] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResearchRun(Base):
    """Immutable research preview, distinct from sealed market evaluations."""
    __tablename__ = 'research_run'
    __table_args__ = (UniqueConstraint('workspace_id','command_key',name='uq_research_run_command'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    workspace_id: Mapped[str] = mapped_column(ForeignKey('workspace.id'))
    actor_id: Mapped[str] = mapped_column(ForeignKey('app_user.id'))
    command_key: Mapped[str] = mapped_column(String(240))
    request_hash: Mapped[str] = mapped_column(String(64))
    manifest_json: Mapped[str] = mapped_column(Text)
    manifest_hash: Mapped[str] = mapped_column(String(64))
    result_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
