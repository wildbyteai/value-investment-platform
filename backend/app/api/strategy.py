import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from app.api.deps import Principal, require
from app.db import get_db
from app.domains.platform import data_mode
from app.models.company import Company, Security
from app.models.strategy import ChangeRecord, SecurityState, StrategyVersion
from app.models.runtime import Evaluation, CommandReceipt
from app.domains.strategy.state_machine import GOLDEN
from app.domains.platform.transactions import record, canonical, digest
from app.domains.strategy.strategy_service import gates, apply_evaluation
from app.domains.companies.scoring_service import config, score_company, score_security

router=APIRouter(prefix='/api/strategy',tags=['strategy'])


def latest(db,ws):
    return db.scalar(select(StrategyVersion).where(StrategyVersion.workspace_id==ws,StrategyVersion.published.is_(True))
                     .order_by(StrategyVersion.version.desc()).limit(1))


def ensure_strategy(db,ws):
    strategy=latest(db,ws)
    if strategy is None:
        # Only invoked under strategy.publish authorization. No implicit publish on reads.
        rules=config('strategy-standard-v1.json')
        strategy=StrategyVersion(workspace_id=ws,strategy_key=rules['strategy_key'],version=1,
                                 name=rules['name'],rules_json=canonical(rules),published=True)
        db.add(strategy);db.flush()
    return strategy


@router.get('/current')
def current(principal: Principal=Depends(require('research.read')),db=Depends(get_db)):
    strategy=latest(db,principal.workspace.id)
    return {'id':strategy.id,'version':strategy.version,'rules':json.loads(strategy.rules_json)} if strategy else {'version':None,'rules':config('strategy-standard-v1.json'),'status':'尚未发布'}


class PublishIn(BaseModel):
    expected_version: int | None = None
    quality_threshold: str = '70'
    simulation_token: str | None = None


def changed_rules(body, prior=None):
    from decimal import Decimal, InvalidOperation
    try:
        value=Decimal(body.quality_threshold)
        if not value.is_finite() or not 0<=value<=100: raise ValueError()
    except (ValueError,InvalidOperation):
        raise HTTPException(422,'经营分门槛必须在0到100之间')
    rules=json.loads(prior.rules_json) if prior else config('strategy-standard-v1.json')
    rules.pop('scoring_binding_manifest',None) # draft binds current inputs rather than hot-changing an old release
    gate=next(g for g in rules['enter']['all'] if g['field']=='company.quality_score')
    gate['value']=str(value)
    return rules


def simulation_inputs(db,ws,rules,at):
    results=[];bindings=[]
    for company in data_mode.companies(db,ws):
        quality=score_company(db,company,ws,at,at)
        bindings.append({'company_id':company.id,'template_hash':quality['template']['config_hash'],
                         'industry_key':company.industry_key,'financial_valid':quality['financial_valid'],
                         'dimension_eligibility':{d:v['status'] for d,v in quality['dimensions'].items()},
                         'inputs':quality['input_refs'],'judgments':quality['judgment_refs']})
        for security in db.scalars(select(Security).where(Security.company_id==company.id).order_by(Security.id)).all():
            valuation=score_security(db,security,ws,at,at)
            bindings.append({'security_id':security.id,'ticker':security.ticker,'market':security.market,'currency':security.currency,
                             'valuation_eligible':valuation['valuation_score'] is not None,'suspended':valuation['suspended'],
                             'inputs':valuation['input_refs']})
            results.append({'company':company.name,'security_id':security.id,'ticker':security.ticker,
                **gates(rules,quality,valuation),'quality':quality['quality_score'],'valuation':valuation['valuation_score']})
    return results, bindings


@router.post('/simulate')
def simulate(body: PublishIn,principal: Principal=Depends(require('strategy.simulate')),db=Depends(get_db)):
    prior=latest(db,principal.workspace.id)
    version=prior.version if prior else None
    if body.expected_version is not None and body.expected_version!=version: raise HTTPException(409,'已发布版本已变化，请重新读取规则')
    rules=changed_rules(body,prior);at=datetime.now(timezone.utc)
    results,bindings=simulation_inputs(db,principal.workspace.id,rules,at)
    token=str(uuid.uuid4())
    snapshot={'actor':principal.user.id,'expected_version':version,'rules':rules,'bindings':bindings,'as_of':at.isoformat()}
    db.add(CommandReceipt(workspace_id=principal.workspace.id,command_key='strategy-simulation:'+token,
        request_hash=digest(snapshot),response_json=canonical(snapshot)))
    record(db,principal.workspace.id,principal.user.id,'strategy.simulated','strategy_simulation',token,{'input_hash':digest(bindings)})
    db.commit()
    return {'mode':'simulation','as_of':at.isoformat(),'results':results,'rules':rules,'simulation_token':token,
            'expected_version':version,'input_hash':digest(bindings)}


@router.post('/publish')
def publish(body: PublishIn,principal: Principal=Depends(require('strategy.publish')),db=Depends(get_db)):
    # Lock a workspace row even before its first release, so two publishers serialize.
    from app.models.identity import Workspace
    db.scalar(select(Workspace).where(Workspace.id==principal.workspace.id).with_for_update())
    prior=latest(db,principal.workspace.id)
    if (prior.version if prior else None)!=body.expected_version:
        raise HTTPException(409,'已发布版本已变化，请重新模拟')
    rules=changed_rules(body,prior)
    if not body.simulation_token: raise HTTPException(409,'请先模拟当前草稿，再发布所见结果')
    receipt=db.scalar(select(CommandReceipt).where(CommandReceipt.workspace_id==principal.workspace.id,
        CommandReceipt.command_key=='strategy-simulation:'+body.simulation_token))
    if not receipt: raise HTTPException(409,'模拟记录不可用，请重新模拟')
    snapshot=json.loads(receipt.response_json)
    _,bindings=simulation_inputs(db,principal.workspace.id,rules,datetime.now(timezone.utc))
    if snapshot['actor']!=principal.user.id or snapshot['expected_version']!=body.expected_version or snapshot['rules']!=rules or digest(snapshot['bindings'])!=digest(bindings):
        raise HTTPException(409,'规则或输入已变化，请重新模拟；草稿已保留')
    if (datetime.now(timezone.utc)-datetime.fromisoformat(snapshot['as_of'])).total_seconds()>1800:
        raise HTTPException(409,'模拟已超过30分钟，请重新模拟当前输入')
    rules['scoring_binding_manifest']=snapshot['bindings']
    version=StrategyVersion(workspace_id=principal.workspace.id,strategy_key=rules['strategy_key'],
          version=(prior.version+1 if prior else 1),name=rules['name'],rules_json=canonical(rules),published=True)
    db.add(version);db.flush()
    record(db,principal.workspace.id,principal.user.id,'strategy.published','strategy_version',version.id,{'version':version.version})
    db.commit()
    return {'id':version.id,'version':version.version,'rules':rules,'status':'新版本已发布，评估尚未生成'}


@router.post('/run-golden')
def run_golden(principal: Principal=Depends(require('strategy.publish')),db=Depends(get_db)):
    data_mode.require_fixture()
    strategy=ensure_strategy(db,principal.workspace.id)
    company=db.scalar(select(Company).where(Company.id=='00000000-0000-4000-8000-000000000001'))
    if company is None: raise HTTPException(409,'请先导入合成资料')
    security=db.scalar(select(Security).where(Security.company_id==company.id,Security.market=='HK'))
    transitions=[];history=[]
    for ev in GOLDEN:
        # Golden mode explicitly tests state application, never represents real analysis.
        evaluation,changes,state=apply_evaluation(db,strategy,security,principal.workspace.id,ev,
           {'mode':'synthetic_state_machine_golden','session':ev.session,'rules':json.loads(strategy.rules_json)},
           {'valid':ev.valid,'passes':ev.passes,'risk':ev.hard_risk},principal.user.id)
        transitions += [{'session':ev.session,**c} for c in changes]
        history.append({'session':ev.session,'status':state.status,'pending':state.pending_count,'last_confirmed':state.last_confirmed,
                        'application':evaluation.application_status})
    db.commit()
    return {'final_status':state.status,'transitions':transitions,'history':history,'mode':'synthetic_state_machine_golden'}


@router.get('/transitions')
def transitions(principal: Principal=Depends(require('research.read')),db=Depends(get_db)):
    rows=db.scalars(select(ChangeRecord).where(ChangeRecord.workspace_id==principal.workspace.id).order_by(ChangeRecord.created_at)).all()
    if not data_mode.fixture_mode():
        rows=[r for r in rows if (e:=db.get(Evaluation,r.evaluation_id)) and not json.loads(e.manifest_json).get('mode','').startswith('synthetic') and data_mode.real_evidence(db,json.loads(e.manifest_json).get('source_evidence'),principal.workspace.id)]
    return [{'id':r.id,'evaluation_id':r.evaluation_id,'session':r.session_label,'from':r.from_status,'to':r.to_status,
             'reason':r.reason,'delivery_count':r.delivery_count} for r in rows]


@router.get('/evaluations/{evaluation_id}')
def evaluation(evaluation_id:str,principal: Principal=Depends(require('research.read')),db=Depends(get_db)):
    row=db.get(Evaluation,evaluation_id)
    if row is None or row.workspace_id!=principal.workspace.id: raise HTTPException(404,'没有该评估')
    manifest=json.loads(row.manifest_json)
    if manifest.get('inputs'):
        from app.models.sealing import FrozenManifest
        from app.api.sealing import readable
        frozen=db.scalar(select(FrozenManifest).where(FrozenManifest.manifest_hash==row.manifest_hash))
        security=db.get(Security,row.security_id)
        if (json.loads(row.result_json).get('current_risk_evidence') and not data_mode.fixture_mode() and not data_mode.real_evidence(db,json.loads(row.result_json)['current_risk_evidence'],principal.workspace.id)) or not frozen or not readable(db,frozen,principal.workspace.id) or security.company_id not in {c.id for c in data_mode.companies(db,principal.workspace.id)}:raise HTTPException(404,'没有具备当前读取权限的封存结果')
    elif not data_mode.fixture_mode() and not data_mode.real_evidence(db,manifest.get('source_evidence'),principal.workspace.id):
        raise HTTPException(404,'没有具备真实来源证据的评估')
    return {'id':row.id,'token':row.token,'manifest':json.loads(row.manifest_json),'manifest_hash':row.manifest_hash,
            'result':json.loads(row.result_json),'application':row.application_status,'generated_at':row.generated_at.isoformat()}
