from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

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
    """Mock identity: header X-Vip-Login + X-Vip-Workspace.

    v0.0.1 has no real login; the login page lists synthetic identities.
    """
    login = request.headers.get("X-Vip-Login")
    workspace_id = request.headers.get("X-Vip-Workspace")
    if not login or not workspace_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing mock identity headers")

    user = db.scalar(select(User).where(User.login == login))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unknown user")

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
