"""Synthetic local-fixture importer for W-08.2.

Reads examples/information-intake.json, upserts source/items/refs and records an
IngestionRun with an output manifest. Idempotent by (source_id, entry_key).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import IngestionRun
from app.models.intake import InformationItem, ItemSourceRef, SourceRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = PROJECT_ROOT / "examples" / "information-intake.json"

SOURCE_KEY = "local-fixture"
SOURCE_NAME = "本地合成日报（演示数据）"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_source(db: Session) -> SourceRegistry:
    src = db.scalar(select(SourceRegistry).where(SourceRegistry.source_key == SOURCE_KEY))
    if src is None:
        src = SourceRegistry(
            source_key=SOURCE_KEY,
            name=SOURCE_NAME,
            policy_json=json.dumps({
                "fetch": "synthetic_local_file",
                "store": "local_db_only",
                "analyze": "local_only",
                "export": "synthetic_demo_only",
            }),
        )
        db.add(src)
        db.flush()
    return src


def import_fixture(db: Session, extra_fail_keys: list[str] | None = None, workspace_id=None, actor_id=None) -> IngestionRun:
    """Import the synthetic fixture. Returns the created run.

    extra_fail_keys: entry keys that should be recorded as failed (partial-failure demo).
    """
    from app.services.data_mode import require_fixture
    require_fixture()
    from app.services.transactions import workspace, digest, record
    from app.services.item_history import observe
    workspace_id = workspace(db, workspace_id)
    extra_fail_keys = extra_fail_keys or []
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    source = get_or_create_source(db)

    run = IngestionRun(
        workspace_id=workspace_id,
        source_key=SOURCE_KEY,
        status="running",
        input_manifest_hash=digest(data),
        note="synthetic fixture import",
        upstream_generated_at=_now(),
    )
    db.add(run)
    db.flush()

    entry_results = []
    imported = 0
    failed = 0

    for entry in data["entries"]:
        key = entry["entry_key"]
        if key in extra_fail_keys:
            entry_results.append({"entry_key": key, "status": "failed", "error_code": "INJECTED_FAIL"})
            failed += 1
            continue
        # minimal shape validation: title + publication required
        if not entry.get("title") or "publication" not in entry:
            entry_results.append({"entry_key": key, "status": "failed", "error_code": "INVALID_ROW"})
            failed += 1
            continue

        item = db.scalar(
            select(InformationItem).where(
                InformationItem.source_id == source.id,
                InformationItem.entry_key == key,
                InformationItem.workspace_id == workspace_id,
            )
        )
        if item is None:
            item = InformationItem(workspace_id=workspace_id, source_id=source.id, entry_key=key)
            db.add(item)
        item.title = entry["title"]
        item.content_kind = entry["content_kind"]
        item.summary_text = entry.get("summary_text")
        item.reading_metadata_json = json.dumps(entry.get("reading_metadata", {}), ensure_ascii=False)
        item.publication_json = json.dumps(entry["publication"], ensure_ascii=False)
        item.origin_locator_json = (
            json.dumps(entry["origin_locator"], ensure_ascii=False) if entry.get("origin_locator") else None
        )
        # body state: no url refs -> no_locator; has url -> not_acquired (we never fetch real body in slice)
        refs = entry.get("source_references", [])
        item.body_state = "no_locator" if not refs else "not_acquired"
        item.body_url = None

        db.flush()
        revision = observe(db, item, entry)
        # replace refs
        db.query(ItemSourceRef).filter(ItemSourceRef.item_id == item.id).delete()
        for ref in refs:
            db.add(ItemSourceRef(
                item_id=item.id,
                reference_key=ref["reference_key"],
                source_name=ref["source_name"],
                url=ref.get("url"),
                locator_kind=ref.get("locator_kind", "unknown"),
                source_locator_json=(
                    json.dumps(ref["source_locator"], ensure_ascii=False)
                    if ref.get("source_locator") else None
                ),
                access_state="available" if ref.get("url") else "restricted",
            ))

        entry_results.append({
            "entry_key": key,
            "status": "imported",
            "item_revision_id": revision.id,
        })
        imported += 1

    run.status = "partial" if failed else "completed"
    run.output_json = json.dumps(
        {"imported": imported, "failed": failed, "entry_results": entry_results},
        ensure_ascii=False,
    )
    record(db,workspace_id,actor_id,"ingestion.completed","ingestion_run",run.id,{"input_hash":run.input_manifest_hash,"status":run.status})
    db.flush()
    return run
