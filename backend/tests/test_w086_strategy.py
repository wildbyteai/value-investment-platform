"""W-08.6 acceptance: strategy golden state machine sequence."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine


from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.services.intake_service import import_fixture  # noqa: E402
from services_companies import link_items, seed_companies  # noqa: E402


@pytest.fixture(scope="module")
def client():
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from scripts_seed import seed
    seed()
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        seed_companies(s)
        import_fixture(s)
        link_items(s)
        s.commit()
    with TestClient(app) as c:
        yield c, engine
    Base.metadata.drop_all(bind=engine)


def _headers(login="strat@demo"):
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    with engine.connect() as conn:
        from sqlalchemy import text
        ws_id = conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one()
    return {"X-Vip-Login": login, "X-Vip-Workspace": str(ws_id)}


def test_golden_sequence(client):
    c, _ = client
    r = c.post("/api/strategy/run-golden", headers=_headers("strat@demo"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["final_status"] == "OUT"
    reasons = [t["reason"] for t in body["transitions"]]
    assert reasons == ["ENTER", "MISSING_DATA", "EXIT", "ENTER", "RISK"]
    # two distinct ENTER records (adjacent sessions)
    assert reasons.count("ENTER") == 2


def test_change_records_immutable_and_no_delivery(client):
    c, _ = client
    r = c.get("/api/strategy/transitions", headers=_headers("research@demo"))
    assert r.status_code == 200
    records = r.json()
    assert len(records) == 5
    assert all(x["delivery_count"] == 0 for x in records)


def test_researcher_cannot_publish_strategy(client):
    c, _ = client
    r = c.post("/api/strategy/run-golden", headers=_headers("research@demo"))
    assert r.status_code == 403
