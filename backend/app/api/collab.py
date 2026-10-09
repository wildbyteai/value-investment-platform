import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, require
from app.db import get_db
from app.domains.platform import data_mode
from app.models.audit import Outbox
from app.models.collab import Note, Watchlist
from app.models.company import Company, Security

router = APIRouter(prefix="/api/me", tags=['我的自选与笔记'])


@router.post("/watchlist/{security_id}")
def add_watch(
    security_id: str,
    principal: Principal = Depends(require("watchlist.own")),
    db: Session = Depends(get_db),
):
    security=db.get(Security,security_id)
    if security is None: raise HTTPException(404,'security not found')
    data_mode.require_company(db,security.company_id,principal.workspace.id)
    exists = db.scalar(
        select(Watchlist).where(
            Watchlist.user_id == principal.user.id,
            Watchlist.workspace_id == principal.workspace.id,
            Watchlist.security_id == security_id,
        )
    )
    if exists is None:
        if db.get(Security, security_id) is None:
            raise HTTPException(status_code=404, detail="security not found")
        db.add(Watchlist(workspace_id=principal.workspace.id, user_id=principal.user.id, security_id=security_id))
        from app.domains.platform.transactions import record
        record(db,principal.workspace.id,principal.user.id,'watchlist.added','security',security_id)
        db.commit()
    return {"security_id": security_id, "watching": True}


@router.get("/watchlist")
def list_watch(
    principal: Principal = Depends(require("watchlist.own")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Watchlist).where(Watchlist.user_id == principal.user.id, Watchlist.workspace_id == principal.workspace.id)).all()
    secs = [db.get(Security, r.security_id) for r in rows]
    allowed={c.id for c in data_mode.companies(db,principal.workspace.id)}
    return [{"security_id": s.id, "company_id": s.company_id, "ticker": s.ticker, "market": s.market} for s in secs if s and s.company_id in allowed]


@router.delete('/watchlist/{security_id}')
def remove_watch(security_id: str, principal: Principal = Depends(require('watchlist.own')), db: Session = Depends(get_db)):
    security = db.get(Security, security_id)
    if security is None: raise HTTPException(404, '没有该证券')
    data_mode.require_company(db, security.company_id, principal.workspace.id)
    row = db.scalar(select(Watchlist).where(Watchlist.user_id == principal.user.id,
        Watchlist.workspace_id == principal.workspace.id, Watchlist.security_id == security_id).with_for_update())
    if row:
        db.delete(row)
        from app.domains.platform.transactions import record
        record(db, principal.workspace.id, principal.user.id, 'watchlist.removed', 'security', security_id)
        db.commit()
    return {'security_id': security_id, 'watching': False}


class NoteIn(BaseModel):
    company_id: str
    body: str


@router.post("/notes")
def add_note(
    body: NoteIn,
    principal: Principal = Depends(require("notes.own")),
    db: Session = Depends(get_db),
):
    data_mode.require_company(db,body.company_id,principal.workspace.id)
    if db.get(Company, body.company_id) is None:
        raise HTTPException(status_code=404, detail="company not found")
    n = Note(workspace_id=principal.workspace.id, user_id=principal.user.id, company_id=body.company_id, body=body.body)
    db.add(n)
    db.flush()
    from app.domains.platform.transactions import record
    record(db,principal.workspace.id,principal.user.id,'note.added','note',n.id)
    db.commit()
    return {"id": n.id}


@router.get("/notes")
def list_notes(
    principal: Principal = Depends(require("notes.own")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Note).where(Note.user_id == principal.user.id, Note.workspace_id == principal.workspace.id)).all()
    allowed={c.id for c in data_mode.companies(db,principal.workspace.id)}
    return [{"id": n.id, "company_id": n.company_id, "body": n.body} for n in rows if n.company_id in allowed]


# --- Worker: idempotent claim/dispatch (fencing by generation) ---
worker_router = APIRouter(prefix="/api/worker", tags=['后台任务'])


@worker_router.post("/outbox/{outbox_id}/claim")
def claim_outbox(
    outbox_id: str,
    principal: Principal = Depends(require("ops.read")),
    db: Session = Depends(get_db),
):
    from app.domains.platform.worker_service import claim, complete
    row = db.get(Outbox, outbox_id)
    if row is None or row.workspace_id != principal.workspace.id:
        raise HTTPException(status_code=404, detail="not found")
    if row.dispatched:
        return {"id": row.id, "already_dispatched": True}
    token = claim(db, "api-local-" + principal.user.id, outbox_id, principal.workspace.id)
    if token is None:
        raise HTTPException(status_code=409, detail="already leased")
    result = complete(db, token)
    if result != "completed":
        db.rollback()
        raise HTTPException(status_code=409, detail=result)
    db.commit()
    return {"id": token["id"], "claimed": True, "generation": token["fence"]}


@worker_router.get('/tasks')
def tasks(principal: Principal = Depends(require('ops.read')), db: Session = Depends(get_db)):
    rows = db.scalars(select(Outbox).where(Outbox.workspace_id == principal.workspace.id)
                      .order_by(Outbox.created_at.desc()).limit(100)).all()
    if not data_mode.fixture_mode():
        from app.models.audit import IngestionRun
        from app.models.intake import SourceRegistry
        allowed_companies={c.id for c in data_mode.companies(db,principal.workspace.id)}
        def visible(r):
            if r.aggregate_type=='ingestion_run':
                run=db.get(IngestionRun,r.aggregate_id)
                src=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key==run.source_key)) if run else None
                return src and json.loads(src.policy_json).get('license') and not json.loads(src.policy_json).get('revoked')
            if r.aggregate_type=='company': return r.aggregate_id in allowed_companies
            if r.aggregate_type=='security':
                sec=db.get(Security,r.aggregate_id)
                return sec and sec.company_id in allowed_companies
            if r.aggregate_type=='note':
                note=db.get(Note,r.aggregate_id)
                return note and note.company_id in allowed_companies
            return False
        rows=[r for r in rows if visible(r)]
    return [{'id':r.id,'stage':r.event_type,'status':'completed' if r.dispatched else 'failed' if r.attempts>=3 else 'waiting',
             'attempts':r.attempts,'error':r.last_error} for r in rows]


@worker_router.post('/outbox/{outbox_id}/retry')
def retry(outbox_id: str, principal: Principal = Depends(require('job.retry')), db: Session = Depends(get_db)):
    from sqlalchemy import func
    from app.domains.platform.transactions import record
    row = db.scalar(select(Outbox).where(Outbox.id == outbox_id, Outbox.workspace_id == principal.workspace.id)
                    .with_for_update().execution_options(populate_existing=True))
    if row is None:
        raise HTTPException(404, '没有该工作区的任务')
    if row.dispatched:
        return {'id': row.id, 'status': 'completed'}
    if row.lease_until and row.lease_until > db.scalar(select(func.now())):
        raise HTTPException(409, '任务仍在处理，请等待租约结束')
    row.generation += 1
    row.attempts = 0
    row.lease_owner = None
    row.lease_until = None
    row.last_error = None
    record(db, principal.workspace.id, principal.user.id, 'research.task_retried', 'outbox', row.id)
    db.commit()
    return {'id': row.id, 'status': 'waiting'}

@worker_router.get('/sources')
def source_runs(principal: Principal = Depends(require('ops.read')), db: Session = Depends(get_db)):
    from app.models.audit import IngestionRun
    rows=db.scalars(select(IngestionRun).where(IngestionRun.workspace_id==principal.workspace.id)
                    .order_by(IngestionRun.created_at.desc()).limit(100)).all()
    # Operations metadata only: no source content, source URLs or private run notes.
    return [{'id':r.id,'source_key':r.source_key,'status':r.status} for r in rows]
