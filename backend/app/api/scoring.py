from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, require
from app.db import get_db
from app.services import data_mode
from app.models.company import Company, Security
from app.services.scoring_service import score_company, score_security
from app.services.scoring_service import inputs, config
from app.models.strategy import StrategyVersion
from app.services.reference_research import quality_reference, valuation_reference, strategy_reference
import json

router = APIRouter(prefix="/api/companies", tags=["scoring"])


@router.get("/{company_id}/score")
def company_score(
    company_id: str,
    as_of: datetime | None = None,
    cutoff: datetime | None = None,
    principal: Principal = Depends(require("research.read")),
    db: Session = Depends(get_db),
):
    c = data_mode.require_company(db, company_id, principal.workspace.id)
    if c is None:
        raise HTTPException(status_code=404, detail="company not found")
    if any(value is not None and value.tzinfo is None for value in (as_of, cutoff)):
        raise HTTPException(status_code=422, detail="时点必须包含时区")
    as_of = as_of or datetime.now(timezone.utc)
    cutoff = cutoff or as_of
    if cutoff < as_of:
        raise HTTPException(status_code=422, detail="知识截止不能早于评估时点")
    result = score_company(db, c, principal.workspace.id, as_of, cutoff)
    secs = db.scalars(select(Security).where(Security.company_id == c.id)).all()
    result["securities"] = [score_security(db, s, principal.workspace.id, as_of, cutoff) for s in secs]
    result['reference_quality'] = quality_reference(result)
    rows = inputs(db, c.id, principal.workspace.id, as_of, cutoff)
    release = db.scalar(select(StrategyVersion).where(StrategyVersion.workspace_id == principal.workspace.id,
        StrategyVersion.published.is_(True), StrategyVersion.created_at <= cutoff).order_by(StrategyVersion.version.desc()).limit(1))
    rules = json.loads(release.rules_json) if release else config('strategy-standard-v1.json')
    for security, value in zip(secs, result['securities']):
        value['reference_valuation'] = valuation_reference(security, rows, as_of, cutoff)
        value['reference_strategy'] = strategy_reference(rules, result, value, value['reference_valuation'], release)
    return result
