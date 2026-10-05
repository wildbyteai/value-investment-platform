"""Seed synthetic demo data: 2 workspaces x 5 role users.

Idempotent: safe to run repeatedly.
"""
from __future__ import annotations

import json

from sqlalchemy import select

from app.db import SessionLocal, engine, Base
import app.models  # noqa: F401
from app.models.identity import Membership, User, Workspace

WORKSPACES = [
    ("demo", "演示研究组织（合成数据）"),
    ("isolated", "隔离测试组织"),
]
USERS = [
    ("admin@demo", "管理员（system_admin）", "system_admin"),
    ("data@demo", "数据管理员（data_admin）", "data_admin"),
    ("research@demo", "研究员（researcher）", "researcher"),
    ("strat@demo", "策略经理（strategy_manager）", "strategy_manager"),
    ("viewer@demo", "观察者（viewer）", "viewer"),
]


def seed() -> None:
    # Schema is managed by Alembic; normal seed never creates/replaces schema.
    db = SessionLocal()
    try:
        ws_by_key: dict[str, Workspace] = {}
        for key, name in WORKSPACES:
            ws = db.scalar(select(Workspace).where(Workspace.name == name))
            if ws is None:
                ws = Workspace(name=name)
                db.add(ws)
                db.flush()
            ws_by_key[key] = ws

        for login, display, role in USERS:
            user = db.scalar(select(User).where(User.login == login))
            if user is None:
                user = User(login=login, display_name=display)
                db.add(user)
                db.flush()
            for ws in ws_by_key.values():
                exists = db.scalar(
                    select(Membership).where(
                        Membership.user_id == user.id,
                        Membership.workspace_id == ws.id,
                        Membership.role == role,
                    )
                )
                if exists is None:
                    db.add(Membership(user_id=user.id, workspace_id=ws.id, role=role))
        db.commit()
        print(
            json.dumps(
                {
                    "workspaces": [{"id": w.id, "name": w.name} for w in ws_by_key.values()],
                    "users": [u[0] for u in USERS],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    from app.services.data_mode import require_fixture
    require_fixture()
    seed()
    from services_companies import seed_companies, link_items
    from app.services.intake_service import import_fixture
    from app.services.decision_service import auto_decide
    with SessionLocal() as db:
        ws = db.scalar(select(Workspace.id).where(Workspace.name == WORKSPACES[0][1]))
        seed_companies(db, ws)
        import_fixture(db, workspace_id=ws)
        link_items(db, ws)
        auto_decide(db, ws)
        db.commit()
        print("Synthetic research inputs and decisions seeded; real records untouched.")
