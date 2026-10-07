"""策略 · 击球区 API."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import Principal, require
from app.db import get_db
from app.domains.strategy import strike_zone, zone_service

router = APIRouter(prefix='/api/strike-zone', tags=['strategy'])


class ZoneCheck(BaseModel):
    key: str
    label: str
    passed: bool | None
    detail: str


class ZoneRow(BaseModel):
    company_id: str
    company: str
    industry_key: str
    security_id: str
    ticker: str
    market: str
    quality_score: float | None = None
    coverage: str | None = None
    valuation_score: float | None = None
    pe_ttm: float | None = None
    zone: str
    label: str
    margin_of_safety: str | None = None
    checks: list[ZoneCheck]


class ZoneBoard(BaseModel):
    as_of: str
    policy: dict
    counts: dict[str, int]
    rows: list[ZoneRow]


@router.get('/policy')
def get_policy(principal: Principal = Depends(require('research.read'))) -> dict:
    return strike_zone.policy()


@router.get('', response_model=ZoneBoard)
def board(principal: Principal = Depends(require('research.read')), db=Depends(get_db)):
    at = datetime.now(timezone.utc)
    rows = zone_service.evaluate_workspace(db, principal.workspace.id, at)
    counts = {z: sum(1 for r in rows if r['zone'] == z) for z in strike_zone.LABELS}
    return {'as_of': at.isoformat(), 'policy': strike_zone.policy(), 'counts': counts, 'rows': rows}


@router.get('/companies/{company_id}', response_model=list[ZoneRow])
def company(company_id: str, principal: Principal = Depends(require('research.read')), db=Depends(get_db)):
    return zone_service.evaluate_company(db, principal.workspace.id, company_id, datetime.now(timezone.utc))
