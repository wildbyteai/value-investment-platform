"""DecisionService: AUTO accept per policy, HUMAN override precedence with CAS."""
from __future__ import annotations

import json

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.company import ItemCompanyLink
from app.models.intake import InformationItem, SourceRegistry
from app.models.judgment import JudgmentRevision, JudgmentSlot

from decimal import Decimal
from pathlib import Path
from app.models.runtime import ResearchInput
from app.services.transactions import workspace, record, canonical, digest
from app.models.runtime import CommandReceipt

AUTO_MIN_CONFIDENCE = Decimal("0.90")


def auto_decide(db: Session, workspace_id=None, actor_id=None) -> dict:
    """Create AUTO accepted impact revisions for accepted links. Idempotent."""
    from app.services.data_mode import require_fixture
    require_fixture()
    workspace_id = workspace(db, workspace_id)
    links = db.scalars(
        select(ItemCompanyLink).where(ItemCompanyLink.status == "accepted", ItemCompanyLink.item_id.in_(select(InformationItem.id).where(InformationItem.workspace_id == workspace_id, InformationItem.source_id.in_(select(SourceRegistry.id).where(SourceRegistry.source_key == "local-fixture")))))
    ).all()
    originals = json.loads((Path(__file__).resolve().parents[3] / 'examples/synthetic-analysis-evidence.json').read_text())['entries']
    created = 0
    for link in links:
        if link.company_id is None:
            continue
        # confidence threshold gate
        if link.confidence is None or float(link.confidence) < AUTO_MIN_CONFIDENCE:
            continue
        item = db.get(InformationItem, link.item_id)
        proposal = originals.get(item.entry_key)
        if proposal is None:
            continue
        original = db.scalar(select(ResearchInput).where(ResearchInput.workspace_id == workspace_id,
                             ResearchInput.input_key == 'impact-original:' + item.entry_key))
        if original is None:
            from datetime import datetime, timezone
            original = ResearchInput(workspace_id=workspace_id, company_id=link.company_id,
                input_key='impact-original:' + item.entry_key, kind='impact-original',
                payload_json=canonical(proposal), content_hash=digest(proposal),
                effective_at=datetime.now(timezone.utc), published_at=datetime.now(timezone.utc))
            db.add(original); db.flush()
        slot_key = f"{workspace_id}:impact:{link.item_id}:{link.company_id}"
        slot = db.scalar(select(JudgmentSlot).where(JudgmentSlot.slot_key == slot_key))
        if slot is None:
            slot = JudgmentSlot(workspace_id=workspace_id, company_id=link.company_id, slot_key=slot_key, kind="impact", dimension="business_model", generation=1)
            db.add(slot)
            db.flush()
            rev = JudgmentRevision(
                slot_id=slot.id,
                author_type="auto",
                value_json=canonical({"direction": "positive", "magnitude": proposal['magnitude'], "dimension": "business_model",
                                      "economic_fact_id": proposal['economic_fact_id'], "relevance": "0.9", "confidence": "0.95", "source_quality": "1"}),
                effective_at=original.effective_at, published_at=original.published_at,
                decision="accepted",
                evidence_json=canonical([{"input_id": original.id, "hash": original.content_hash, "locator": "original", "synthetic": True}]),
            )
            db.add(rev)
            db.flush()
            slot.effective_revision_id = rev.id
            slot.generation = 1
            record(db, workspace_id, actor_id, "judgment.auto_accepted", "judgment_slot", slot.id, {"revision_id": rev.id})
            created += 1
    from app.services.research_seed import seed_rubrics
    rubrics = seed_rubrics(db, workspace_id, actor_id)
    db.flush()
    return {"auto_accepted": created, "rubric_accepted": rubrics}


def human_override(db: Session, slot_key: str, value: dict, if_match_generation: int,
                   workspace_id=None, actor_id=None, command_key=None, release=False):
    workspace_id = workspace(db, workspace_id)
    if command_key:
        lock = int(digest({'workspace': workspace_id, 'key': command_key})[:16], 16)
        if lock >= 2**63: lock -= 2**64
        db.execute(select(func.pg_advisory_xact_lock(lock)))
    # Lock the actual slot before inspecting generation or issuing a revision.
    slot = db.scalar(select(JudgmentSlot).where(JudgmentSlot.slot_key == slot_key,
                     JudgmentSlot.workspace_id == workspace_id).with_for_update()
                     .execution_options(populate_existing=True))
    if slot is None:
        return None, "not_found", 0
    request_hash = digest({"slot": slot_key, "value": value, "release": release,
                           "generation": if_match_generation, "actor": actor_id})
    if command_key:
        receipt = db.scalar(select(CommandReceipt).where(CommandReceipt.workspace_id == workspace_id,
                                  CommandReceipt.command_key == command_key))
        if receipt:
            if receipt.request_hash != request_hash:
                return None, "conflict", slot.generation
            result = __import__('json').loads(receipt.response_json)
            return db.get(JudgmentRevision, result['id']), "ok", result['generation']
    if slot.generation != if_match_generation:
        return None, "conflict", slot.generation
    prior = db.get(JudgmentRevision, slot.effective_revision_id) if slot.effective_revision_id else None
    if not release:
        if prior is None or not json.loads(prior.evidence_json):
            raise ValueError('缺少该判断槽的有效输入证据')
        inherited=json.loads(prior.value_json)
        if slot.kind == 'impact':
            for key in ('economic_fact_id','relevance','confidence','source_quality'):
                if key in inherited and key in value and value[key] != inherited[key]:
                    raise ValueError('影响目标和证据参数不能随新值改写')
            value={**inherited,**value}
            magnitude = Decimal(str(value.get('magnitude')))
            if not magnitude.is_finite() or not Decimal('-1') <= magnitude <= Decimal('1'):
                raise ValueError('影响值必须在 -1 到 1 之间')
            value = {**value, 'dimension': slot.dimension, 'magnitude': str(magnitude),
                     'direction': 'positive' if magnitude > 0 else 'negative' if magnitude < 0 else 'neutral'}
        elif slot.kind == 'rubric':
            if type(value.get('grade')) is not int or not 0 <= value['grade'] <= 4:
                raise ValueError('档位必须是 0 到 4 的整数')
            criterion = json.loads(prior.value_json).get('criterion') if prior else None
            if value.get('criterion', criterion) != criterion:
                raise ValueError('不能修改判断槽的问题身份')
            value = {**value, 'criterion': criterion}
        else:
            raise ValueError('此接口不接受该判断类型')
    rev = JudgmentRevision(slot_id=slot.id, author_type="human", value_json=canonical(value),
                           decision="released" if release else "accepted")
    # Replacement inherits evidence scope/time; it cannot invent evidence.
    prior = db.get(JudgmentRevision, slot.effective_revision_id) if slot.effective_revision_id else None
    if prior:
        rev.evidence_json = prior.evidence_json
        rev.effective_at, rev.published_at, rev.valid_until = prior.effective_at, prior.published_at, prior.valid_until
    db.add(rev)
    db.flush()
    if release:
        auto = db.scalar(select(JudgmentRevision).where(JudgmentRevision.slot_id == slot.id,
                          JudgmentRevision.author_type == 'auto', JudgmentRevision.decision == 'accepted')
                         .order_by(JudgmentRevision.created_at.desc()).limit(1))
        slot.effective_revision_id = auto.id if auto else None
    else:
        slot.effective_revision_id = rev.id
    slot.generation += 1
    record(db, workspace_id, actor_id, 'judgment.released' if release else 'judgment.overridden',
           'judgment_slot', slot.id, {'revision_id': rev.id, 'generation': slot.generation,
                                     'recompute': 'read_with_current_revision'})
    if command_key:
        db.add(CommandReceipt(workspace_id=workspace_id, command_key=command_key,
                              request_hash=request_hash, response_json=canonical({'id': rev.id, 'generation': slot.generation})))
    db.flush()
    return rev, "ok", slot.generation


def effective_value(db: Session, slot: JudgmentSlot) -> dict | None:
    if slot.effective_revision_id is None:
        return None
    rev = db.get(JudgmentRevision, slot.effective_revision_id)
    return json.loads(rev.value_json) if rev else None
