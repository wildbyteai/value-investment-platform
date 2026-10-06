"""Explicit synthetic financial originals; never called by real-source ingestion."""
import json
from datetime import datetime, timezone
from sqlalchemy import select
from app.models.runtime import ResearchInput
from app.models.judgment import JudgmentSlot, JudgmentRevision
from app.services.transactions import workspace, canonical, digest, record
from app.services.scoring_service import ROOT, config


def seed_inputs(db, company, workspace_id=None):
    from app.services.data_mode import require_fixture
    require_fixture()
    workspace_id=workspace(db,workspace_id)
    if company.id != '00000000-0000-4000-8000-000000000001': return
    fixture=json.loads((ROOT/'examples/research-inputs-v0001.json').read_text())
    effective=datetime.fromisoformat(fixture['effective_at']);published=datetime.fromisoformat(fixture['published_at'])
    entries=[('financials','financials',fixture['financials'])]
    entries += [('price:'+p['ticker'],'price',p) for p in fixture['prices']]
    entries += [('rubric-original','rubric-original',{'grades':fixture['rubric_grades'],
        'text':'原创合成研究：11项事实锚点均为档位3；客户留存档位3。仅用于验收，非真实公司。',
        'issuer_original':True})]
    for key,kind,payload in entries:
        if db.scalar(select(ResearchInput).where(ResearchInput.workspace_id==workspace_id,
                   ResearchInput.company_id==company.id,ResearchInput.input_key==key)) is None:
            db.add(ResearchInput(workspace_id=workspace_id,company_id=company.id,input_key=key,kind=kind,
                payload_json=canonical(payload),content_hash=digest(payload),effective_at=effective,published_at=published))
    db.flush()


def seed_rubrics(db, workspace_id=None, actor_id=None):
    workspace_id=workspace(db,workspace_id)
    original=db.scalar(select(ResearchInput).where(ResearchInput.workspace_id==workspace_id,
                       ResearchInput.kind=='rubric-original'))
    if original is None: return 0
    payload=json.loads(original.payload_json)
    catalog={**config('rubrics-standard-v1.json')['rubrics'],**config('rubrics-synthetic-v03.json')['rubrics']}
    mapping={'business_model':'business-model-v1','governance':'governance-v1',
             'growth_sustainability':'growth-v1','x_customer_retention':'customer-retention-synthetic-v1'}
    created=0
    for dim,rubric in mapping.items():
        for criterion in catalog[rubric]['criteria']:
            key=f'{workspace_id}:rubric:{original.company_id}:{dim}:{criterion["key"]}'
            if db.scalar(select(JudgmentSlot).where(JudgmentSlot.slot_key==key)): continue
            slot=JudgmentSlot(workspace_id=workspace_id,company_id=original.company_id,slot_key=key,kind='rubric',dimension=dim,generation=1)
            db.add(slot);db.flush()
            rev=JudgmentRevision(slot_id=slot.id,author_type='auto',decision='accepted',
                effective_at=original.effective_at,published_at=original.published_at,
                evidence_json=canonical([{'input_id':original.id,'hash':original.content_hash,'locator':criterion['key'],
                                          'issuer_original':True}]),
                value_json=canonical({'rubric_ref':rubric,'period_start':'2026-01-01','period_end':'2026-12-31','criterion':criterion['key'],'grade':payload['grades'][dim],'confidence':'0.95'}))
            db.add(rev);db.flush();slot.effective_revision_id=rev.id
            record(db,workspace_id,actor_id,'judgment.auto_accepted','judgment_slot',slot.id,{'revision_id':rev.id})
            created+=1
    return created
