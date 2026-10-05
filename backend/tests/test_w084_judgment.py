"""W-08.4 acceptance: AUTO accepted, HUMAN override CAS, 409, RBAC."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.judgment import JudgmentSlot  # noqa: E402
from app.services.intake_service import import_fixture  # noqa: E402
from services_companies import link_items, seed_companies  # noqa: E402


@pytest.fixture(scope="module")
def client():
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from scripts_seed import seed
    seed()
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        seed_companies(s)
        import_fixture(s)
        link_items(s)
        s.commit()
    with TestClient(app) as c:
        yield c, engine
    Base.metadata.drop_all(bind=engine)


def _headers(login):
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    with engine.connect() as conn:
        from sqlalchemy import text
        ws_id = conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one()
    return {"X-Vip-Login": login, "X-Vip-Workspace": str(ws_id)}


def test_auto_run_creates_accepted(client):
    c, _ = client
    r = c.post("/api/judgments/auto-run", headers=_headers("research@demo"))
    assert r.status_code == 200, r.text
    assert r.json()["auto_accepted"] >= 4
    r = c.get("/api/judgments", headers=_headers("viewer@demo"))
    assert r.status_code == 200
    assert len(r.json()) >= 4
    assert r.json()[0]["effective"]["direction"] == "positive"


def test_human_override_with_cas(client):
    c, engine = client
    # pick first slot
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        slot = s.scalar(select(JudgmentSlot))
        key, gen = slot.slot_key, slot.generation
    r = c.post(
        f"/api/judgments/{key}/override",
        json={"value": {"direction": "negative", "magnitude": "-0.2"}},
        headers={**_headers("research@demo"), "If-Match-Generation": str(gen)},
    )
    assert r.status_code == 200, r.text
    assert r.json()["value"]["magnitude"] == "-0.2"
    # effective now reflects human
    r = c.get("/api/judgments", headers=_headers("viewer@demo"))
    eff = next(x for x in r.json() if x["slot_key"] == key)
    assert eff["effective"]["magnitude"] == "-0.2"


def test_stale_generation_returns_409(client):
    c, engine = client
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        slot = s.scalar(select(JudgmentSlot))
        key, gen = slot.slot_key, slot.generation
    r = c.post(
        f"/api/judgments/{key}/override",
        json={"value": {"direction": "positive"}},
        headers={**_headers("research@demo"), "If-Match-Generation": str(gen - 1)},
    )
    assert r.status_code == 409


def test_viewer_cannot_override(client):
    c, _ = client
    r = c.post(
        "/api/judgments/any/override",
        json={"value": {}},
        headers={**_headers("viewer@demo"), "If-Match-Generation": "1"},
    )
    assert r.status_code == 403
