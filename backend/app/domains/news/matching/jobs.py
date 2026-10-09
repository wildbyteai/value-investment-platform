"""重新匹配 / 重新研判 background jobs (``match_job``).

* ``rematch``  — stage 2 only over existing mentions (after watchlist / alias changes); fast, no LLM.
* ``reassess`` — stage 1 + 2 for events in a date range (or given ids) with scene ``news_reassess``;
  needs permission ``news.reassess``; estimate shown before running; runs in the worker with progress.

Status flow: queued → running → done | failed | cancelled. Progress counters: total, processed,
links_added, links_updated. A job only ever adds or updates *proposed* links.

R10a fixes the contract; R11 (``feature/match-jobs``) implements it. Never commits, except
``run_job`` which owns its transactions per batch (like ``collector.run_due``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:  # pragma: no cover
    from app.models.news import MatchJob

JobKind = Literal['rematch', 'reassess']
JOB_KINDS: tuple[str, ...] = ('rematch', 'reassess')
JOB_STATUSES: tuple[str, ...] = ('queued', 'running', 'done', 'failed', 'cancelled')


@dataclass(frozen=True)
class JobParams:
    kind: JobKind
    date_from: date | None = None
    date_to: date | None = None
    event_ids: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Estimate:
    events: int
    estimated_calls: int   # 0 for rematch


def estimate(db, workspace_id: str, params: JobParams) -> Estimate:
    raise NotImplementedError('R11: matching.jobs.estimate')


def create_job(db, workspace_id: str, actor_id: str, params: JobParams) -> 'MatchJob':
    """Queue a job (one queued/running job per workspace and kind; Conflict otherwise)."""
    raise NotImplementedError('R11: matching.jobs.create_job')


def run_job(db_factory, job_id: str, transport=None) -> dict:
    raise NotImplementedError('R11: matching.jobs.run_job')


def cancel_job(db, workspace_id: str, actor_id: str, job_id: str) -> 'MatchJob':
    raise NotImplementedError('R11: matching.jobs.cancel_job')


def job_dict(job: 'MatchJob') -> dict:
    """Shape of ``MatchJobOut`` in app/api/matching.py."""
    raise NotImplementedError('R11: matching.jobs.job_dict')


def list_jobs(db, workspace_id: str, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    raise NotImplementedError('R11: matching.jobs.list_jobs')
