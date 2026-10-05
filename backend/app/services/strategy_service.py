import json
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.models.strategy import SecurityState, ChangeRecord
from app.models.runtime import Evaluation
from app.services.transactions import canonical, digest, record
from app.services.state_machine import apply_session


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
    passed=None if any(r['result'] is None for r in results) else all(r['result'] for r in results)
    return {'passes':passed,'conditions':results}


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
