from app.core.errors import DomainError
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Any, Literal
from sqlalchemy import select
from app.api.deps import Principal, require
from app.db import get_db
from app.models.runtime import ResearchRun
from app.domains.companies.research_pipeline import start_run, readable_run, response
router=APIRouter(prefix='/api/research',tags=['公司档案'])

class RunSummary(BaseModel):
    id: str
    status: Literal['partial','completed']
    manifest_hash: str
    created_at: str

class RunDetail(RunSummary):
    manifest: dict[str,Any]
    result: dict[str,Any]

@router.post('/runs',response_model=RunDetail)
def run(principal:Principal=Depends(require('analysis.override')),db=Depends(get_db),command_key:str=Header(alias='Idempotency-Key',min_length=8,max_length=240)):
    row=start_run(db,principal,command_key);db.commit();db.refresh(row)
    return response(row)

@router.get('/runs',response_model=list[RunSummary])
def list_runs(principal:Principal=Depends(require('research.read')),db=Depends(get_db)):
    rows=db.scalars(select(ResearchRun).where(ResearchRun.workspace_id==principal.workspace.id).order_by(ResearchRun.created_at.desc()).limit(30)).all()
    out=[]
    for row in rows:
        try:readable_run(db,row,principal.workspace.id)
        except DomainError:continue
        out.append({'id':row.id,'status':row.status,'manifest_hash':row.manifest_hash,'created_at':row.created_at.isoformat()})
    return out

@router.get('/runs/{run_id}',response_model=RunDetail)
def read(run_id:str,principal:Principal=Depends(require('research.read')),db=Depends(get_db)):
    return response(readable_run(db,db.get(ResearchRun,run_id),principal.workspace.id))
