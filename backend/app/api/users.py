"""后台设置 › 账号与角色，以及审计日志。

账号属于工作区：管理员只能看到、修改本工作区的成员。角色是固定的五种（config/roles-standard-v1.json）。
"""
import json

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import Principal, require, require_any
from app.core.paging import PageParams, page, page_params
from app.core.uow import unit_of_work
from app.db import get_db
from app.domains.identity import users
from app.domains.identity.permissions import catalog
from app.models.audit import AuditLog
from app.models.identity import User

router = APIRouter(prefix='/api/admin', tags=['账号与角色'])

MANAGE = ('user.manage', 'role.assign')


class UserCreate(BaseModel):
    login: str = Field(min_length=3, max_length=120, pattern=r'^[^\s]+$', description='登录名，一般用邮箱')
    display_name: str = Field(min_length=1, max_length=120)
    roles: list[str] = Field(min_length=1)
    password: str | None = Field(None, max_length=256, description='留空则生成一次性初始密码')


class UserPatch(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=120)
    disabled: bool | None = None


class RolesIn(BaseModel):
    roles: list[str] = Field(min_length=1)


class PasswordReset(BaseModel):
    password: str | None = Field(None, max_length=256, description='留空则生成一次性密码')


@router.get('/roles')
def roles(principal: Principal = Depends(require_any(*MANAGE))):
    return catalog()


@router.get('/users')
def list_users(q: str | None = Query(None, max_length=120), paging: PageParams = Depends(page_params),
               principal: Principal = Depends(require_any(*MANAGE)), db=Depends(get_db)):
    items, total = users.list_users(db, principal.workspace.id, q=q, limit=paging.limit, offset=paging.offset)
    return page(items, total, paging)


@router.post('/users', status_code=201)
def create_user(body: UserCreate, principal: Principal = Depends(require('user.manage')), db=Depends(get_db)):
    with unit_of_work(db):
        generated = None
        password = body.password
        if not password:
            import secrets
            generated = password = secrets.token_urlsafe(12)
        out = users.create_user(db, principal.workspace.id, principal.user.id, login=body.login,
                                display_name=body.display_name, roles=body.roles, password=password)
    return {**out, 'initial_password': generated}


@router.get('/users/{user_id}')
def get_user(user_id: str, principal: Principal = Depends(require_any(*MANAGE)), db=Depends(get_db)):
    return users.view(db, users.member(db, principal.workspace.id, user_id), principal.workspace.id)


@router.patch('/users/{user_id}')
def update_user(user_id: str, body: UserPatch, principal: Principal = Depends(require('user.manage')), db=Depends(get_db)):
    with unit_of_work(db):
        return users.update_user(db, principal.workspace.id, principal.user.id, user_id,
                                 display_name=body.display_name, disabled=body.disabled)


@router.put('/users/{user_id}/roles')
def set_roles(user_id: str, body: RolesIn, principal: Principal = Depends(require('role.assign')), db=Depends(get_db)):
    with unit_of_work(db):
        return users.set_roles(db, principal.workspace.id, principal.user.id, user_id, body.roles)


@router.post('/users/{user_id}/password')
def reset_password(user_id: str, body: PasswordReset, principal: Principal = Depends(require('user.manage')), db=Depends(get_db)):
    with unit_of_work(db):
        generated = users.reset_password(db, principal.workspace.id, principal.user.id, user_id, body.password or None)
    return {'ok': True, 'initial_password': generated}


@router.post('/users/{user_id}/sign-out')
def sign_out(user_id: str, principal: Principal = Depends(require('user.manage')), db=Depends(get_db)):
    with unit_of_work(db):
        users.sign_out_everywhere(db, principal.workspace.id, principal.user.id, user_id)
    return {'ok': True}


# ------------------------------------------------------------------ 审计日志

@router.get('/audit')
def audit(action: str | None = Query(None, max_length=120, description='按动作前缀过滤，如 identity.'),
          actor: str | None = Query(None, max_length=120, description='操作人登录名'),
          paging: PageParams = Depends(page_params),
          principal: Principal = Depends(require('audit.read')), db=Depends(get_db)):
    q = select(AuditLog, User.login, User.display_name).outerjoin(User, User.id == AuditLog.actor_user_id) \
        .where(AuditLog.workspace_id == principal.workspace.id)
    if action:
        q = q.where(AuditLog.action.startswith(action))
    if actor:
        q = q.where(User.login == actor.strip().lower())
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.execute(q.order_by(AuditLog.created_at.desc(), AuditLog.id).limit(paging.limit).offset(paging.offset)).all()
    items = [{'id': a.id, 'at': a.created_at.isoformat() if a.created_at else None, 'action': a.action,
              'entity_type': a.entity_type, 'entity_id': a.entity_id,
              'actor': {'login': login, 'display_name': name} if login else None,
              'detail': json.loads(a.detail_json or '{}')} for a, login, name in rows]
    return page(items, total, paging)
