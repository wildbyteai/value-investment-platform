from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import sessions
from app.db import get_db
from app.models.identity import Membership, User, Workspace
from app.security import role_has, VALID_ROLES


@dataclass
class Principal:
    user: User
    workspace: Workspace
    role: str


def get_current_principal(
    request: Request,
    db: Session = Depends(get_db),
) -> Principal:
    """Who is calling, and in which workspace.

    * ``session`` (default, production): the user comes from the HttpOnly session cookie set by
      ``POST /api/auth/login``. Client headers can only *choose* among the caller's own workspaces.
    * ``dev`` (local work and the test suite only): the mock header ``X-Vip-Login``.
    Membership in the requested workspace is checked server-side in both modes.
    """
    workspace_id = request.headers.get("X-Vip-Workspace")
    if get_settings().auth_mode == "dev":
        login = request.headers.get("X-Vip-Login")
        if not login:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing mock identity headers")
        user = db.scalar(select(User).where(User.login == login))
    else:
        user = sessions.resolve(db, request.cookies.get(sessions.COOKIE))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    if not workspace_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少工作区")

    ws = db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    if ws is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="unknown workspace")

    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.workspace_id == ws.id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not a member of this workspace")

    return Principal(user=user, workspace=ws, role=membership.role)


def require(permission: str):
    def _dep(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not role_has(principal.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role '{principal.role}' lacks permission '{permission}'",
            )
        return principal

    return _dep


def require_any(*permissions: str):
    """Allow the call when the role holds at least one of ``permissions``."""
    def _dep(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not any(role_has(principal.role, p) for p in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role '{principal.role}' lacks any of {', '.join(permissions)}",
            )
        return principal

    return _dep
