"""Stage 1 — extract EVERY company a news event mentions (watched or not) → ``news_mention``.

Scene ``news_extract`` (config/model-scenes-v1.json); prompt as agent_skill ``news-extract`` v1.
If the LLM call fails, fall back to rule extraction (alias dictionary scan + ``normalize.find_tickers``)
with extractor ``rule:v1``. Limits live in config/news-matching-v1.json ``extract``.

R10a fixes the contract; R10b (``feature/matching-engine``) implements it. Never commits.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # pragma: no cover
    import httpx

    from app.domains.news.llm import ProviderConfig
    from app.domains.news.matching.resolve import AliasIndex
    from app.models.news import NewsEvent

RULE_EXTRACTOR = 'rule:v1'
SKILL_KEY = 'news-extract'
EXTRACT_STATUSES = ('pending', 'done', 'rule_only', 'failed')


@dataclass(frozen=True)
class MentionDraft:
    """One company as the extractor saw it, before normalization and storage.

    ``name`` as written (≤200), ``ticker_raw`` as written or ``None``, ``market`` one of
    normalize.MARKETS or ``None``, ``relevance`` 0..1, ``impact`` -1..1 (clamped by policy),
    ``key_point`` ≤80 chars, ``evidence`` a short quote from the event text."""
    name: str
    ticker_raw: str | None
    market: str | None
    relevance: Decimal
    impact: Decimal
    key_point: str
    evidence: str


@dataclass(frozen=True)
class ExtractResult:
    """``extractor`` is ``llm:<provider_key>/<model>@news-extract:v<skill version>`` or ``rule:v1``;
    ``status`` is the value written to ``news_event.extract_status`` (done | rule_only | failed);
    ``error`` the LLM failure that caused a rule fallback (safe to show, never contains a key)."""
    mentions: list[MentionDraft] = field(default_factory=list)
    extractor: str = RULE_EXTRACTOR
    model: str | None = None
    status: str = 'rule_only'
    error: str | None = None


def parse_mentions(content: str) -> list[MentionDraft]:
    """Parse the model's strict JSON ``{"mentions": [{name, ticker, market, relevance, impact,
    key_point, evidence}]}``; clamp numbers, trim text, drop blanks. Raises ``llm.LlmError``."""
    raise NotImplementedError('R10b: matching.extract.parse_mentions')


def extract_mentions(provider: 'ProviderConfig', event_text: str, hints: Sequence[str] = (),
                     transport: 'httpx.BaseTransport | None' = None) -> ExtractResult:
    """Call scene ``news_extract`` (provider from ``model_scenes.resolve``; reasoning effort already
    on ``provider``). ``hints`` are target company names of a targeted collector. Raises
    ``llm.LlmError`` on any model failure; never falls back by itself."""
    raise NotImplementedError('R10b: matching.extract.extract_mentions')


def rule_mentions(event_text: str, index: 'AliasIndex') -> list[MentionDraft]:
    """Rule fallback: every alias of ``index`` (ticker / exact / contained ≥3 chars) and every ticker
    from ``normalize.find_tickers`` found in the text; relevance = policy rule_fallback_relevance,
    impact 0, key_point '规则匹配：…'."""
    raise NotImplementedError('R10b: matching.extract.rule_mentions')


def extract_event(db, workspace_id: str, event: 'NewsEvent', provider: 'ProviderConfig | None' = None,
                  hints: Sequence[str] = (), transport: 'httpx.BaseTransport | None' = None) -> ExtractResult:
    """Stage 1 for one event: LLM (fallback rule), then upsert ``news_mention`` rows by
    ``(event_id, name_norm)`` and set ``event.extract_status / extract_version / extracted_at``
    (mirrored to ``ai_status`` for older pages). Mentions no longer returned are deleted unless a
    human-reviewed link points at them. Never commits."""
    raise NotImplementedError('R10b: matching.extract.extract_event')
