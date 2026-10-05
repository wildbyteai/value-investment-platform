from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, require
from app.db import get_db
from app.services import data_mode
from app.models.company import Company, Security
from app.services.scoring_service import score_company, score_security

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
    return result
