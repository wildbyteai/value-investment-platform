from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, require
from app.db import get_db
from app.domains.platform import data_mode
from app.models.company import Company, ItemCompanyLink, Security
from app.models.intake import InformationItem, SourceRegistry

router = APIRouter(prefix="/api/companies", tags=['公司档案'])


@router.get("")
def list_companies(
    principal: Principal = Depends(require("research.read")),
    db: Session = Depends(get_db),
):
    companies = data_mode.companies(db, principal.workspace.id)
    out = []
    for c in companies:
        secs = db.scalars(select(Security).where(Security.company_id == c.id)).all()
        out.append({
            "id": c.id,
            "name": c.name,
            "industry_key": c.industry_key,
            "securities": [
                {"market": s.market, "ticker": s.ticker, "currency": s.currency} for s in secs
            ],
        })
    return out


@router.get("/{company_id}/timeline")
def company_timeline(
    company_id: str,
    principal: Principal = Depends(require("research.read")),
    db: Session = Depends(get_db),
):
    c = data_mode.require_company(db, company_id, principal.workspace.id)
    if c is None:
        raise HTTPException(status_code=404, detail="company not found")
    links = db.scalars(
        select(ItemCompanyLink).where(
            ItemCompanyLink.company_id == company_id,
            ItemCompanyLink.status == "accepted",
            ItemCompanyLink.item_id.in_(select(InformationItem.id).where(InformationItem.workspace_id == principal.workspace.id)),
        )
    ).all()
    item_ids = [lk.item_id for lk in links]
    items = db.scalars(select(InformationItem).where(InformationItem.id.in_(item_ids))).all() if item_ids else []
    import json
    items = [it for it in items if data_mode.readable_item(db, it, principal.workspace.id)]
    return {
        "company": {"id": c.id, "name": c.name},
        "items": [
            {"id": it.id, "title": it.title, "content_kind": it.content_kind} for it in items
        ],
    }
