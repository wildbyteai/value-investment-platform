"""Internal strategy-worker sealing. No HTTP command can supply a final price or cutoff."""
import json
import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from app.core.errors import Conflict, Forbidden, NotFound
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from app.models.sealing import (EvaluationSeal, FrozenManifest, PrimaryListing, MarketSession,
                                KnowledgeEntry, SafetyGeneration, InstalledArtifact)
from app.models.company import Company, Security
from app.models.runtime import Evaluation, ResearchInput
from app.models.strategy import StrategyVersion, SecurityState, ChangeRecord
from app.models.intake import SourceRegistry
from app.services import data_mode, algorithm_versions
from app.services.transactions import canonical, digest, record
from app.services.scoring_service import inputs, input_time_bounds, current_decisions, resolve_template, score_company, score_security, config, ROOT
from app.services.strategy_service import gates
from app.services.state_machine import Eval, apply_session

GROUPS=('identity','calendar','price','fx','share_capital','financials','report_obligations','links',
        'impacts','rubrics','risks','human_overrides','templates','decision_policies','algorithms','rights')
CONFIGS=('numeric-policy-v1.json','auto-review-policy-v1.json','scoring-standard-v1.json',
         'rubrics-standard-v1.json','metric-definitions-v2.json','dimensions-standard-v1.json','templates-standard-v1.json')
ALGORITHMS=('scoring_service.py','strategy_service.py','state_machine.py','sealing_service.py','knowledge_clock.py','share_capital.py')


@dataclass(frozen=True)
class WorkerContext:
    owner: str
    capabilities: frozenset


def authorize(context):
    if not isinstance(context,WorkerContext) or 'strategy.seal' not in context.capabilities:
        raise Forbidden('仅受限策略worker可以冻结与封存')


def clock(db): return db.scalar(select(func.vip_knowledge_now()))


def runtime_artifacts():
    artifacts={name:config(name) for name in CONFIGS}
    for name in ALGORITHMS:
        # Released fingerprint, not a live file hash: see algorithm_versions.
        artifacts['algorithm:'+name]={'source_sha256':algorithm_versions.fingerprint(name)}
    return artifacts


def install_artifacts(db,context):
    """Explicit worker preparation after the code/config release is approved; never on GET."""
    authorize(context)
    for key,payload in runtime_artifacts().items():
        sha=digest(payload)
        db.execute(insert(InstalledArtifact).values(id=str(uuid.uuid4()),artifact_key=key,
                   sha256=sha,payload_json=canonical(payload),installed_at=clock(db))
                   .on_conflict_do_nothing(index_elements=['artifact_key','sha256']))
    db.flush()


def schedule(db,context,workspace_id,release_id,security_id,session_id):
    authorize(context)
    release=db.get(StrategyVersion,release_id);security=db.get(Security,security_id)
    listing=db.scalar(select(PrimaryListing).where(PrimaryListing.security_id==security_id))
    session=db.get(MarketSession,session_id)
    if not release or release.workspace_id!=workspace_id or not release.published or not security:
        raise NotFound('发布策略/证券不属于此工作区')
    data_mode.require_company(db,security.company_id,workspace_id)
    if not listing or not session or listing.calendar_ref!=session.calendar_ref:
        raise Conflict('未批准挂牌日历，不能猜测封存时点')
    policy=json.loads(listing.close_policy_json)
    if not policy.get('approved') or not policy.get('price_kinds') or not policy.get('evidence') or not json.loads(session.evidence_json):
        raise Conflict('日历或最终收盘政策缺少已批准依据')
    if not data_mode.fixture_mode():
        if not data_mode.real_evidence(db,policy['evidence'],workspace_id) or not data_mode.real_evidence(db,json.loads(session.evidence_json),workspace_id):
            raise Conflict('挂牌政策或日历来源无分析许可')
    if listing.currency!=security.currency:raise Conflict('挂牌币种与证券不一致')
    # Cutoff is derived server-side, never supplied by an HTTP request or retry.
    values={'id':str(uuid.uuid4()),'workspace_id':workspace_id,'release_id':release_id,'security_id':security_id,
            'listing_id':listing.id,'market_session':session.market_session,'mode':'live',
            'evaluation_as_of':session.final_market_at,'knowledge_cutoff':session.final_market_at+timedelta(minutes=60),
            'finalization_token':str(uuid.uuid4())}
    db.execute(insert(EvaluationSeal).values(**values).on_conflict_do_nothing(
        index_elements=['workspace_id','release_id','security_id','market_session','mode']))
    return db.scalar(select(EvaluationSeal).where(EvaluationSeal.workspace_id==workspace_id,
        EvaluationSeal.release_id==release_id,EvaluationSeal.security_id==security_id,
        EvaluationSeal.market_session==session.market_session,EvaluationSeal.mode=='live'))


def claim(db,context,seal_id,lease_seconds=120):
    authorize(context)
    row=db.scalar(select(EvaluationSeal).where(EvaluationSeal.id==seal_id).with_for_update().execution_options(populate_existing=True))
    if not row:raise NotFound('没有此封存任务')
    now=clock(db)
    if row.state=='sealed':return {'seal_id':row.id,'state':'sealed','evaluation_id':row.evaluation_id}
    if row.state=='blocked_safety':return {'seal_id':row.id,'state':'blocked_safety'}
    if now<row.knowledge_cutoff:
        row.state='provisional'
        return {'seal_id':row.id,'state':'provisional','knowledge_cutoff':min(now,row.knowledge_cutoff).isoformat(),
                'planned_seal_cutoff':row.knowledge_cutoff.isoformat()}
    if row.lease_until and row.lease_until>now:return None
    row.fence+=1;row.lease_owner=context.owner;row.lease_until=now+timedelta(seconds=lease_seconds)
    row.state='ready_to_seal'
    db.flush()
    return {'seal_id':row.id,'owner':context.owner,'fence':row.fence,'generation':row.generation}


def leased(db,context,token):
    authorize(context)
    row=db.scalar(select(EvaluationSeal).where(EvaluationSeal.id==token['seal_id']).with_for_update().execution_options(populate_existing=True))
    if not row or row.fence!=token.get('fence') or row.lease_owner!=context.owner or token.get('owner')!=context.owner:
        raise Conflict('封存worker租约fence已失效')
    if row.lease_until is None or row.lease_until<=clock(db):raise Conflict('封存worker租约已到期')
    return row


def _knowledge(db,cutoff):
    entries=db.scalars(select(KnowledgeEntry).where(KnowledgeEntry.recorded_at<=cutoff)
        .order_by(KnowledgeEntry.sequence)).all()
    latest={(e.entity_type,e.entity_id):e for e in entries}
    return {k:e for k,e in latest.items() if e.operation!='DELETE'}, max((e.sequence for e in entries),default=0)


def freeze(db,context,token):
    # Caller must establish a fresh REPEATABLE READ transaction before any statement.
    if db.connection().exec_driver_sql('SHOW transaction_isolation').scalar()!='repeatable read':
        raise Conflict('冻结必须使用PG一致性snapshot事务')
    seal=leased(db,context,token)
    if clock(db)<seal.knowledge_cutoff:raise Conflict('尚未到固定封存截止')
    if seal.manifest_id:return db.get(FrozenManifest,seal.manifest_id)
    if seal.generation!=token['generation']:raise Conflict('冻结generation已变化')
    knowledge,watermark=_knowledge(db,seal.knowledge_cutoff)
    security=db.get(Security,seal.security_id);company=db.get(Company,security.company_id)
    listing=db.get(PrimaryListing,seal.listing_id)
    session=db.scalar(select(MarketSession).where(MarketSession.calendar_ref==listing.calendar_ref,
                        MarketSession.market_session==seal.market_session))
    release=db.get(StrategyVersion,seal.release_id)
    groups={k:{'quality':'missing','inputs':[],'reason_codes':['missing_'+k]} for k in GROUPS}
    def add(group,kind,id,sha=None):
        entry=knowledge.get((kind,id))
        if not entry:return False
        if group=='rights' and not data_mode.fixture_mode():
            past=json.loads(json.loads(entry.snapshot_json)['policy_json'])
            current=json.loads(db.get(SourceRegistry,id).policy_json)
            if past!=current:raise Conflict('来源政策在cutoff后改变，不能把新许可回填旧manifest')
        ref={'revision_id':id,'sha256':sha or entry.sha256,'known_at':entry.recorded_at.isoformat()}
        if ref not in groups[group]['inputs']:groups[group]['inputs'].append(ref)
        groups[group].update(quality='valid',reason_codes=[])
        return True
    for kind,id in [('company',company.id),('security',security.id),('primary_listing',listing.id),('strategy_version',release.id)]:
        if not add('identity',kind,id):raise Conflict('身份或发布版本在固定cutoff前尚未可知')
        entry=knowledge[(kind,id)]
        snap=json.loads(entry.snapshot_json)
        # Mutable identity cannot silently substitute post-cutoff values.
        if kind=='company' and snap['industry_key']!=company.industry_key:raise Conflict('公司行业已改变，需固定合法身份版本')
        if kind=='security' and any(snap[k]!=getattr(security,k) for k in ('ticker','market','currency','company_id')):raise Conflict('证券身份已改变')
    if not add('calendar','market_session',session.id):raise Conflict('批准日历在cutoff前未知')
    for key in CONFIGS+tuple('algorithm:'+name for name in ALGORITHMS):
        expected=runtime_artifacts()[key]
        artifact=db.scalar(select(InstalledArtifact).where(InstalledArtifact.artifact_key==key,InstalledArtifact.sha256==digest(expected)))
        if not artifact or not add('algorithms' if key.startswith('algorithm:') else 'decision_policies','installed_artifact',artifact.id,artifact.sha256):
            raise Conflict('算法/政策版本未在cutoff前发布，不能回填')
    selected=[]
    # Same recorded time with different values for one logical input is conflicting.
    all_rows=db.scalars(select(ResearchInput).where(ResearchInput.company_id==company.id,
        ResearchInput.workspace_id==seal.workspace_id,
        *input_time_bounds(seal.evaluation_as_of,seal.knowledge_cutoff))).all()
    # Filter by the DB ledger before choosing the latest logical input.
    candidates=[r for r in all_rows if ('research_input',r.id) in knowledge]
    candidates.sort(key=lambda r:knowledge[('research_input',r.id)].sequence)
    latest={}
    for row in candidates:
        payload=json.loads(row.payload_json)
        if not data_mode.fixture_mode() and (row.synthetic or row.content_hash!=digest(payload) or
            not data_mode.real_evidence(db,payload.get('evidence'),seal.workspace_id,company.id,seal.knowledge_cutoff)):continue
        latest[row.input_key]=row
    selected=list(latest.values())
    conflicts=set()
    for chosen in selected:
        for other in all_rows:
            a=knowledge.get(('research_input',chosen.id));b=knowledge.get(('research_input',other.id))
            if a and b and other.input_key==chosen.input_key and a.recorded_at==b.recorded_at and other.content_hash!=chosen.content_hash:conflicts.add(chosen.input_key)
    selected=[r for r in selected if r.input_key not in conflicts]
    price_policy=json.loads(listing.close_policy_json)
    usable=[]
    for row in selected:
        payload=json.loads(row.payload_json)
        if row.kind=='price' and row.input_key=='price:'+security.ticker:
            valid=(payload.get('session')==seal.market_session and payload.get('is_final') is True
                   and payload.get('price_kind') in price_policy['price_kinds']
                   and payload.get('currency')==security.currency)
            if not valid:continue
        if not data_mode.fixture_mode():
            refs=payload.get('evidence',[])
            if any(('item_revision',r.get('source_revision_id')) not in knowledge for r in refs):continue
            eligible=True
            for ref in refs:
                source_item=__import__('app.models.runtime',fromlist=['ItemRevision']).ItemRevision
                revision=db.get(source_item,ref['source_revision_id'])
                links=[json.loads(e.snapshot_json) for (kind,id),e in knowledge.items() if kind=='item_company_link']
                if not any(l['item_id']==revision.item_id and l['company_id']==company.id and l['status']=='accepted' for l in links):eligible=False
            if not eligible:continue
        usable.append(row)
    selected=usable
    decisions=[(s,r,v) for s,r,v in current_decisions(db,company.id,seal.workspace_id,seal.evaluation_as_of,seal.knowledge_cutoff,
                   revision_ids={id for (kind,id) in knowledge if kind=='judgment_revision'})
               if ('judgment_revision',r.id) in knowledge]
    if not data_mode.fixture_mode():
        accepted_links=[json.loads(e.snapshot_json) for (kind,id),e in knowledge.items() if kind=='item_company_link']
        def eligible_decision(entry):
            from app.models.runtime import ItemRevision
            refs=json.loads(entry[1].evidence_json)
            for ref in refs:
                id=ref.get('source_revision_id')
                if ('item_revision',id) not in knowledge:return False
                revision=db.get(ItemRevision,id)
                if not any(l['item_id']==revision.item_id and l['company_id']==company.id and l['status']=='accepted' for l in accepted_links):return False
            return bool(refs)
        decisions=[entry for entry in decisions if eligible_decision(entry)]
    template=resolve_template(company,db,seal.workspace_id,seal.knowledge_cutoff)
    # A frozen resolution is stored verbatim; no future template/code lookups on retry.
    for (kind,id),e in knowledge.items():
        snap=json.loads(e.snapshot_json)
        if kind=='template_release' and id==template.get('release_id'):add('templates',kind,id)
        if kind=='item_company_link' and snap['company_id']==company.id and snap['status']=='accepted':add('links',kind,id)
    if not groups['templates']['inputs']:
        for artifact in db.scalars(select(InstalledArtifact).where(InstalledArtifact.artifact_key=='templates-standard-v1.json')):
            if artifact.sha256==digest(config('templates-standard-v1.json')):add('templates','installed_artifact',artifact.id,artifact.sha256)
    calendar_evidence=json.loads(session.evidence_json)+json.loads(listing.close_policy_json)['evidence']
    for ref in calendar_evidence:
        from app.models.runtime import ItemRevision
        from app.models.intake import InformationItem
        revision=db.get(ItemRevision,ref.get('source_revision_id',''))
        if revision:
            if ('item_revision',revision.id) not in knowledge:raise Conflict('日历或收盘政策依据在cutoff前不可知')
            item=db.get(InformationItem,revision.item_id);add('rights','source_registry',item.source_id)
    for row in selected:
        if row.kind=='price' and row.input_key=='price:'+security.ticker:
            add('price','research_input',row.id,row.content_hash)
            if json.loads(row.payload_json).get('fx_per_cny'):add('fx','research_input',row.id,row.content_hash)
            elif security.currency=='HKD':
                from app.services.ecb_fx import matching_fx
                fx_row,_=matching_fx(selected,json.loads(row.payload_json).get('session'))
                if fx_row:add('fx','research_input',fx_row.id,fx_row.content_hash)
        elif row.kind=='financials':
            for group in ('financials','share_capital','report_obligations'):add(group,'research_input',row.id,row.content_hash)
        elif row.kind=='share_capital':add('share_capital','research_input',row.id,row.content_hash)
        for ref in json.loads(row.payload_json).get('evidence',[]) if isinstance(json.loads(row.payload_json).get('evidence'),list) else []:
            from app.models.runtime import ItemRevision
            from app.models.intake import InformationItem
            revision=db.get(ItemRevision,ref.get('source_revision_id',''))
            if revision:
                item=db.get(InformationItem,revision.item_id);add('rights','source_registry',item.source_id)
    for slot,revision,value in decisions:
        if slot.kind in ('impact','rubric','risk'):add({'impact':'impacts','rubric':'rubrics','risk':'risks'}[slot.kind],'judgment_revision',revision.id,digest({'value':value,'evidence':json.loads(revision.evidence_json)}))
        if revision.author_type=='human':add('human_overrides','judgment_revision',revision.id,digest(value))
        for ref in json.loads(revision.evidence_json):
            from app.models.runtime import ItemRevision
            from app.models.intake import InformationItem
            evidence_revision=db.get(ItemRevision,ref.get('source_revision_id',''))
            if evidence_revision:
                item=db.get(InformationItem,evidence_revision.item_id);add('rights','source_registry',item.source_id)
    if security.currency=='CNY':groups['fx']={'quality':'not_applicable','inputs':[],'reason_codes':['valuation_currency_is_cny']}
    for group in ('impacts','risks','human_overrides'):
        if not groups[group]['inputs']:groups[group]={'quality':'not_applicable','inputs':[],'reason_codes':['no_effective_'+group]}
    if data_mode.fixture_mode():groups['rights']={'quality':'not_applicable','inputs':[],'reason_codes':['original_disposable_fixture']}
    if conflicts:
        for key in conflicts:
            group='price' if key.startswith('price:') else 'fx' if key.startswith('fx:') else 'share_capital' if key.startswith('share_capital:') else 'financials'
            groups[group]={'quality':'conflicting','inputs':[],'reason_codes':['same_knowledge_time_conflict']}
    quality=score_company(db,company,seal.workspace_id,seal.evaluation_as_of,seal.knowledge_cutoff,template,input_rows=selected,decision_rows=decisions)
    valuation=score_security(db,security,seal.workspace_id,seal.evaluation_as_of,seal.knowledge_cutoff,seal.market_session,input_rows=selected)
    rules=json.loads(release.rules_json)
    result=gates(rules,quality,valuation)
    # Externally-derived classifications must be explicit gaps; no empty-input success.
    missing=[k for k,v in groups.items() if v['quality'] in ('missing','conflicting') and k not in ('links','rubrics')]
    if missing and result['status'] not in ('risk_excluded','suspended','not_applicable'):
        result.update(passes=None,status='pending_evidence',gaps=result['gaps']+['冻结输入缺口：'+k for k in missing])
    frozen_at=clock(db);id=str(uuid.uuid4());generation=seal.generation+1
    manifest={'schema_version':'1.0','manifest_id':id,'release_id':release.id,'security_id':security.id,
              'primary_listing_id':listing.id,'market_session':seal.market_session,
              'evaluation_as_of':seal.evaluation_as_of.isoformat(),'knowledge_cutoff':seal.knowledge_cutoff.isoformat(),
              'frozen_at':frozen_at.isoformat(),'selection_algorithm_ref':'database-knowledge-selection-v1',
              'cutoff_knowledge_sequence':watermark,'inputs':groups}
    snapshot={'quality':quality,'valuation':valuation,'result':result,'retain_result':gates(rules,quality,valuation,retain=True),
              'rules':rules,'calendar':{'ordinal':session.ordinal,'previous_session':session.previous_session},
              'source_policies':{ref['revision_id']:json.loads(db.get(SourceRegistry,ref['revision_id']).policy_json) for ref in groups['rights']['inputs']},
              'template_hash':template['config_hash'],
              'source_evidence':calendar_evidence+[ref for row in selected for ref in json.loads(row.payload_json).get('evidence',[])]+[ref for slot,rev,value in decisions for ref in json.loads(rev.evidence_json)],
              'identity':{'ticker':security.ticker,'market':security.market,'currency':security.currency,'company_id':company.id}}
    row=FrozenManifest(id=id,seal_id=seal.id,generation=generation,manifest_json=canonical(manifest),manifest_hash=digest(manifest),
        snapshot_json=canonical(snapshot),snapshot_hash=digest(snapshot),safety_generation=db.get(SafetyGeneration,'safety').generation,frozen_at=frozen_at)
    db.add(row);db.flush();seal.manifest_id=id;seal.generation=generation
    record(db,seal.workspace_id,None,'strategy.inputs_frozen','evaluation_seal',seal.id,{'manifest_id':id,'hash':row.manifest_hash,'cutoff':seal.knowledge_cutoff.isoformat()})
    return row


def finish(db,context,token,manifest_id,manifest_hash):
    authorize(context)
    existing=db.get(EvaluationSeal,token['seal_id'])
    if existing and existing.state=='sealed' and existing.fence==token.get('fence') and existing.lease_owner==context.owner and token.get('owner')==context.owner:
        prior=db.get(FrozenManifest,existing.manifest_id)
        if prior.id==manifest_id and prior.manifest_hash==manifest_hash:return db.get(Evaluation,existing.evaluation_id)
        raise Conflict('封存已完成，manifest不能替换')
    seal=leased(db,context,token)
    frozen=db.get(FrozenManifest,manifest_id)
    if not frozen or seal.manifest_id!=manifest_id or frozen.manifest_hash!=manifest_hash or frozen.generation!=seal.generation:
        raise Conflict('manifest身份/hash/generation不匹配')
    manifest=json.loads(frozen.manifest_json);snapshot=json.loads(frozen.snapshot_json)
    if digest(manifest)!=frozen.manifest_hash or digest(snapshot)!=frozen.snapshot_hash:raise Conflict('冻结内容完整性不通过')
    if clock(db)<seal.knowledge_cutoff:raise Conflict('不能提前封存')
    guard=db.scalar(select(SafetyGeneration).where(SafetyGeneration.key=='safety').with_for_update().execution_options(populate_existing=True))
    # Serialize with all safety mutations, then check current permissions/identity/
    # binding and hard risks independently from historical frozen inputs.
    security=db.get(Security,seal.security_id);company=db.get(Company,security.company_id)
    identity={'ticker':security.ticker,'market':security.market,'currency':security.currency,'company_id':company.id}
    current_template=resolve_template(company,db,seal.workspace_id)
    frozen_artifacts={r['sha256'] for group in ('algorithms','decision_policies') for r in manifest['inputs'][group]['inputs']}
    runtime_changed=any(digest(payload) not in frozen_artifacts for payload in runtime_artifacts().values())
    revoked=any(not db.get(SourceRegistry,id) or json.loads(db.get(SourceRegistry,id).policy_json)!=policy
                for id,policy in snapshot['source_policies'].items())
    if runtime_changed or revoked or identity!=snapshot['identity'] or current_template['config_hash']!=snapshot['template_hash']:
        seal.state='blocked_safety';seal.lease_until=None
        record(db,seal.workspace_id,None,'strategy.freeze_invalidated','evaluation_seal',seal.id,
               {'manifest_id':frozen.id,'reason':'runtime_rights_identity_or_template_changed'})
        return None
    # Accepted links may be revoked after the freeze; do not apply old evidence.
    for ref in manifest['inputs']['links']['inputs']:
        from app.models.company import ItemCompanyLink
        link=db.get(ItemCompanyLink,ref['revision_id'])
        if not link or link.status!='accepted':
            seal.state='blocked_safety';seal.lease_until=None
            record(db,seal.workspace_id,None,'strategy.freeze_invalidated','evaluation_seal',seal.id,
                   {'manifest_id':frozen.id,'reason':'evidence_link_revoked'})
            return None
    now=clock(db)
    live_decisions=current_decisions(db,company.id,seal.workspace_id,now,now)
    live_risk_entries=[(slot,r,v) for slot,r,v in live_decisions if slot.kind=='risk' and v.get('confirmed') is True]
    live_risks=[{**v,'revision_id':r.id} for slot,r,v in live_risk_entries]
    live_risk_evidence=[ref for slot,r,v in live_risk_entries for ref in json.loads(r.evidence_json)]
    release=db.get(StrategyVersion,seal.release_id)
    current=db.scalar(select(StrategyVersion).where(StrategyVersion.workspace_id==seal.workspace_id,StrategyVersion.published.is_(True)).order_by(StrategyVersion.version.desc()).limit(1))
    db.execute(insert(SecurityState).values(id=str(uuid.uuid4()),security_id=seal.security_id,strategy_id=seal.release_id,
        status='OUT',pending_count=0,last_confirmed=None,last_ordinal=-1,generation=0).on_conflict_do_nothing(index_elements=['security_id','strategy_id']))
    state=db.scalar(select(SecurityState).where(SecurityState.security_id==seal.security_id,SecurityState.strategy_id==seal.release_id).with_for_update().execution_options(populate_existing=True))
    result=snapshot['retain_result'] if state.last_confirmed=='IN' else snapshot['result']
    calendar=snapshot['calendar'];rules=snapshot['rules']
    risk_gate=gates(rules,{'hard_risks':live_risks},{'security_id':security.id})
    if risk_gate['status']=='risk_excluded':result=risk_gate
    changes=[];application='superseded'
    if current and current.id==release.id:
        ev=Eval(seal.market_session, result['passes'] is not None,bool(result['passes']),
                hard_risk=result['status']=='risk_excluded',ordinal=calendar['ordinal'],previous_session=calendar['previous_session'],
                final=True,suspended=result['status']=='suspended')
        changes,application=apply_session(state,ev,rules['state_policy']['enter_distinct_sessions'],rules['state_policy']['exit_distinct_sessions'])
        if application=='applied':state.generation+=1
    now=clock(db)
    evaluation=Evaluation(workspace_id=seal.workspace_id,strategy_id=release.id,security_id=seal.security_id,
        session=seal.market_session,manifest_json=frozen.manifest_json,manifest_hash=frozen.manifest_hash,
        result_json=canonical({'quality':snapshot['quality'],'valuation':snapshot['valuation'],'rules':result,
                               'current_risk_gate_refs':[r['revision_id'] for r in live_risks],
                               'current_risk_evidence':live_risk_evidence,
                               'sealed_at':now.isoformat(),'state':'sealed','validity':'UNKNOWN' if result['passes'] is None else 'VALID'}),
        token=seal.finalization_token,application_status=application,generated_at=now)
    db.add(evaluation);db.flush()
    for change in changes:
        row=ChangeRecord(workspace_id=seal.workspace_id,evaluation_id=evaluation.id,security_id=seal.security_id,
            strategy_id=release.id,session_label=seal.market_session,from_status=change['from'],to_status=change['to'],reason=change['reason'])
        db.add(row);db.flush();record(db,seal.workspace_id,None,'membership.changed','change_record',row.id,{'evaluation_id':evaluation.id,**change})
    seal.state='sealed';seal.evaluation_id=evaluation.id;seal.lease_until=None
    record(db,seal.workspace_id,None,'strategy.sealed','evaluation',evaluation.id,{'token':evaluation.token,'manifest_id':frozen.id,'application_status':application})
    return evaluation
