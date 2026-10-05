import hashlib
import json
from sqlalchemy import select
from app.models.audit import AuditLog, Outbox
from app.models.identity import Workspace


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value): return hashlib.sha256(canonical(value).encode()).hexdigest()


def workspace(db, workspace_id=None):
    if workspace_id:
        return workspace_id
    return db.scalar(select(Workspace.id).where(Workspace.name == '演示研究组织（合成数据）'))


def record(db, workspace_id, actor_id, action, entity_type, entity_id, detail=None):
    payload = canonical(detail or {})
    db.add(AuditLog(workspace_id=workspace_id, actor_user_id=actor_id, action=action,
                    entity_type=entity_type, entity_id=entity_id, detail_json=payload))
    db.add(Outbox(workspace_id=workspace_id, aggregate_type=entity_type,
                  aggregate_id=entity_id, event_type=action, payload_json=payload))
