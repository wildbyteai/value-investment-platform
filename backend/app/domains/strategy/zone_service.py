"""Strike-zone service: gathers scores from the company layer and classifies each
security (A 股、H 股分别判断). Read-only; never commits."""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select

from app.core.errors import NotFound
from app.domains.strategy import strike_zone
from app.models.company import Company, Security
from app.models.strategy import StrategyVersion
from app.domains.platform import data_mode
from app.domains.companies.scoring_service import config, score_company, score_security
from app.domains.strategy.strategy_service import gates


def strategy_rules(db, workspace_id) -> dict:
    """The published strategy's rules, or the standard config before the first release."""
    published = db.scalar(select(StrategyVersion).where(
        StrategyVersion.workspace_id == workspace_id, StrategyVersion.published.is_(True))
        .order_by(StrategyVersion.version.desc()).limit(1))
    return json.loads(published.rules_json) if published else config('strategy-standard-v1.json')


def _security_rows(db, company, workspace_id, rules, at):
    quality = score_company(db, company, workspace_id, at, at)
    company_ctx = {**quality, 'company_id': company.id, 'industry_key': company.industry_key}
    for security in db.scalars(select(Security).where(Security.company_id == company.id).order_by(Security.market, Security.ticker)).all():
        valuation = score_security(db, security, workspace_id, at, at)
        result = gates(rules, quality, valuation)
        zone = strike_zone.classify(company_ctx, valuation, result)
        yield {
            'company_id': company.id, 'company': company.name, 'industry_key': company.industry_key,
            'security_id': security.id, 'ticker': security.ticker, 'market': security.market,
            'quality_score': quality.get('quality_score'), 'coverage': quality.get('coverage_exact'),
            'valuation_score': valuation.get('valuation_score'), 'pe_ttm': valuation.get('pe_ttm'),
            **zone.as_dict(),
        }


def evaluate_workspace(db, workspace_id, at: datetime) -> list[dict]:
    rules = strategy_rules(db, workspace_id)
    rows = []
    for company in data_mode.companies(db, workspace_id):
        rows.extend(_security_rows(db, company, workspace_id, rules, at))
    order = {strike_zone.SWEET: 0, strike_zone.EDGE: 1, strike_zone.OUTSIDE: 2}
    return sorted(rows, key=lambda r: (order[r['zone']], r['company'], r['market']))


def evaluate_company(db, workspace_id, company_id, at: datetime) -> list[dict]:
    company = next((c for c in data_mode.companies(db, workspace_id) if c.id == company_id), None)
    if company is None:
        raise NotFound('当前研究模式和工作区没有该公司')
    return list(_security_rows(db, company, workspace_id, strategy_rules(db, workspace_id), at))
