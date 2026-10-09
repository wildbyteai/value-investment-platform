"""DecisionService: AUTO accept per policy, HUMAN override precedence with CAS."""
from __future__ import annotations
from app.core.paths import REPO_ROOT

import json

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.company import ItemCompanyLink
from app.models.intake import InformationItem, SourceRegistry
from app.models.judgment import JudgmentRevision, JudgmentSlot

from decimal import Decimal
from pathlib import Path
from app.models.runtime import ResearchInput
from app.domains.platform.transactions import workspace, record, canonical, digest
from app.models.runtime import CommandReceipt

AUTO_MIN_CONFIDENCE = Decimal("0.90")


def auto_decide(db: Session, workspace_id=None, actor_id=None) -> dict:
    """Create AUTO accepted impact revisions for accepted links. Idempotent."""
    from app.domains.platform.data_mode import require_fixture
    require_fixture()
    workspace_id = workspace(db, workspace_id)
    links = db.scalars(
        select(ItemCompanyLink).where(ItemCompanyLink.status == "accepted", ItemCompanyLink.item_id.in_(select(InformationItem.id).where(InformationItem.workspace_id == workspace_id, InformationItem.source_id.in_(select(SourceRegistry.id).where(SourceRegistry.source_key == "local-fixture")))))
    ).all()
    originals = json.loads((REPO_ROOT / 'examples/synthetic-analysis-evidence.json').read_text())['entries']
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
    from app.domains.companies.research_seed import seed_rubrics
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
    prior = db.get(JudgmentRevision, slot.effective_revision_id) if slot.effective_revision_id else db.scalar(select(JudgmentRevision).where(JudgmentRevision.slot_id==slot.id,JudgmentRevision.decision=='accepted').order_by(JudgmentRevision.created_at.desc()).limit(1))
    if prior is None and slot.kind=='rubric' and not release:
        prior=db.scalar(select(JudgmentRevision).where(JudgmentRevision.slot_id==slot.id,JudgmentRevision.decision=='pending')
                        .order_by(JudgmentRevision.created_at.desc()).limit(1))
        if prior:
            from datetime import datetime, timezone
            from app.models.company import Company
            from app.domains.companies.judgment_authoring import catalog
            now=datetime.now(timezone.utc);proposed=json.loads(prior.value_json)
            if not prior.valid_until or now>=prior.valid_until:
                raise ValueError('研判建议已过期，请用新证据重新研究')
            rules=catalog(db,db.get(Company,slot.company_id),workspace_id)
            if not any(r['dimension']==slot.dimension and r['rubric_ref']==proposed.get('rubric_ref') and
                       any(c['key']==proposed.get('criterion') for c in r['criteria']) for r in rules):
                raise ValueError('研判建议不属于当前模板')
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
            for key in ('rubric_ref', 'period_start', 'period_end'):
                if key in value and value[key] != inherited.get(key):
                    raise ValueError('不能修改rubric或期间身份')
            value = {**inherited, **value, 'criterion': criterion}
        else:
            raise ValueError('此接口不接受该判断类型')
    rev = JudgmentRevision(slot_id=slot.id, author_type="human", value_json=canonical(value),
                           decision="released" if release else "accepted")
    # Replacement inherits evidence scope/time; it cannot invent evidence.
    if prior:
        rev.evidence_json = prior.evidence_json
        rev.effective_at, rev.published_at, rev.valid_until = prior.effective_at, prior.published_at, prior.valid_until
    db.add(rev)
    db.flush()
    if release:
        # Release clears the human lock; current legal inputs must be reviewed.
        slot.effective_revision_id = None
    else:
        slot.effective_revision_id = rev.id
    slot.generation += 1
    record(db, workspace_id, actor_id, 'judgment.released' if release else 'judgment.overridden',
           'judgment_slot', slot.id, {'revision_id': rev.id, 'generation': slot.generation,
                                     'recompute': 'pending_review' if release else 'read_with_current_revision',
                                     'cutoff': db.scalar(select(func.clock_timestamp())).isoformat()})
    if command_key:
        db.add(CommandReceipt(workspace_id=workspace_id, command_key=command_key,
                              request_hash=request_hash, response_json=canonical({'id': rev.id, 'generation': slot.generation})))
    db.flush()
    return rev, "ok", slot.generation


def effective_value(db: Session, slot: JudgmentSlot) -> dict | None:
    from datetime import datetime, timezone
    from app.domains.companies.scoring_service import current_decisions
    now=datetime.now(timezone.utc)
    found=next((v for s,r,v in current_decisions(db,slot.company_id,slot.workspace_id,now,now) if s.id==slot.id),None)
    return found


def reevaluate_release(db, slot, cutoff):
    """Revalidate a proposal at one fixed cutoff; never point back to its old revision."""
    from datetime import datetime, timedelta, timezone
    from app.models.company import Company
    from app.domains.platform import data_mode
    from app.domains.companies.scoring_service import config, resolve_template, dec
    candidates=db.scalars(select(JudgmentRevision).where(JudgmentRevision.slot_id==slot.id,
        JudgmentRevision.author_type=='auto',JudgmentRevision.decision=='accepted',JudgmentRevision.created_at<=cutoff)
        .order_by(JudgmentRevision.created_at.desc())).all()
    template=resolve_template(db.get(Company,slot.company_id),db,slot.workspace_id,cutoff)
    policy=config('auto-review-policy-v1.json')
    for candidate in candidates:
        if candidate.effective_at and candidate.effective_at>cutoff: continue
        if candidate.published_at and candidate.published_at>cutoff: continue
        if candidate.valid_until and cutoff>=candidate.valid_until: continue
        value=json.loads(candidate.value_json);evidence=json.loads(candidate.evidence_json)
        if not evidence or slot.kind not in ('rubric','impact'): continue
        if not data_mode.fixture_mode():
            if not value.get('confidence_calibrated') or not data_mode.real_evidence(db,evidence,slot.workspace_id,slot.company_id,cutoff): continue
        if dec(value.get('confidence','0'))<dec(policy[slot.kind]['minimum_confidence']): continue
        if slot.dimension not in template['weights']: continue
        if slot.kind=='rubric':
            baseline=template['baselines'][slot.dimension]
            if baseline.get('rubric_ref')!=value.get('rubric_ref'): continue
            if not value.get('period_start','9999')<=cutoff.date().isoformat()<=value.get('period_end','0000'): continue
            quality=template['dimension_policies'][slot.dimension]['quality_policy']
            age=quality['freshness']['max_age_days']
            if cutoff>=(candidate.effective_at or candidate.created_at)+timedelta(days=age): continue
            if quality['evidence_requirement']=='issuer_or_regulator_original' and not all(e.get('issuer_original') for e in evidence): continue
        revision=JudgmentRevision(slot_id=slot.id,author_type='auto',decision='accepted',
            value_json=candidate.value_json,evidence_json=candidate.evidence_json,
            effective_at=candidate.effective_at,published_at=candidate.published_at,valid_until=candidate.valid_until)
        db.add(revision);db.flush();slot.effective_revision_id=revision.id;slot.generation+=1
        record(db,slot.workspace_id,None,'judgment.reevaluated','judgment_slot',slot.id,
            {'revision_id':revision.id,'generation':slot.generation,'cutoff':cutoff.isoformat(),
             'prior_proposal':candidate.id,'policy_hash':digest(policy),'template_hash':template['config_hash']})
        return 'reevaluated'
    return 'pending_review'
