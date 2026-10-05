import json

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, require
from app.db import get_db
from app.services import data_mode
from app.models.judgment import JudgmentRevision, JudgmentSlot
from app.services.decision_service import auto_decide, effective_value, human_override

router = APIRouter(prefix="/api/judgments", tags=["judgments"])


class OverrideIn(BaseModel):
    value: dict
    release: bool = False


@router.post("/auto-run")
def run_auto(
    principal: Principal = Depends(require("analysis.override")),
    db: Session = Depends(get_db),
):
    data_mode.require_fixture()
    stats = auto_decide(db, principal.workspace.id, principal.user.id)
    db.commit()
    return stats


@router.get("")
def list_effective(
    principal: Principal = Depends(require("research.read")),
    db: Session = Depends(get_db),
):
    slots = db.scalars(select(JudgmentSlot).where(JudgmentSlot.workspace_id == principal.workspace.id).order_by(JudgmentSlot.kind, JudgmentSlot.slot_key)).all()
    out = []
    for s in slots:
        rev=db.get(JudgmentRevision,s.effective_revision_id) if s.effective_revision_id else None
        if not data_mode.fixture_mode() and (not rev or not data_mode.real_evidence(db,json.loads(rev.evidence_json),principal.workspace.id,s.company_id)): continue
        out.append({
            "slot_key": s.slot_key,
            "kind": s.kind,
            "company_id": s.company_id,
            "dimension": s.dimension,
            "evidence": json.loads(db.get(JudgmentRevision, s.effective_revision_id).evidence_json) if s.effective_revision_id else [],
            "generation": s.generation,
            "effective": effective_value(db, s),
        })
    return out


@router.post("/{slot_key}/override")
def override(
    slot_key: str,
    body: OverrideIn,
    principal: Principal = Depends(require("analysis.override")),
    db: Session = Depends(get_db),
    if_match: int = Header(alias="If-Match-Generation"),
    command_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=240),
):
    if not data_mode.fixture_mode():
        slot=db.scalar(select(JudgmentSlot).where(JudgmentSlot.slot_key==slot_key,JudgmentSlot.workspace_id==principal.workspace.id))
        prior=db.get(JudgmentRevision,slot.effective_revision_id) if slot and slot.effective_revision_id else None
        if not prior or not data_mode.real_evidence(db,json.loads(prior.evidence_json),principal.workspace.id,slot.company_id):
            raise HTTPException(404,'没有具备真实来源证据的判断槽')
    try:
        rev, status, current_gen = human_override(db, slot_key, body.value, if_match,
            principal.workspace.id, principal.user.id, command_key, body.release)
    except (ValueError, ArithmeticError):
        db.rollback()
        raise HTTPException(status_code=422, detail="判断值不符合类型或取值范围")
    if status == "not_found":
        raise HTTPException(status_code=404, detail="slot not found")
    if status == "conflict":
        # 409 keeps the caller's input; report current generation
        raise HTTPException(status_code=409, detail=f"stale generation; current={current_gen}")
    db.commit()
    return {"id": rev.id, "generation": current_gen, "value": json.loads(rev.value_json), "released": body.release}
