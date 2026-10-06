"""Local durable effects only. There is no recipient, channel or external send."""
import json
from datetime import timedelta
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from app.models.audit import Outbox
from app.models.runtime import WorkEffect


def claim(db: Session, owner: str, outbox_id=None, workspace_id=None, lease_seconds=30):
    conditions = [Outbox.dispatched.is_(False), Outbox.attempts < 3, Outbox.workspace_id.is_not(None),
                  or_(Outbox.lease_until.is_(None), Outbox.lease_until <= func.now())]
    if outbox_id:
        conditions.append(Outbox.id == outbox_id)
    if workspace_id:
        conditions.append(Outbox.workspace_id == workspace_id)
    row = db.scalar(select(Outbox).where(*conditions).order_by(Outbox.created_at)
                    .with_for_update(skip_locked=True).limit(1))
    if row is None:
        return None
    row.generation += 1
    row.attempts += 1
    row.lease_owner = owner
    row.lease_until = db.scalar(select(func.now())) + timedelta(seconds=lease_seconds)
    db.flush()
    return {'id': row.id, 'owner': owner, 'fence': row.generation}


def complete(db: Session, token: dict):
    row = db.scalar(select(Outbox).where(Outbox.id == token['id']).with_for_update()
                    .execution_options(populate_existing=True))
    now = db.scalar(select(func.now()))
    if row is None or row.generation != token['fence'] or row.lease_owner != token['owner']:
        return 'stale_fence'
    if row.dispatched:
        return 'already_completed'
    if row.lease_until is None or row.lease_until <= now:
        return 'expired'
    # Effect and acknowledgment commit atomically. Unique primary key prevents a
    # second effect after a lost acknowledgment. Unknown event types fail closed.
    supported = ('ingestion', 'judgment', 'strategy', 'template', 'research', 'note', 'watchlist', 'membership')
    if not row.event_type.startswith(supported):
        row.last_error = 'UNSUPPORTED_EVENT'
        return 'unsupported'
    if db.get(WorkEffect, row.id) is None:
        result = {'event': row.event_type, 'status': 'recorded_local'}
        if row.aggregate_type == 'judgment_slot':
            from app.models.judgment import JudgmentSlot
            from app.models.company import Company, Security
            from app.services.scoring_service import score_company, score_security
            slot = db.scalar(select(JudgmentSlot).where(JudgmentSlot.id==row.aggregate_id).with_for_update().execution_options(populate_existing=True))
            generation = json.loads(row.payload_json).get('generation')
            if slot and generation is not None and generation != slot.generation:
                result['status'] = 'superseded'
            elif slot and slot.company_id:
                if row.event_type=='judgment.released':
                    from datetime import datetime
                    from app.services.decision_service import reevaluate_release
                    cutoff=json.loads(row.payload_json).get('cutoff')
                    if cutoff:
                        result['reassessment']=reevaluate_release(db,slot,datetime.fromisoformat(cutoff))
                    else:
                        result['reassessment']='pending_review' # legacy event lacks fixed cutoff
                company = db.get(Company, slot.company_id)
                result['company_id'] = company.id
                result['score'] = score_company(db, company, row.workspace_id)
                result['securities'] = [score_security(db,s,row.workspace_id) for s in db.scalars(
                    select(Security).where(Security.company_id == company.id))]
        db.add(WorkEffect(id=row.id, result_json=json.dumps(result,ensure_ascii=False)))
    row.dispatched = True
    row.last_error = None
    return 'completed'
