from app.db import Base  # noqa: F401
from app.models.identity import Workspace, User, Membership  # noqa: F401
from app.models.audit import AuditLog, Outbox, IngestionRun  # noqa: F401
from app.models.intake import SourceRegistry, InformationItem, ItemSourceRef  # noqa: F401
from app.models.company import Company, Security, ItemCompanyLink, EconomicFact  # noqa: F401
from app.models.judgment import JudgmentSlot, JudgmentRevision  # noqa: F401
from app.models.strategy import StrategyVersion, SecurityState, ChangeRecord  # noqa: F401
from app.models.collab import Watchlist, Note  # noqa: F401
from app.models.runtime import CommandReceipt, WorkEffect, ResearchInput, Evaluation, TemplateRelease, ItemRevision, ItemObservation  # noqa: F401

from app.models.runtime import ResearchRun  # noqa: F401
from app.models.sealing import KnowledgeEntry, SafetyGeneration, InstalledArtifact, PrimaryListing, MarketSession, EvaluationSeal, FrozenManifest  # noqa: F401
from app.services.knowledge_clock import register_metadata_triggers
register_metadata_triggers(Base.metadata)
