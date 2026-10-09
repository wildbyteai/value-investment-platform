"""关注列表（``watch_company``）与公司别名（``company_alias``）维护。

Only active watch rows take part in stage-2 matching. Adding/archiving a company or changing an alias
does not rewrite links by itself; the caller offers a re-match (``jobs`` kind ``rematch``).
Every change writes an audit record (``news.watchlist.*`` / ``news.alias.*``).

R10a fixes the contract; R10b implements it. Never commits.
"""
from __future__ import annotations

WATCH_STATUSES = ('active', 'archived')
ALIAS_SOURCES = ('seed', 'manual', 'suggested')


def list_watch(db, workspace_id: str, status: str | None = None, q: str | None = None,
               limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    """(items, total); each item = schemas ``WatchCompanyOut`` in app/api/matching.py."""
    raise NotImplementedError('R10b: matching.watchlist.list_watch')


def add_watch(db, workspace_id: str, actor_id: str, company_id: str | None = None, name: str | None = None,
              tickers: list[str] | None = None, note: str = '') -> dict:
    """Watch an existing company (``company_id``) or create one by ``name`` (+ tickers → securities
    and ticker aliases). Re-activates an archived row. Conflict if already active."""
    raise NotImplementedError('R10b: matching.watchlist.add_watch')


def update_watch(db, workspace_id: str, actor_id: str, watch_id: str, status: str | None = None,
                 note: str | None = None) -> dict:
    raise NotImplementedError('R10b: matching.watchlist.update_watch')


def remove_watch(db, workspace_id: str, actor_id: str, watch_id: str) -> None:
    """Delete the watch row (links already made are kept)."""
    raise NotImplementedError('R10b: matching.watchlist.remove_watch')


def list_aliases(db, company_id: str) -> list[dict]:
    raise NotImplementedError('R10b: matching.watchlist.list_aliases')


def add_alias(db, workspace_id: str, actor_id: str, company_id: str, alias: str, kind: str,
              market: str | None = None, source: str = 'manual') -> dict:
    """``alias_norm`` = ``normalize.alias_norm``; Conflict when the company already has that norm."""
    raise NotImplementedError('R10b: matching.watchlist.add_alias')


def delete_alias(db, workspace_id: str, actor_id: str, company_id: str, alias_id: str) -> None:
    raise NotImplementedError('R10b: matching.watchlist.delete_alias')


def seed_aliases(db, actor_id: str | None = None) -> dict:
    """Idempotently (re)seed aliases from company names, security tickers and
    config/company-aliases-v1.json (same rules as migration 0016); returns counts."""
    raise NotImplementedError('R10b/R11: matching.watchlist.seed_aliases')
