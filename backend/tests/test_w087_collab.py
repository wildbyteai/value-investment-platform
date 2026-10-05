"""W-08.7 acceptance: watchlist/notes, idempotent outbox claim."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import Outbox  # noqa: E402
from app.models.company import Company, Security  # noqa: E402
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


def _headers(login="research@demo"):
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    with engine.connect() as conn:
        from sqlalchemy import text
        ws_id = conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one()
    return {"X-Vip-Login": login, "X-Vip-Workspace": str(ws_id)}


def test_watchlist_and_note(client):
    c, engine = client
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        sec = s.scalar(select(Security).where(Security.ticker == "0001.HK"))
        co = s.scalar(select(Company).where(Company.name == "合成甲制造"))
    r = c.post(f"/api/me/watchlist/{sec.id}", headers=_headers())
    assert r.status_code == 200
    # duplicate idempotent
    r = c.post(f"/api/me/watchlist/{sec.id}", headers=_headers())
    assert r.status_code == 200
    r = c.get("/api/me/watchlist", headers=_headers())
    assert any(x["ticker"] == "0001.HK" for x in r.json())

    r = c.post("/api/me/notes", json={"company_id": co.id, "body": "关注订单执行"}, headers=_headers())
    assert r.status_code == 200
    r = c.get("/api/me/notes", headers=_headers())
    assert any("关注订单" in x["body"] for x in r.json())


def test_outbox_claim_idempotent(client):
    c, engine = client
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        from app.services.transactions import workspace
        ob = Outbox(workspace_id=workspace(s), aggregate_type="ingestion_run", aggregate_id="x",
                    event_type="ingestion_run.created", payload_json="{}")
        s.add(ob)
        s.commit()
        ob_id = ob.id
    r1 = c.post(f"/api/worker/outbox/{ob_id}/claim", headers=_headers("admin@demo"))
    assert r1.status_code == 200
    assert r1.json()["claimed"] is True
    # second claim must be no-op, not an error / redelivery
    r2 = c.post(f"/api/worker/outbox/{ob_id}/claim", headers=_headers("admin@demo"))
    assert r2.status_code == 200
    assert r2.json()["already_dispatched"] is True
