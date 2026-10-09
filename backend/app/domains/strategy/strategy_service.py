import json
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.models.strategy import SecurityState, ChangeRecord
from app.models.runtime import Evaluation
from app.domains.platform.transactions import canonical, digest, record
from app.domains.strategy.state_machine import apply_session


def gates(rules, company, security, retain=False):
    fields={'company.quality_score':company.get('quality_exact'),'company.coverage':company.get('coverage_exact'),
            'security.valuation_score':security.get('valuation_exact')}
    fields.update({'metrics.'+k:v for k,v in company.get('metrics',{}).items()})
    results=[]
    for gate in rules['retain' if retain else 'enter']['all']:
        value=fields.get(gate['field']);expected=Decimal(gate['value'])
        actual=Decimal(value) if value is not None else None
        result=None if actual is None else (actual>=expected if gate['op']=='gte' else actual<=expected)
        results.append({'field':gate['field'],'actual':str(actual) if actual is not None else None,
                        'expected':str(expected),'op':gate['op'],'result':result})
    policy=rules['quality_gates']
    risks=[r for r in company.get('hard_risks',[]) if r.get('risk_code') in rules['hard_risk_policy']['risk_codes']
           and (r.get('target_kind')=='company' or r.get('target_id')==security.get('security_id'))]
    if risks: return {'passes':False,'status':'risk_excluded','conditions':results,'gaps':[], 'risks':risks}
    if security.get('suspended'): return {'passes':None,'status':'suspended','conditions':results,'gaps':['证券暂停评估']}
    universe=rules['universe']
    if (security.get('market') is not None and security['market'] not in universe['markets']) or company.get('industry_key') in universe['exclude_sector_groups']:
        return {'passes':False,'status':'not_applicable','conditions':results,'gaps':['不属于当前策略适用范围']}
    gaps=[]
    if rules.get('scoring_binding_manifest'):
        bound=next((b for b in rules['scoring_binding_manifest'] if b.get('company_id')==company.get('company_id')),None)
        if not bound or bound.get('template_hash')!=company.get('template',{}).get('config_hash'):
            gaps.append('当前模板与策略发布绑定不同，需重新模拟并发布')
    if universe['common_equity_only'] and not security.get('common_equity'): gaps.append('普通股权利范围未确认')
    if company.get('coverage_exact') is None or Decimal(company['coverage_exact'])<Decimal(policy['minimum_coverage']): gaps.append('经营依据覆盖不足')
    for dimension in policy['required_dimensions']:
        d=company.get('dimensions',{}).get(dimension,{})
        if d.get('score') is None: gaps.append('必需维度缺少有效依据：'+dimension)
    for d,dimension in company.get('dimensions',{}).items():
        age=dimension.get('baseline_age_days')
        if age is not None and age>=policy['baseline_max_age_days']: gaps.append('经营判断超过策略允许龄期：'+d)
    if not company.get('financial_valid'): gaps.append('财务期间或报告义务未满足')
    if policy['only_approved_inputs'] and not security.get('approved_inputs'): gaps.append('缺少批准使用的输入')
    if not security.get('price_final') or security.get('price_lag_sessions') is None or security['price_lag_sessions']>policy['price_max_lag_sessions']:
        gaps.append('正式收盘价或对应交易日未核验')
    if policy['currency_and_share_basis_required'] and security.get('valuation_exact') is None: gaps.append('币种、股本或财务估值口径未满足')
    # Quality gates precede numeric AND: insufficient required data remains UNKNOWN.
    passed=None if gaps else False if any(r['result'] is False for r in results) else None if any(r['result'] is None for r in results) else True
    return {'passes':passed,'status':'pending_evidence' if gaps else 'match' if passed else 'no_match' if passed is False else 'pending_evidence',
            'conditions':results,'gaps':gaps}



def apply_evaluation(db, strategy, security, workspace_id, ev, manifest, result, actor_id=None):
    if not ev.final:
        from types import SimpleNamespace
        state = db.scalar(select(SecurityState).where(SecurityState.security_id == security.id,
                          SecurityState.strategy_id == strategy.id))
        state = state or SimpleNamespace(status='OUT', pending_count=0, last_confirmed='OUT')
        return SimpleNamespace(id=None, token=None, application_status='provisional'), [], state
    # Concurrent creation and application use the same unique key plus row lock.
    db.execute(insert(SecurityState).values(security_id=security.id,strategy_id=strategy.id,
        status='OUT',pending_count=0,last_confirmed=None,last_ordinal=-1,generation=0)
        .on_conflict_do_nothing(index_elements=['security_id','strategy_id']))
    state=db.scalar(select(SecurityState).where(SecurityState.security_id==security.id,
          SecurityState.strategy_id==strategy.id).with_for_update().execution_options(populate_existing=True))
    prior=db.scalar(select(Evaluation).where(Evaluation.workspace_id==workspace_id,Evaluation.strategy_id==strategy.id,
               Evaluation.security_id==security.id,Evaluation.session==ev.session))
    if prior: return prior, [], state
    changes,application=apply_session(state,ev)
    evaluation=Evaluation(workspace_id=workspace_id,strategy_id=strategy.id,security_id=security.id,
        session=ev.session,manifest_json=canonical(manifest),manifest_hash=digest(manifest),
        result_json=canonical(result),application_status=application)
    db.add(evaluation);db.flush()
    if application=='applied': state.generation+=1
    for change in changes:
        rec=ChangeRecord(workspace_id=workspace_id,evaluation_id=evaluation.id,security_id=security.id,
            strategy_id=strategy.id,session_label=ev.session,from_status=change['from'],to_status=change['to'],reason=change['reason'])
        db.add(rec);db.flush()
        record(db,workspace_id,actor_id,'strategy.transition','change_record',rec.id,
               {'evaluation_id':evaluation.id,'manifest_hash':evaluation.manifest_hash,**change})
    record(db,workspace_id,actor_id,'strategy.evaluated','evaluation',evaluation.id,{'application':application})
    return evaluation,changes,state
