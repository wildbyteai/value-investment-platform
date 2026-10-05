from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal
from app.db import get_db
from app.services import data_mode
from app.models.identity import Membership, User, Workspace
from app.models.intake import InformationItem

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/identities")
def list_identities(db: Session = Depends(get_db)):
    """List synthetic login options for the demo login page (5 roles x 2 workspaces)."""
    users = db.scalars(select(User).order_by(User.login)).all()
    workspaces = db.scalars(select(Workspace).order_by(Workspace.name)).all()
    memberships = db.scalars(select(Membership)).all()
    by_user: dict[str, list[dict]] = {}
    for m in memberships:
        by_user.setdefault(m.user_id, []).append(
            {"workspace_id": m.workspace_id, "role": m.role}
        )
    real_ws={c.workspace_id for c in db.scalars(select(InformationItem)).all() if data_mode.real_item(db,c,c.workspace_id)}
    return {
        "data_mode":"synthetic_test" if data_mode.fixture_mode() else "real_public",
        "workspaces": [{"id": w.id, "name": w.name if data_mode.fixture_mode() else ("真实公开资料研究" if w.id in real_ws else "空研究工作区"), "has_real_data":w.id in real_ws} for w in workspaces],
        "users": [
            {
                "login": u.login,
                "display_name": u.display_name,
                "memberships": by_user.get(u.id, []),
            }
            for u in users
        ],
    }


@router.get("/me")
def me(principal: Principal = Depends(get_current_principal)):
    return {
        "user": {"login": principal.user.login, "display_name": principal.user.display_name},
        "workspace": {"id": principal.workspace.id, "name": principal.workspace.name if data_mode.fixture_mode() else "真实公开资料研究"},
        "data_mode":"synthetic_test" if data_mode.fixture_mode() else "real_public",
        "role": principal.role,
        "permissions": __import__("app.security", fromlist=["role_permissions"]).role_permissions().get(principal.role, []),
    }
