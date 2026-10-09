"""Every external data source in one list.

Before R3 each provider module was discovered by reading its code. Now each source
declares which business layer it feeds, how it runs and what it needs, and the
settings page (后台设置 › 数据源) reads this list. Provider modules keep their own
fetch logic; new feeds (R5) implement :class:`FeedAdapter`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable, Protocol


@dataclass(frozen=True)
class SourceSpec:
    key: str
    name: str
    layer: str            # news | companies | strategy
    kind: str             # what it provides
    module: str           # where the fetch code lives
    trigger: str          # manual_script | scheduled | upload
    markets: tuple[str, ...] = ()
    secret_env: str | None = None
    notes: str = ''
    key_is_prefix: bool = False

    def as_dict(self):
        d = asdict(self)
        d['markets'] = list(self.markets)
        return d


class FeedAdapter(Protocol):
    """Contract for news feeds: return raw rows; normalization is the news layer's job."""
    key: str

    def fetch(self) -> Iterable[dict]: ...


_REGISTRY: dict[str, SourceSpec] = {}


def register(spec: SourceSpec) -> SourceSpec:
    if spec.key in _REGISTRY and _REGISTRY[spec.key] != spec:
        raise ValueError(f'duplicate source key {spec.key}')
    _REGISTRY[spec.key] = spec
    return spec


def get(key: str) -> SourceSpec | None:
    if key in _REGISTRY:
        return _REGISTRY[key]
    return next((s for s in _REGISTRY.values() if s.key_is_prefix and key.startswith(s.key)), None)


def all_sources(layer: str | None = None) -> list[SourceSpec]:
    return [s for s in _REGISTRY.values() if layer is None or s.layer == layer]


for _spec in (
    SourceSpec('baostock-a-daily', 'BaoStock 免费 A 股日线', 'companies', 'daily_price', 'app.domains.market_data.baostock_source', 'manual_script', ('CN_A',)),
    SourceSpec('baostock-a-financial', 'BaoStock 免费财务指标', 'companies', 'financial_indicators', 'app.domains.companies.baostock_financial', 'manual_script', ('CN_A',), key_is_prefix=True),
    SourceSpec('eodhd-', 'EODHD 港股日线（个人用途）', 'companies', 'daily_price', 'app.domains.market_data.eodhd_source', 'manual_script', ('HK',), secret_env='EODHD_API_TOKEN', key_is_prefix=True),
    SourceSpec('futu-', '富途 OpenAPI 行情（本机个人用途）', 'companies', 'quote', 'app.domains.market_data.futu_source', 'manual_script', ('HK', 'CN_A'), notes='需本机 OpenD', key_is_prefix=True),
    SourceSpec('ecb-reference-fx', '欧洲央行每日参考汇率', 'companies', 'fx_reference', 'app.domains.market_data.ecb_fx', 'manual_script'),
    SourceSpec('cninfo-', '巨潮法定报告摘录', 'companies', 'statement_excerpt', 'app.domains.companies.issuer_reports', 'manual_script', ('CN_A',), key_is_prefix=True),
    SourceSpec('cninfo-bounded-issuer-disclosures', '巨潮发行人公告', 'news', 'issuer_announcement', 'app.domains.news.issuer_disclosures', 'manual_script', ('CN_A',)),
    SourceSpec('wikimedia-en-text', 'Wikipedia 英文百科', 'companies', 'business_description', 'app.domains.companies.real_source', 'manual_script'),
    SourceSpec('news-excel-upload', '每日资讯 Excel（人工定时任务产出）', 'news', 'news_items', 'app.domains.news.normalize', 'upload', notes='后台上传或接口导入'),
    SourceSpec('news-rss', 'RSS / Atom 资讯源', 'news', 'news_items', 'app.domains.news.service', 'scheduled', notes='python -m app.jobs news'),
    SourceSpec('local-fixture', '合成演示资料', 'news', 'synthetic_items', 'app.domains.news.intake_service', 'manual_script', notes='仅测试库'),
):
    register(_spec)
