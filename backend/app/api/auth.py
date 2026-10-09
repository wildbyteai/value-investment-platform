from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.domains.identity import passwords, sessions
from app.domains.platform.transactions import record

from app.api.deps import Principal, get_current_principal
from app.db import get_db
from app.domains.platform import data_mode
from app.models.identity import Membership, User, Workspace
from app.models.intake import InformationItem

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/identities")
def list_identities(db: Session = Depends(get_db)):
    """List synthetic login options for the demo login page (5 roles x 2 workspaces).
    Development mode only: in production this would hand every account name to anyone."""
    if get_settings().auth_mode != "dev":
        raise HTTPException(status_code=404, detail="Not Found")
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
        "permissions": __import__("app.domains.identity.permissions", fromlist=["role_permissions"]).role_permissions().get(principal.role, []),
    }


# ------------------------------------------------------------------ real sign-in

def _ip(request: Request) -> str | None:
    # Uvicorn runs with --proxy-headers behind the TLS proxy, so client.host is the real address.
    return request.client.host if request.client else None


def _workspaces(db, user: User) -> list[dict]:
    rows = db.execute(select(Membership.workspace_id, Membership.role, Workspace.name)
                      .join(Workspace, Workspace.id == Membership.workspace_id)
                      .where(Membership.user_id == user.id).order_by(Workspace.name)).all()
    out: dict[str, dict] = {}
    for ws_id, role, name in rows:
        out.setdefault(ws_id, {"id": ws_id, "name": name, "roles": []})["roles"].append(role)
    return list(out.values())


@router.get("/auth/state")
def auth_state(request: Request, db: Session = Depends(get_db)):
    """What the UI should show first: the dev identity picker, a login form, or the app."""
    mode = get_settings().auth_mode
    if mode == "dev":
        return {"mode": "dev", "user": None, "workspaces": []}
    user = sessions.resolve(db, request.cookies.get(sessions.COOKIE))
    if user is None:
        return {"mode": "session", "user": None, "workspaces": []}
    return {"mode": "session", "user": {"login": user.login, "display_name": user.display_name},
            "workspaces": _workspaces(db, user)}


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    if get_settings().auth_mode == "dev":
        raise HTTPException(status_code=409, detail="开发模式不使用密码登录")
    now = datetime.now(timezone.utc)
    ip = _ip(request)
    name = body.login.strip().lower()
    if sessions.throttled(db, name, ip, now):
        raise HTTPException(status_code=429, detail="尝试次数过多，请 15 分钟后再试")
    user = db.scalar(select(User).where(User.login == name))
    ok = passwords.verify_password(body.password, user.password_hash if user else None) and user is not None and not user.disabled
    sessions.note_attempt(db, name, ip, ok, now)
    if not ok:
        db.commit()
        raise HTTPException(status_code=401, detail="账号或密码不对")
    token = sessions.create(db, user, ip, request.headers.get("user-agent"), now)
    workspaces = _workspaces(db, user)
    for ws in workspaces:
        record(db, ws["id"], user.id, "auth.login", "app_user", user.id, {"ip": ip})
    db.commit()
    sessions.set_cookie(response, token)
    return {"user": {"login": user.login, "display_name": user.display_name}, "workspaces": workspaces}


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    sessions.revoke(db, request.cookies.get(sessions.COOKIE))
    db.commit()
    sessions.clear_cookie(response)
    return {"ok": True}


class PasswordIn(BaseModel):
    current: str = Field(min_length=1, max_length=256)
    new: str = Field(min_length=1, max_length=256)


@router.post("/auth/password")
def change_password(body: PasswordIn, request: Request, db: Session = Depends(get_db)):
    if get_settings().auth_mode == "dev":
        raise HTTPException(status_code=409, detail="开发模式不使用密码登录")
    token = request.cookies.get(sessions.COOKIE)
    user = sessions.resolve(db, token)
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    if not passwords.verify_password(body.current, user.password_hash):
        raise HTTPException(status_code=403, detail="当前密码不对")
    problem = passwords.password_problem(body.new)
    if problem:
        raise HTTPException(status_code=422, detail=problem)
    user.password_hash = passwords.hash_password(body.new)
    sessions.revoke_user(db, user.id, keep_token=token)  # sign out every other browser
    for ws in _workspaces(db, user):
        record(db, ws["id"], user.id, "auth.password_changed", "app_user", user.id, {})
    db.commit()
    return {"ok": True}
