"""Collapse items about the same happening into one event.

Two items are the same event when their normalized titles share enough character
bigrams and they were published within the dedupe window. The score is the overlap
coefficient |A∩B| / min(|A|,|B|): Chinese headlines about one event differ in length
and wording ("发布全天候AI智能体" vs "发布始终在线智能体"), which Jaccard punishes.
Simple, explainable, and good enough for ~30 items a day; numbers in config.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from app.domains.news.normalize import normalize_title
from app.domains.news.policy import policy


def bigrams(text: str) -> set[str]:
    t = normalize_title(text)
    return {t[i:i + 2] for i in range(len(t) - 1)} or ({t} if t else set())


def similarity(a: str, b: str) -> Decimal:
    x, y = bigrams(a), bigrams(b)
    if not x or not y:
        return Decimal(0)
    return Decimal(len(x & y)) / Decimal(min(len(x), len(y)))


def same_event(title: str, published: datetime | None, other_title: str, other_published: datetime | None,
               cfg: dict | None = None) -> bool:
    d = (cfg or policy())['dedupe']
    if published and other_published and abs(published - other_published) > timedelta(days=d['window_days']):
        return False
    return similarity(title, other_title) >= Decimal(d['title_similarity_minimum'])
