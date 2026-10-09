"""Human rubric authoring with immutable identity, fixed accessible evidence and receipts."""
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from app.core.errors import Conflict, Invalid
from sqlalchemy import select, func
from app.models.judgment import JudgmentSlot, JudgmentRevision
from app.models.runtime import ItemRevision, CommandReceipt
from app.models.intake import InformationItem, SourceRegistry
from app.domains.platform import data_mode
from app.domains.companies.scoring_service import config, resolve_template, current_decisions, score_company
from app.domains.platform.transactions import digest, canonical, record


def catalog(db, company, workspace_id):
    template = resolve_template(company, db, workspace_id)
    rubrics = config('rubrics-standard-v1.json')['rubrics']
    if data_mode.fixture_mode(): rubrics = {**rubrics, **config('rubrics-synthetic-v03.json')['rubrics']}
    return [{'dimension': d, 'rubric_ref': b['rubric_ref'], **rubrics[b['rubric_ref']],
             'quality_policy': template['dimension_policies'][d]['quality_policy']}
            for d, b in template['baselines'].items() if b['method']=='accepted_evidence_rubric' and b['rubric_ref'] in rubrics]


def pending_proposals(db, company_id, workspace_id, cutoff):
    """Freeze readable advice separately from accepted calculation decisions."""
    rows=[]
    slots=db.scalars(select(JudgmentSlot).where(JudgmentSlot.company_id==company_id,
                       JudgmentSlot.workspace_id==workspace_id)).all()
    for slot in slots:
        revision=db.scalar(select(JudgmentRevision).where(JudgmentRevision.slot_id==slot.id,
                         JudgmentRevision.created_at<=cutoff).order_by(JudgmentRevision.created_at.desc()).limit(1))
        if not revision or revision.decision!='pending' or revision.author_type!='auto':continue
        if revision.effective_at and revision.effective_at>cutoff:continue
        if revision.published_at and revision.published_at>cutoff:continue
        if not revision.valid_until or cutoff>=revision.valid_until:continue
        evidence=json.loads(revision.evidence_json)
        if not data_mode.fixture_mode() and not data_mode.real_evidence(db,evidence,workspace_id,company_id,cutoff):continue
        value=json.loads(revision.value_json)
        rows.append({'revision_id':revision.id,'dimension':slot.dimension,'value':value,'evidence':evidence,
                     'hash':digest({'value':value,'evidence':evidence}),'status':'pending_review'})
    return rows


def create(db, principal, body, command_key, *, proposal=False):
    ws = principal.workspace.id
    request = body.model_dump(mode='json')
    request_hash = digest({'actor':principal.user.id, 'request':request, **({'proposal':True} if proposal else {})})
    db.execute(select(func.pg_advisory_xact_lock(int(digest({'ws':ws, 'key':command_key})[:15],16))))
    receipt = db.scalar(select(CommandReceipt).where(CommandReceipt.workspace_id==ws, CommandReceipt.command_key==command_key))
    if receipt:
        if receipt.request_hash != request_hash: raise Conflict('幂等命令已用于不同输入')
        return json.loads(receipt.response_json)
    company = data_mode.require_company(db, body.company_id, ws)
    rule = next((r for r in catalog(db, company, ws) if r['dimension']==body.dimension and r['rubric_ref']==body.rubric_ref), None)
    if not rule or not any(c['key']==body.criterion for c in rule['criteria']): raise Invalid('评价项不属于当前发布的公司模板')
    now = db.scalar(select(func.now()))
    if body.period_start > body.period_end: raise Invalid('研究期间起止不合法')
    if not body.effective_from.tzinfo or not body.valid_until.tzinfo: raise Invalid('有效时间必须包含时区')
    if not body.effective_from < body.valid_until or body.effective_from > now: raise Invalid('有效时间不合法或尚未生效')
    if body.valid_until <= now: raise Invalid('研判已经过期')
    max_age = rule['quality_policy'].get('freshness', {}).get('max_age_days',rule['validity_days'])
    if (body.valid_until-body.effective_from).total_seconds() > min(max_age,rule['validity_days'])*86400:
        raise Invalid('有效期限超过当前模板允许范围')
    refs=[]
    for e in body.evidence:
        revision=db.get(ItemRevision,e.source_revision_id)
        item=db.get(InformationItem,revision.item_id) if revision else None
        if not revision or not data_mode.readable_item(db,item,ws): raise Invalid('证据资料不可读')
        payload=json.loads(revision.payload_json)
        original=payload.get('readable_text','')
        if digest(payload)!=revision.content_hash or e.hash!=revision.content_hash: raise Invalid('证据修订或hash已变化')
        if not 0<=e.start<e.end<=len(original) or original[e.start:e.end]!=e.quote: raise Invalid('证据定位与原文不一致')
        policy=json.loads(db.get(SourceRegistry,item.source_id).policy_json)
        issuer=policy.get('evidence_category') in ('issuer_original','regulator_original')
        # Validated statutory report bundles are issuer originals even though the
        # original personal-study source registration predates category metadata.
        from app.domains.companies.issuer_reports import POLICY,validate
        raw=payload.get('raw_capture',{})
        if db.get(SourceRegistry,item.source_id).source_key=='cninfo-reviewed-statements' and policy==POLICY and raw.get('report_type')=='reviewed_original_statements':
            checked={**raw,'documents':[{**d,'observed_at':json.loads(item.reading_metadata_json)['source_observed_at']} for d in raw['documents']]}
            try:validate(checked)
            except (ValueError,KeyError,TypeError):raise Invalid('发行人原文载荷校验失败')
            issuer=True
        ref={'synthetic':False,'source_revision_id':revision.id,'hash':revision.content_hash,
             'locator':f'readable_text[{e.start}:{e.end}]','quote':e.quote,'relation':e.relation,
             'issuer_original':issuer,'item_id':item.id}
        if not data_mode.real_evidence(db,[ref],ws,company.id,now): raise Invalid('证据缺少公司关联或本地分析许可')
        refs.append(ref)
    if not any(e['relation']=='supports' for e in refs): raise Invalid('至少需要一项支持证据')
    identity={'ws':ws,'company':company.id,'rubric':body.rubric_ref,'criterion':body.criterion,
              'period_start':body.period_start.isoformat(),'period_end':body.period_end.isoformat()}
    key='rubric:'+digest(identity)
    db.execute(select(func.pg_advisory_xact_lock(int(digest(identity)[:15],16))))
    if db.scalar(select(JudgmentSlot).where(JudgmentSlot.slot_key==key)):
        raise Conflict('此公司、评价项和期间已有研判，请修改现有判断')
    slot=JudgmentSlot(slot_key=key,workspace_id=ws,company_id=company.id,kind='rubric',dimension=body.dimension,generation=1)
    db.add(slot);db.flush()
    value={'rubric_ref':body.rubric_ref,'criterion':body.criterion,'period_start':body.period_start.isoformat(),
           'period_end':body.period_end.isoformat(),'grade':body.grade,'confidence':str(body.confidence),'reason':body.reason.strip()}
    if proposal:
        value.update({'confidence_calibrated':False,'research_method':body.research_method,
                      'author_label':body.author_label,'limitations':body.limitations.strip(),
                      'acceptance_reason':'未经校准的AI研判建议，等待有权限人员确认'})
    revision=JudgmentRevision(slot_id=slot.id,author_type='auto' if proposal else 'human',
        decision='pending' if proposal else 'accepted',value_json=canonical(value),
        evidence_json=canonical(refs),effective_at=body.effective_from,published_at=now,valid_until=body.valid_until)
    db.add(revision);db.flush();slot.effective_revision_id=None if proposal else revision.id
    record(db,ws,principal.user.id,'judgment.proposed' if proposal else 'judgment.created','judgment_slot',slot.id,{'revision_id':revision.id,'generation':1})
    applicable = any(r.id==revision.id for s,r,v in current_decisions(db,company.id,ws,datetime.now(timezone.utc),datetime.now(timezone.utc)))
    current_score=score_company(db,company,ws)
    eligible=any(c.get('revision_id')==revision.id and c['status']=='valid' for d in current_score['dimensions'].values() for c in d.get('criteria',[]))
    result={'id':revision.id,'slot_key':key,'generation':1,'value':value,'saved':True,
            'applicability':'pending_review' if proposal else 'eligible' if eligible else 'outside_period_or_evidence_policy',
            'score_status':'读取公司评分以核对质量门；已有研究快照不更新'}
    db.add(CommandReceipt(workspace_id=ws,command_key=command_key,request_hash=request_hash,response_json=canonical(result)))
    return result
