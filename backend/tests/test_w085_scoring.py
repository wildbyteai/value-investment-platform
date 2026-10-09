"""W-08.5 acceptance: template resolution A vs B, A/H independent valuation, UNKNOWN."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.company import Company  # noqa: E402
from app.domains.news.intake_service import import_fixture  # noqa: E402
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


def _headers(login="viewer@demo"):
    engine = create_engine(os.environ["VIP_DB_URL"], future=True)
    with engine.connect() as conn:
        from sqlalchemy import text
        ws_id = conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one()
    return {"X-Vip-Login": login, "X-Vip-Workspace": str(ws_id)}


def _company_id(engine, name):
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        return s.scalar(select(Company).where(Company.name == name)).id


def test_template_differs_between_a_and_b(client):
    c, engine = client
    a_id = _company_id(engine, "合成甲制造")
    b_id = _company_id(engine, "合成乙制造")
    ra = c.get(f"/api/companies/{a_id}/score", headers=_headers()).json()
    rb = c.get(f"/api/companies/{b_id}/score", headers=_headers()).json()
    # company A carries company-level patch
    assert "company" in ra["template"]["levels_applied"]
    assert ra["template"]["weights"]["profit_quality"] == 0.35
    # company B does not
    assert "company" not in rb["template"]["levels_applied"]
    assert rb["template"]["weights"]["profit_quality"] == 0.30


def test_insufficient_evidence_is_unknown(client):
    c, engine = client
    b_id = _company_id(engine, "合成乙制造")
    rb = c.get(f"/api/companies/{b_id}/score", headers=_headers()).json()
    assert rb["quality_score"] is None
    assert "INSUFFICIENT_EVIDENCE" in rb["reasons"]


def test_a_h_valuation_independent(client):
    c, engine = client
    a_id = _company_id(engine, "合成甲制造")
    ra = c.get(f"/api/companies/{a_id}/score", headers=_headers()).json()
    secs = {s["market"]: s for s in ra["securities"]}
    assert secs["CN_A"]["valuation_score"] is not None
    assert secs["HK"]["valuation_score"] is not None
    # different pe -> different score, independent currency/market
    assert secs["CN_A"]["valuation_score"] != secs["HK"]["valuation_score"]


def test_unknown_pe_is_unknown(client):
    c, engine = client
    b_id = _company_id(engine, "合成乙制造")
    rb = c.get(f"/api/companies/{b_id}/score", headers=_headers()).json()
    assert rb["securities"][0]["valuation_score"] is None
    assert rb["securities"][0]["reason"] == "UNKNOWN_PE"
