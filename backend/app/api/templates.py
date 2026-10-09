import json
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from app.api.deps import Principal,require
from app.db import get_db
from app.domains.platform import data_mode
from app.models.company import Company
from app.models.runtime import TemplateRelease
from app.domains.companies.scoring_service import resolve_template,apply_patches
from app.domains.platform.transactions import record,canonical,digest

router=APIRouter(prefix='/api/templates',tags=['templates'])


class TemplateIn(BaseModel):
    expected_version: int | None = None
    patches: list[dict]


def company(db,id):
    row=db.get(Company,id)
    if row is None: raise HTTPException(404,'没有该公司')
    return row


@router.get('/{company_id}')
def read(company_id:str,principal:Principal=Depends(require('research.read')),db=Depends(get_db)):
    row=data_mode.require_company(db,company_id,principal.workspace.id)
    release=db.scalar(select(TemplateRelease).where(TemplateRelease.company_id==row.id,TemplateRelease.workspace_id==principal.workspace.id)
                      .order_by(TemplateRelease.version.desc()).limit(1))
    return {'version':release.version if release else None,'resolved':resolve_template(row,db,principal.workspace.id)}


@router.post('/{company_id}/preview')
def preview(company_id:str,body:TemplateIn,principal:Principal=Depends(require('template.edit')),db=Depends(get_db)):
    try:
        resolved=apply_patches(resolve_template(data_mode.require_company(db,company_id,principal.workspace.id),db,principal.workspace.id),body.patches,'draft')
    except (ValueError,KeyError,TypeError,ArithmeticError): raise HTTPException(422,'模板字段、维度或权重不合法')
    return {'resolved':resolved,'preview_hash':digest(resolved)}


@router.post('/{company_id}/publish')
def publish(company_id:str,body:TemplateIn,principal:Principal=Depends(require('template.publish')),db=Depends(get_db)):
    data_mode.require_company(db,company_id,principal.workspace.id)
    row=db.scalar(select(Company).where(Company.id==company_id).with_for_update())
    if row is None: raise HTTPException(404,'没有该公司')
    prior=db.scalar(select(TemplateRelease).where(TemplateRelease.company_id==row.id,TemplateRelease.workspace_id==principal.workspace.id)
                    .order_by(TemplateRelease.version.desc()).limit(1))
    if (prior.version if prior else None)!=body.expected_version: raise HTTPException(409,'模板版本已变化，请重新预览')
    try: resolved=apply_patches(resolve_template(row,db,principal.workspace.id),body.patches,'company-published')
    except (ValueError,KeyError,TypeError,ArithmeticError): raise HTTPException(422,'模板字段、维度或权重不合法')
    resolved.pop('release_id',None);resolved.pop('config_hash',None)
    release=TemplateRelease(workspace_id=principal.workspace.id,company_id=row.id,version=prior.version+1 if prior else 1,
                           config_json=canonical(resolved),config_hash=digest(resolved))
    db.add(release);db.flush()
    record(db,principal.workspace.id,principal.user.id,'template.published','template_release',release.id,{'hash':release.config_hash})
    db.commit()
    return {'id':release.id,'version':release.version,'resolved':resolved,'hash':release.config_hash}
