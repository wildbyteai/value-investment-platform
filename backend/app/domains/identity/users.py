"""Account administration inside one workspace: list, create, rename, disable, reset password, assign roles.

Used by the settings page (/api/admin/users) and the server shell (python -m app.admin_cli).
Every change is audited. Guards keep a workspace from locking itself out: nobody can disable
themselves or drop their own 系统管理员 role, and the last active 系统管理员 cannot be removed.
"""
from __future__ import annotations

import secrets

from sqlalchemy import delete, func, select

from app.core.errors import Conflict, Invalid, NotFound
from app.domains.identity import passwords, sessions
from app.domains.identity.permissions import VALID_ROLES, role_label
from app.domains.platform.transactions import record
from app.models.identity import AuthSession, Membership, User

ADMIN_ROLE = 'system_admin'


def normalize_login(login: str) -> str:
    return login.strip().lower()


def _roles(db, user_id: str, workspace_id: str) -> list[str]:
    return list(db.scalars(select(Membership.role).where(Membership.user_id == user_id, Membership.workspace_id == workspace_id)
                           .order_by(Membership.role)).all())


def view(db, user: User, workspace_id: str) -> dict:
    roles = _roles(db, user.id, workspace_id)
    last = db.scalar(select(func.max(AuthSession.last_seen_at)).where(AuthSession.user_id == user.id))
    active = db.scalar(select(func.count()).select_from(AuthSession).where(AuthSession.user_id == user.id))
    return {'id': user.id, 'login': user.login, 'display_name': user.display_name, 'disabled': user.disabled,
            'has_password': bool(user.password_hash), 'roles': roles, 'role_labels': [role_label(r) for r in roles],
            'active_sessions': active, 'last_seen_at': last.isoformat() if last else None,
            'created_at': user.created_at.isoformat() if user.created_at else None}


def member(db, workspace_id: str, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None or not _roles(db, user_id, workspace_id):
        raise NotFound('本工作区没有该账号')
    return user


def list_users(db, workspace_id: str, *, q: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
    base = select(User).where(User.id.in_(select(Membership.user_id).where(Membership.workspace_id == workspace_id)))
    if q:
        like = f'%{q.strip().lower()}%'
        base = base.where(func.lower(User.login).like(like) | func.lower(User.display_name).like(like))
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    rows = db.scalars(base.order_by(User.login).limit(limit).offset(offset)).all()
    return [view(db, u, workspace_id) for u in rows], total


def _check_roles(roles: list[str]) -> list[str]:
    roles = sorted(set(roles))
    if not roles:
        raise Invalid('至少选择一个角色')
    unknown = [r for r in roles if r not in VALID_ROLES]
    if unknown:
        raise Invalid(f'没有这个角色：{", ".join(unknown)}')
    return roles


def _active_admins(db, workspace_id: str) -> set[str]:
    return set(db.scalars(select(Membership.user_id).join(User, User.id == Membership.user_id)
                          .where(Membership.workspace_id == workspace_id, Membership.role == ADMIN_ROLE,
                                 User.disabled.is_(False))).all())


def _keep_an_admin(db, workspace_id: str, user_id: str, actor_id: str, losing_admin: bool) -> None:
    if not losing_admin:
        return
    if user_id == actor_id:
        raise Conflict('不能取消自己的系统管理员角色或停用自己')
    if _active_admins(db, workspace_id) == {user_id}:
        raise Conflict('这是本工作区最后一个系统管理员，不能取消或停用')


def create_user(db, workspace_id: str, actor_id: str | None, *, login: str, display_name: str, roles: list[str],
                password: str | None = None) -> dict:
    login = normalize_login(login)
    roles = _check_roles(roles)
    user = db.scalar(select(User).where(User.login == login))
    if user is not None and _roles(db, user.id, workspace_id):
        raise Conflict('该账号已在本工作区')
    if user is None:
        user = User(login=login, display_name=display_name.strip())
        db.add(user)
        db.flush()
    for role in roles:
        db.add(Membership(user_id=user.id, workspace_id=workspace_id, role=role))
    if password is not None:
        _set_password(user, password)
    db.flush()
    record(db, workspace_id, actor_id, 'identity.user.created', 'app_user', user.id,
           {'login': login, 'roles': roles, 'password_set': password is not None})
    return view(db, user, workspace_id)


def update_user(db, workspace_id: str, actor_id: str, user_id: str, *, display_name: str | None = None,
                disabled: bool | None = None) -> dict:
    user = member(db, workspace_id, user_id)
    changes = {}
    if display_name is not None and display_name.strip() != user.display_name:
        user.display_name = display_name.strip()
        changes['display_name'] = user.display_name
    if disabled is not None and disabled != user.disabled:
        if disabled:
            if user.id == actor_id:
                raise Conflict('不能停用自己')
            _keep_an_admin(db, workspace_id, user.id, actor_id, ADMIN_ROLE in _roles(db, user.id, workspace_id))
            sessions.revoke_user(db, user.id)
        user.disabled = disabled
        changes['disabled'] = disabled
    if changes:
        record(db, workspace_id, actor_id, 'identity.user.updated', 'app_user', user.id, changes)
    return view(db, user, workspace_id)


def set_roles(db, workspace_id: str, actor_id: str, user_id: str, roles: list[str]) -> dict:
    user = member(db, workspace_id, user_id)
    roles = _check_roles(roles)
    before = _roles(db, user.id, workspace_id)
    _keep_an_admin(db, workspace_id, user.id, actor_id, ADMIN_ROLE in before and ADMIN_ROLE not in roles)
    db.execute(delete(Membership).where(Membership.user_id == user.id, Membership.workspace_id == workspace_id,
                                        Membership.role.not_in(roles)))
    for role in roles:
        if role not in before:
            db.add(Membership(user_id=user.id, workspace_id=workspace_id, role=role))
    db.flush()
    record(db, workspace_id, actor_id, 'identity.user.roles_changed', 'app_user', user.id, {'before': before, 'after': roles})
    return view(db, user, workspace_id)


def _set_password(user: User, password: str) -> None:
    problem = passwords.password_problem(password)
    if problem:
        raise Invalid(problem)
    user.password_hash = passwords.hash_password(password)


def reset_password(db, workspace_id: str, actor_id: str, user_id: str, password: str | None = None) -> str | None:
    """Set a new password and sign the account out everywhere.

    With no password given, a random one-time password is generated and returned once, to hand
    to the person; it is never stored or logged in clear text.
    """
    user = member(db, workspace_id, user_id)
    generated = None
    if password is None:
        generated = password = secrets.token_urlsafe(12)
    _set_password(user, password)
    sessions.revoke_user(db, user.id)
    record(db, workspace_id, actor_id, 'identity.user.password_reset', 'app_user', user.id, {'generated': generated is not None})
    return generated


def sign_out_everywhere(db, workspace_id: str, actor_id: str, user_id: str) -> None:
    user = member(db, workspace_id, user_id)
    sessions.revoke_user(db, user.id)
    record(db, workspace_id, actor_id, 'identity.user.signed_out', 'app_user', user.id, {})
