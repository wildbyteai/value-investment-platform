import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, require
from app.db import get_db
from app.services import data_mode
from app.models.audit import AuditLog, IngestionRun, Outbox

router = APIRouter(prefix="/api", tags=["demo"])


class RunIn(BaseModel):
    source_key: str
    note: str = ""


@router.post("/demo/runs")
def create_run(
    body: RunIn,
    principal: Principal = Depends(require("source.manage")),
    db: Session = Depends(get_db),
):
    """Authorized business write (data_admin). Writes run + audit + outbox in ONE txn."""
    data_mode.require_fixture()
    run = IngestionRun(
        workspace_id=principal.workspace.id,
        source_key=body.source_key,
        status="created",
        note=body.note,
    )
    db.add(run)
    db.flush()  # get run.id

    db.add(
        AuditLog(
            workspace_id=principal.workspace.id,
            actor_user_id=principal.user.id,
            action="ingestion_run.create",
            entity_type="ingestion_run",
            entity_id=run.id,
            detail_json=json.dumps({"source_key": body.source_key, "at": datetime.now(timezone.utc).isoformat()}),
        )
    )
    db.add(
        Outbox(
            workspace_id=principal.workspace.id,
            aggregate_type="ingestion_run",
            aggregate_id=run.id,
            event_type="ingestion_run.created",
            payload_json=json.dumps({"source_key": body.source_key}),
        )
    )
    db.commit()
    db.refresh(run)
    return {"id": run.id, "source_key": run.source_key, "status": run.status}


@router.get("/demo/runs")
def list_runs(
    principal: Principal = Depends(require("research.read")),
    db: Session = Depends(get_db),
):
    runs = db.scalars(select(IngestionRun).where(IngestionRun.workspace_id == principal.workspace.id).order_by(IngestionRun.created_at.desc())).all()
    if not data_mode.fixture_mode():
        from app.models.intake import SourceRegistry
        allowed={s.source_key for s in db.scalars(select(SourceRegistry)).all() if json.loads(s.policy_json).get("license") and not json.loads(s.policy_json).get("revoked")}
        runs=[r for r in runs if r.source_key in allowed]
    return [{"id": r.id, "source_key": r.source_key, "status": r.status, "note": r.note} for r in runs]


@router.get("/demo/audit")
def read_audit(
    principal: Principal = Depends(require("audit.read")),
    db: Session = Depends(get_db),
):
    """Only system_admin has audit.read."""
    rows = db.scalars(select(AuditLog).where(AuditLog.workspace_id == principal.workspace.id).order_by(AuditLog.created_at.desc()).limit(100)).all()
    return [
        {
            "id": a.id,
            "action": a.action,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "at": a.created_at.isoformat(),
        }
        for a in rows
    ]


@router.get("/demo/outbox")
def read_outbox(
    principal: Principal = Depends(require("ops.read")),
    db: Session = Depends(get_db),
):
    """Worker/ops view of undispatched outbox rows."""
    rows = db.scalars(
        select(Outbox).where(Outbox.dispatched.is_(False), Outbox.workspace_id == principal.workspace.id).order_by(Outbox.created_at)
    ).all()
    return [{"id": o.id, "event_type": o.event_type, "aggregate_id": o.aggregate_id} for o in rows]


@router.post("/demo/outbox/{outbox_id}/dispatch")
def mark_dispatched(
    outbox_id: str,
    principal: Principal = Depends(require("ops.read")),
    db: Session = Depends(get_db),
):
    row = db.get(Outbox, outbox_id)
    if row is None or row.workspace_id != principal.workspace.id:
        raise HTTPException(status_code=404, detail="outbox row not found")
    from app.services.worker_service import claim, complete
    if row.dispatched:
        return {"id": row.id, "dispatched": True}
    token = claim(db, "api-demo-" + principal.user.id, outbox_id, principal.workspace.id)
    if token is None or complete(db, token) != "completed":
        db.rollback()
        raise HTTPException(status_code=409, detail="lease conflict")
    db.commit()
    return {"id": row.id, "dispatched": True}
