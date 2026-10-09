import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal, require
from app.db import get_db
from app.domains.platform import data_mode
from app.models.intake import InformationItem, ItemSourceRef, SourceRegistry
from app.domains.news.intake_service import import_fixture

router = APIRouter(prefix="/api/intake", tags=['资讯雷达'])


@router.post("/synthetic")
def ingest_synthetic(
    principal: Principal = Depends(require("source.manage")),
    db: Session = Depends(get_db),
):
    """data_admin imports the synthetic fixture. Idempotent by entry_key."""
    data_mode.require_fixture()
    from services_companies import seed_companies, link_items
    seed_companies(db, principal.workspace.id)
    run = import_fixture(db, workspace_id=principal.workspace.id, actor_id=principal.user.id)
    link_items(db, principal.workspace.id)
    db.commit()
    return {
        "run_id": run.id,
        "status": run.status,
        "output": json.loads(run.output_json or "{}"),
    }


@router.get("/items")
def list_items(
    principal: Principal = Depends(require("research.read")),
    db: Session = Depends(get_db),
):
    """Timeline of readable items. Sorted: dated first (newest), unknown-date last."""
    items = db.scalars(select(InformationItem).where(InformationItem.workspace_id == principal.workspace.id).order_by(InformationItem.observed_at.desc())).all()
    out = []
    for it in items:
        if not data_mode.readable_item(db, it, principal.workspace.id): continue
        source = db.get(SourceRegistry, it.source_id)
        if json.loads(source.policy_json).get("revoked"): continue
        pub = json.loads(it.publication_json)
        out.append({
            "id": it.id,
            "title": it.title,
            "content_kind": it.content_kind,
            "source_name": source.name,
            "material_type": json.loads(it.reading_metadata_json).get("material_type"),
            "publication_date": pub.get("date"),
            "precision": pub.get("precision"),
            "body_state": it.body_state,
            "summary_text": it.summary_text,
            "observed_at": it.observed_at.isoformat(),
        })
    # sort: known date desc first, unknown date last (stable)
    def sort_key(x):
        return (0 if x["publication_date"] else 1, x["publication_date"] or "", x["observed_at"])
    out.sort(key=sort_key, reverse=False)
    dated = [x for x in out if x["publication_date"]]
    unknown = [x for x in out if not x["publication_date"]]
    dated.sort(key=lambda x: x["publication_date"], reverse=True)
    return dated + unknown


@router.get("/items/{item_id}")
def get_item(
    item_id: str,
    revision_id: str | None = None,
    principal: Principal = Depends(require("research.read")),
    db: Session = Depends(get_db),
):
    it = db.get(InformationItem, item_id)
    if it is None or it.workspace_id != principal.workspace.id:
        raise HTTPException(status_code=404, detail="item not found")
    if not data_mode.fixture_mode() and not data_mode.real_item(db, it, principal.workspace.id):
        raise HTTPException(404, '当前研究模式没有该资料')
    refs = db.scalars(select(ItemSourceRef).where(ItemSourceRef.item_id == it.id)).all()
    pub = json.loads(it.publication_json)
    meta = json.loads(it.reading_metadata_json)
    source = db.get(SourceRegistry, it.source_id)
    policy = json.loads(source.policy_json)
    if policy.get('revoked'):
        raise HTTPException(status_code=403, detail="来源阅读权限已撤销")
    from app.models.runtime import ItemRevision, ItemObservation
    selected_revision = revision_id or it.current_revision_id
    revision = db.get(ItemRevision, selected_revision) if selected_revision else None
    if revision_id and (not revision or revision.item_id != it.id):
        raise HTTPException(404, '没有该资料的修订')
    payload = json.loads(revision.payload_json) if revision else {}
    snapshot = payload.get('item_snapshot')
    is_current = selected_revision == it.current_revision_id
    # Legacy history never substitutes mutable metadata for an old revision.
    if snapshot is None and is_current:
        snapshot = {'title': it.title, 'content_kind': it.content_kind,
                    'summary_text': it.summary_text, 'publication': pub,
                    'reading_metadata': meta, 'body_access': {'state': it.body_state, 'url': it.body_url}}
    snapshot = snapshot or {}
    observation = db.scalar(select(ItemObservation)
        .where(ItemObservation.revision_id == selected_revision)
        .order_by(ItemObservation.sequence).limit(1))
    return {
        'id': it.id, 'title': snapshot.get('title') or '历史原文（标题未留存）',
        'content_kind': snapshot.get('content_kind'), 'summary_text': snapshot.get('summary_text'),
        'original_text': payload.get('readable_text'),
        'revision': {'id': revision.id, 'hash': revision.content_hash} if revision else None,
        'metadata_state': 'saved' if payload.get('item_snapshot') else 'legacy_current' if is_current else 'unavailable',
        'data_mode': 'synthetic_test' if data_mode.fixture_mode() else 'real_public',
        'source': {'name': source.name, 'policy': policy},
        'reading_metadata': snapshot.get('reading_metadata', {}),
        'publication': snapshot.get('publication', {}),
        'observed_at': observation.observed_at.isoformat() if observation else None,
        'body_access': snapshot.get('body_access', {'state': 'unknown', 'url': None}),
        'reference_access': [{'reference_key': r.reference_key, 'source_name': r.source_name,
            'locator_kind': r.locator_kind, 'access': {'state': r.access_state, 'url': r.url}}
            for r in refs] if is_current else [],
    }
