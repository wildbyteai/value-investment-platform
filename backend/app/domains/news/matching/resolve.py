"""Stage 2 — deterministic mention → watched company resolution (no LLM).

Look each ``news_mention`` up in ``company_alias`` restricted to the workspace's active
``watch_company`` rows, in this order (never fuzzy):

1. ``ticker``   — ``mention.ticker_norm`` equals a ticker alias;
2. ``alias``    — ``mention.name_norm`` equals a non-ticker alias;
3. ``contains`` — a non-ticker alias of length ≥ ``resolve.contains_min_length`` (3) is contained in
   ``name_norm`` (or ``name_norm`` ≥3 is contained in the alias).

A hit creates/updates ``news_event_company`` (status proposed, ``mention_id``, ``match_method``,
``rule_version``); rows with status confirmed/rejected (human) are never overwritten. Ambiguous hits
(several companies at the same step) resolve to none and count as ``ambiguous``.

R10a fixes the contract; R10b implements it. Never commits.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RULE_VERSION = 'resolve:v1'
MatchMethod = Literal['ticker', 'alias', 'contains']
MATCH_METHODS: tuple[str, ...] = ('ticker', 'alias', 'contains')


@dataclass(frozen=True)
class AliasEntry:
    company_id: str
    alias: str
    alias_norm: str
    kind: str          # name | short | en | former | ticker
    market: str | None


@dataclass
class AliasIndex:
    """Aliases of the active watchlist, indexed for the three lookups."""
    by_ticker: dict[str, set[str]] = field(default_factory=dict)   # ticker_norm → company ids
    by_name: dict[str, set[str]] = field(default_factory=dict)     # alias_norm → company ids
    contains: list[tuple[str, str]] = field(default_factory=list)  # (alias_norm, company_id), len ≥ min

    @classmethod
    def build(cls, entries: list[AliasEntry], contains_min_length: int = 3) -> 'AliasIndex':
        raise NotImplementedError('R10b: matching.resolve.AliasIndex.build')


@dataclass(frozen=True)
class Resolution:
    company_id: str
    method: MatchMethod
    alias_norm: str


@dataclass
class ResolveStats:
    mentions: int = 0
    links_added: int = 0
    links_updated: int = 0
    unresolved: int = 0
    ambiguous: int = 0
    kept_human: int = 0


def load_index(db, workspace_id: str) -> AliasIndex:
    """Aliases of companies whose ``watch_company`` row in this workspace is active."""
    raise NotImplementedError('R10b: matching.resolve.load_index')


def resolve_mention(index: AliasIndex, name_norm: str, ticker_norm: str | None) -> Resolution | None:
    """Pure lookup (ticker → alias → contains); ``None`` when nothing or more than one company hits."""
    raise NotImplementedError('R10b: matching.resolve.resolve_mention')


def resolve_event(db, workspace_id: str, event_id: str, index: AliasIndex | None = None) -> ResolveStats:
    """Stage 2 for one event's mentions; writes ``news_event_company``. Never commits."""
    raise NotImplementedError('R10b: matching.resolve.resolve_event')
