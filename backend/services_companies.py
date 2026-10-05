"""Seed synthetic companies and securities; run rule-based item linking."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.company import Company, EconomicFact, ItemCompanyLink, Security
from app.models.intake import InformationItem, SourceRegistry

# Synthetic company A: A + H listings (same company, two securities, different currency/market)
COMPANIES = [
    {
        "id": "00000000-0000-4000-8000-000000000001",
        "name": "合成甲制造",
        "industry_key": "manufacturing",
        "securities": [
            {"market": "CN_A", "ticker": "600001.SH", "currency": "CNY"},
            {"market": "HK", "ticker": "0001.HK", "currency": "HKD"},
        ],
    },
    {
        "id": "00000000-0000-4000-8000-000000000002",
        "name": "合成乙制造",
        "industry_key": "manufacturing",
        "securities": [
            {"market": "CN_A", "ticker": "600002.SH", "currency": "CNY"},
        ],
    },
]


def seed_companies(db: Session, workspace_id=None) -> None:
    from app.services.data_mode import require_fixture
    require_fixture()
    for c in COMPANIES:
        company = db.scalar(select(Company).where(Company.name == c["name"]))
        if company is None:
            company = Company(id=c["id"], name=c["name"], industry_key=c["industry_key"])
            db.add(company)
            db.flush()
        for s in c["securities"]:
            exists = db.scalar(
                select(Security).where(
                    Security.company_id == company.id,
                    Security.market == s["market"],
                    Security.ticker == s["ticker"],
                )
            )
            if exists is None:
                db.add(Security(company_id=company.id, **s))
    db.flush()
    from app.services.research_seed import seed_inputs
    for company in db.scalars(select(Company)).all():
        seed_inputs(db, company, workspace_id)


def link_items(db: Session, workspace_id=None) -> dict:
    """Rule-based auto-link: title contains company name.

    Policy (auto-review-standard-v1): accept if relevance>=0.50 and confidence>=0.90.
    Multiple matches -> ambiguous. No match -> no_link.
    """
    from app.services.transactions import workspace
    workspace_id = workspace(db, workspace_id)
    companies = db.scalars(select(Company)).all()
    items = db.scalars(select(InformationItem).where(InformationItem.workspace_id == workspace_id, InformationItem.source_id.in_(select(SourceRegistry.id).where(SourceRegistry.source_key=="local-fixture")))).all()
    stats = {"accepted": 0, "ambiguous": 0, "no_link": 0}

    for item in items:
        matches = [c for c in companies if c.name in item.title]
        # remove existing links for this item (re-run idempotent)
        db.query(ItemCompanyLink).filter(ItemCompanyLink.item_id == item.id).delete()

        if len(matches) == 0:
            db.add(ItemCompanyLink(
                item_id=item.id, company_id=None, label_text="",
                status="no_link", relevance=None, confidence=None,
            ))
            stats["no_link"] += 1
        elif len(matches) > 1:
            for c in matches:
                db.add(ItemCompanyLink(
                    item_id=item.id, company_id=c.id, label_text=c.name,
                    status="ambiguous", relevance=0.5, confidence=0.6,
                ))
            stats["ambiguous"] += 1
        else:
            c = matches[0]
            db.add(ItemCompanyLink(
                item_id=item.id, company_id=c.id, label_text=c.name,
                status="accepted", relevance=0.9, confidence=0.95,
            ))
            stats["accepted"] += 1
    db.flush()
    return stats


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_companies(db)
        stats = link_items(db)
        db.commit()
        print(json.dumps(stats, ensure_ascii=False))
    finally:
        db.close()
