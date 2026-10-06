import json

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, StrictInt
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Literal
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
    from app.services.scoring_service import current_decisions
    now = datetime.now(timezone.utc)
    effective = {s.id:r for company in data_mode.companies(db,principal.workspace.id)
                 for s,r,v in current_decisions(db,company.id,principal.workspace.id,now,now)}
    out = []
    for slot in slots:
        rev = effective.get(slot.id)
        # Keep released/stale slots visible only if their previous evidence remains readable.
        prior = db.scalar(select(JudgmentRevision).where(JudgmentRevision.slot_id==slot.id)
                          .order_by(JudgmentRevision.created_at.desc()).limit(1))
        if not data_mode.fixture_mode() and (not prior or not data_mode.real_evidence(db,json.loads(prior.evidence_json),principal.workspace.id,slot.company_id)): continue
        out.append({'slot_key':slot.slot_key,'kind':slot.kind,'company_id':slot.company_id,
            'dimension':slot.dimension,'generation':slot.generation,
            'evidence':json.loads((rev or prior).evidence_json) if rev or prior else [],
            'effective':json.loads(rev.value_json) if rev else None,
            'identity':{k:json.loads((db.scalar(select(JudgmentRevision).where(JudgmentRevision.slot_id==slot.id,JudgmentRevision.decision=='accepted').order_by(JudgmentRevision.created_at.desc()).limit(1)) or prior).value_json).get(k) for k in ('rubric_ref','criterion','period_start','period_end')} if prior else {},
            'status':'effective' if rev else 'pending_review',
            'author_type':(rev or prior).author_type if rev or prior else None,
            'proposal':json.loads(prior.value_json) if prior and prior.decision=='pending' else None})
    return out


class EvidenceIn(BaseModel):
    source_revision_id: str
    hash: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1,max_length=5000)
    relation: Literal['supports','contradicts'] = 'supports'


class CreateIn(BaseModel):
    company_id: str
    dimension: str
    rubric_ref: str
    criterion: str
    period_start: date
    period_end: date
    grade: StrictInt = Field(ge=0,le=4)
    confidence: Decimal = Field(ge=0,le=1,allow_inf_nan=False)
    reason: str = Field(min_length=3,max_length=4000,pattern=r'\S')
    effective_from: datetime
    valid_until: datetime
    evidence: list[EvidenceIn] = Field(min_length=1,max_length=10)


class ProposalIn(CreateIn):
    research_method: Literal['local_evidence_review'] = 'local_evidence_review'
    author_label: str = Field(min_length=1,max_length=120)
    limitations: str = Field(min_length=3,max_length=4000,pattern=r'\S')


@router.post('/proposals',status_code=201)
def propose_judgment(body: ProposalIn, principal: Principal = Depends(require('analysis.override')),
                     db: Session = Depends(get_db), command_key: str = Header(alias='Idempotency-Key',min_length=1,max_length=240)):
    from app.services.judgment_authoring import create
    result=create(db,principal,body,command_key,proposal=True)
    db.commit()
    return result


@router.get('/catalog/{company_id}')
def rubric_catalog(company_id: str, principal: Principal = Depends(require('research.read')), db: Session = Depends(get_db)):
    from app.services.judgment_authoring import catalog
    company=data_mode.require_company(db,company_id,principal.workspace.id)
    return catalog(db,company,principal.workspace.id)


@router.post('',status_code=201)
def create_judgment(body: CreateIn, principal: Principal = Depends(require('analysis.override')),
                    db: Session = Depends(get_db), command_key: str = Header(alias='Idempotency-Key',min_length=1,max_length=240)):
    from app.services.judgment_authoring import create
    result=create(db,principal,body,command_key)
    db.commit()
    return result


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
        prior=db.get(JudgmentRevision,slot.effective_revision_id) if slot and slot.effective_revision_id else (db.scalar(select(JudgmentRevision).where(JudgmentRevision.slot_id==slot.id).order_by(JudgmentRevision.created_at.desc()).limit(1)) if slot else None)
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
    return {"id": rev.id, "generation": current_gen, "value": json.loads(rev.value_json), "released": body.release, "applicability": "pending_review" if body.release else "check_current_score"}
