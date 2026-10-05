"""W-08.2 acceptance: synthetic intake readable, lineage, idempotency, partial failure."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker


from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.intake import InformationItem  # noqa: E402


@pytest.fixture(scope="module")
def client():
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from scripts_seed import seed
    seed()
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def _headers(login):
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    with engine.connect() as conn:
        ws_id = conn.execute(
            text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")
        ).scalar_one()
    return {"X-Vip-Login": login, "X-Vip-Workspace": str(ws_id)}


def test_import_creates_readable_items(client):
    r = client.post("/api/intake/synthetic", headers=_headers("data@demo"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["output"]["imported"] == 6

    r = client.get("/api/intake/items", headers=_headers("viewer@demo"))
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 6
    # unknown-date item (digest-2: precision unknown, date null) must be last
    assert items[-1]["precision"] == "unknown"
    # dated items first
    assert items[0]["publication_date"] is not None


def test_reimport_is_idempotent(client):
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        before = s.scalar(select(func.count(InformationItem.id)))
    r = client.post("/api/intake/synthetic", headers=_headers("data@demo"))
    assert r.status_code == 200
    with Session() as s:
        after = s.scalar(select(func.count(InformationItem.id)))
    assert before == after, "re-import must not duplicate items"


def test_partial_failure_keeps_good_items(client):
    # inject a failure via a second run flag: directly call service with extra_fail_keys
    from app.services.intake_service import import_fixture
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        run = import_fixture(s, extra_fail_keys=["digest-1"])
        s.commit()
        assert run.status == "partial"
        out = __import__("json").loads(run.output_json)
        assert out["failed"] == 1
        # good items still readable
        items = s.scalars(select(InformationItem)).all()
        assert len(items) == 6  # still 6 (digest-1 already existed from prior import)


def test_item_detail_body_and_reference_states(client):
    r = client.get("/api/intake/items", headers=_headers("viewer@demo"))
    items = r.json()
    # find digest-1 id via title
    detail_id = next(x["id"] for x in items if "订单安排" in x["title"])
    r = client.get(f"/api/intake/items/{detail_id}", headers=_headers("viewer@demo"))
    assert r.status_code == 200
    d = r.json()
    assert d["body_access"]["state"] == "not_acquired"  # has url refs but body not fetched
    assert len(d["reference_access"]) == 2
    states = {ref["access"]["state"] for ref in d["reference_access"]}
    assert "available" in states


def test_viewer_cannot_import(client):
    r = client.post("/api/intake/synthetic", headers=_headers("viewer@demo"))
    assert r.status_code == 403
