"""W-08.3 acceptance: companies, A/H securities, rule-based linking, no_link."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker


from app.db import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.company import Company, ItemCompanyLink, Security  # noqa: E402
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
        stats = link_items(s)
        s.commit()
    with TestClient(app) as c:
        yield c, stats, engine
    Base.metadata.drop_all(bind=engine)


def test_a_h_two_securities_different_currency(client):
    _, _, engine = client
    with engine.connect() as conn:
        from sqlalchemy import text
        rows = conn.execute(text(
            "SELECT s.market, s.ticker, s.currency FROM security s JOIN company c ON c.id=s.company_id WHERE c.name='合成甲制造' ORDER BY s.market"
        )).all()
    assert len(rows) == 2
    markets = {r[0] for r in rows}
    assert markets == {"CN_A", "HK"}
    currencies = {r[2] for r in rows}
    assert currencies == {"CNY", "HKD"}


def test_link_stats_and_no_link(client):
    _, stats, _ = client
    assert stats["accepted"] >= 4
    assert stats["no_link"] >= 2  # 合成消费 / 合成科技
    assert stats["ambiguous"] == 0


def test_company_timeline_only_accepted(client):
    _, _, engine = client
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        a = s.scalar(select(Company).where(Company.name == "合成甲制造"))
        links = s.scalars(select(ItemCompanyLink).where(ItemCompanyLink.company_id == a.id)).all()
        titles = []
        for lk in links:
            if lk.status == "accepted":
                from app.models.intake import InformationItem
                it = s.get(InformationItem, lk.item_id)
                titles.append(it.title)
    assert any("订单安排" in t for t in titles)
    # 合成乙制造 item must NOT appear on company A timeline
    assert not any("公告摘要" in t for t in titles)


def test_relink_idempotent(client):
    _, _, engine = client
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        before = s.scalar(select(func.count(ItemCompanyLink.id)))
        link_items(s)
        s.commit()
        after = s.scalar(select(func.count(ItemCompanyLink.id)))
    assert before == after
