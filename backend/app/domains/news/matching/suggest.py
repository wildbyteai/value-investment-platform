"""建议关注：not-watched mention names seen in ≥ ``suggest.min_events`` events within the last
``suggest.days`` days (config/news-matching-v1.json), with a one-click add.

R10a fixes the contract; R10b implements it. Never commits.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Suggestion:
    name: str                    # most frequent spelling
    name_norm: str
    ticker_norm: str | None
    market: str | None
    events: int
    last_seen_at: datetime | None
    sample_event_ids: list[str] = field(default_factory=list)
    company_id: str | None = None  # an existing company (not watched here) whose alias matches


def suggested_companies(db, workspace_id: str, min_events: int | None = None, days: int | None = None,
                        now: datetime | None = None, limit: int = 50) -> list[Suggestion]:
    raise NotImplementedError('R10b: matching.suggest.suggested_companies')


def add_suggested(db, workspace_id: str, actor_id: str, name_norm: str, name: str | None = None,
                  ticker: str | None = None) -> dict:
    """Create the company if missing (+ aliases from the mention spellings, source ``suggested``),
    watch it, and return ``{"watch": WatchCompanyOut, "company_created": bool, "aliases_added": int}``."""
    raise NotImplementedError('R10b: matching.suggest.add_suggested')
