"""W-08.1 acceptance: authorized write + audit/outbox readback + RBAC denials."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Point at the isolated test database BEFORE app import.

from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, future=True)

    from scripts_seed import seed
    seed()

    with TestClient(app) as c:
        yield c

    Base.metadata.drop_all(bind=engine)


def _headers(login: str, ws_name: str = "演示研究组织（合成数据）"):
    # resolve workspace id from the DB
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    with engine.connect() as conn:
        ws_id = conn.execute(
            text("SELECT id FROM workspace WHERE name = :n"), {"n": ws_name}
        ).scalar_one()
    return {"X-Vip-Login": login, "X-Vip-Workspace": str(ws_id)}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["db"] == "ok"


def test_data_admin_can_create_run_and_audit_outbox_written(client):
    r = client.post(
        "/api/demo/runs",
        json={"source_key": "synthetic-local", "note": "首条合成导入"},
        headers=_headers("data@demo"),
    )
    assert r.status_code == 200, r.text
    run_id = r.json()["id"]
    assert r.json()["status"] == "created"

    # research.read: any role can list runs
    r = client.get("/api/demo/runs", headers=_headers("viewer@demo"))
    assert r.status_code == 200
    assert any(x["id"] == run_id for x in r.json())

    # system_admin can read audit: the create action was audited
    r = client.get("/api/demo/audit", headers=_headers("admin@demo"))
    assert r.status_code == 200
    assert any(a["action"] == "ingestion_run.create" and a["entity_id"] == run_id for a in r.json())

    # outbox row exists undispatched, then worker dispatches it
    r = client.get("/api/demo/outbox", headers=_headers("admin@demo"))
    assert r.status_code == 200
    out = next(o for o in r.json() if o["aggregate_id"] == run_id)
    r = client.post(f"/api/demo/outbox/{out['id']}/dispatch", headers=_headers("admin@demo"))
    assert r.status_code == 200
    r = client.get("/api/demo/outbox", headers=_headers("admin@demo"))
    assert all(o["id"] != out["id"] for o in r.json())


def test_viewer_cannot_create_run(client):
    r = client.post(
        "/api/demo/runs",
        json={"source_key": "x"},
        headers=_headers("viewer@demo"),
    )
    assert r.status_code == 403


def test_viewer_cannot_read_audit(client):
    r = client.get("/api/demo/audit", headers=_headers("viewer@demo"))
    assert r.status_code == 403


def test_researcher_cannot_manage_source(client):
    # researcher lacks source.manage
    r = client.post(
        "/api/demo/runs",
        json={"source_key": "x"},
        headers=_headers("research@demo"),
    )
    assert r.status_code == 403


def test_missing_identity_is_unauthorized(client):
    r = client.get("/api/demo/runs")
    assert r.status_code == 401
