"""Read-only formal status. Scheduling/finality/sealing are internal-worker only."""
import json
from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter,Depends
from sqlalchemy import select,text
from app.api.deps import Principal,require
from app.db import get_db
from app.models.sealing import EvaluationSeal,FrozenManifest
from app.models.runtime import Evaluation
from app.models.company import Security
from app.models.strategy import SecurityState
from app.models.intake import SourceRegistry
from app.domains.platform import data_mode
from app.domains.platform.transactions import digest
router=APIRouter(prefix='/api/strategy',tags=['策略'])

class FormalRow(BaseModel):
    seal_id:str
    security_id:str
    ticker:str
    currency:str
    release_id:str
    market_session:str
    phase:str
    evaluation_as_of:datetime
    knowledge_cutoff:datetime
    generated_at:datetime|None=None
    evaluation_id:str|None=None
    manifest_hash:str|None=None
    validity:str|None=None
    application:str|None=None
    membership:str|None=None
    gaps:list[str]=[]

class FormalStatus(BaseModel):
    available:bool
    reason:str|None=None
    rows:list[FormalRow]


def readable(db,frozen,workspace_id):
    if not frozen:return False
    manifest=json.loads(frozen.manifest_json);snapshot=json.loads(frozen.snapshot_json)
    if frozen.manifest_hash!=digest(manifest) or frozen.snapshot_hash!=digest(snapshot):return False
    if data_mode.fixture_mode():return True
    if not snapshot.get('source_policies'):return False
    for id,policy in snapshot['source_policies'].items():
        source=db.get(SourceRegistry,id)
        if not source or json.loads(source.policy_json)!=policy or policy.get('revoked') or not policy.get('store') or not policy.get('analyze') or policy.get('analyze')=='disabled':return False
    return data_mode.real_evidence(db,snapshot.get('source_evidence',[]),workspace_id)


@router.get('/seals',response_model=FormalStatus)
def status(principal:Principal=Depends(require('research.read')),db=Depends(get_db)):
    if not db.execute(text("SELECT to_regclass('public.evaluation_seal')")).scalar():
        return {'available':False,'reason':'正式封存迁移尚未安装；研究预览仍可使用','rows':[]}
    visible={c.id for c in data_mode.companies(db,principal.workspace.id)};rows=[]
    for seal in db.scalars(select(EvaluationSeal).where(EvaluationSeal.workspace_id==principal.workspace.id)
                          .order_by(EvaluationSeal.knowledge_cutoff.desc()).limit(100)):
        security=db.get(Security,seal.security_id)
        if not security or security.company_id not in visible:continue
        ev=db.get(Evaluation,seal.evaluation_id) if seal.evaluation_id else None
        frozen=db.get(FrozenManifest,seal.manifest_id) if seal.manifest_id else None
        if ev and not readable(db,frozen,principal.workspace.id):continue
        result=json.loads(ev.result_json) if ev else {}
        if result.get('current_risk_evidence') and not data_mode.fixture_mode() and not data_mode.real_evidence(db,result['current_risk_evidence'],principal.workspace.id):continue
        state=db.scalar(select(SecurityState).where(SecurityState.security_id==security.id,SecurityState.strategy_id==seal.release_id)) if ev else None
        rows.append({'seal_id':seal.id,'security_id':security.id,'ticker':security.ticker,'currency':security.currency,
            'release_id':seal.release_id,'market_session':seal.market_session,'phase':seal.state,
            'evaluation_as_of':seal.evaluation_as_of,'knowledge_cutoff':seal.knowledge_cutoff,
            'generated_at':ev.generated_at if ev else None,'evaluation_id':ev.id if ev else None,
            'manifest_hash':ev.manifest_hash if ev else None,'validity':result.get('validity'),
            'application':ev.application_status if ev else None,
            'membership':state.status if state and ev.application_status=='applied' else None,
            'gaps':result.get('rules',{}).get('gaps',[])})
    return {'available':True,'rows':rows}
