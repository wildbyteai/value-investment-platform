"""R3: domain errors, unit of work, source registry, strike-zone classification + API."""
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.errors import Conflict, DomainError, Forbidden, Invalid, NotFound
from app.core.uow import unit_of_work
from app.domains.strategy import strike_zone as sz
from app.domains.market_data import registry

APP = Path(__file__).resolve().parents[1] / 'app'


def test_services_do_not_import_fastapi():
    offenders = [str(p.relative_to(APP)) for p in (APP / 'domains').rglob('*.py') if 'fastapi' in p.read_text(encoding='utf-8')]
    assert offenders == []


def test_domain_error_status_codes():
    assert [e('x').status_code for e in (Forbidden, NotFound, Conflict, Invalid)] == [403, 404, 409, 422]
    assert issubclass(Conflict, DomainError)


class FakeDb:
    def __init__(self): self.log = []
    def commit(self): self.log.append('commit')
    def rollback(self): self.log.append('rollback')


def test_unit_of_work_commits_or_rolls_back():
    db = FakeDb()
    with unit_of_work(db):
        pass
    with pytest.raises(Conflict):
        with unit_of_work(db):
            raise Conflict('x')
    assert db.log == ['commit', 'rollback']


def test_registry_lists_every_layer_and_resolves_prefixes():
    keys = {s.key for s in registry.all_sources()}
    assert {'baostock-a-daily', 'ecb-reference-fx', 'cninfo-bounded-issuer-disclosures'} <= keys
    assert registry.get('eodhd-hk-daily').module == 'app.domains.market_data.eodhd_source'
    assert registry.get('cninfo-bounded-issuer-disclosures').layer == 'news'
    assert registry.get('nope') is None
    with pytest.raises(ValueError):
        registry.register(registry.SourceSpec('ecb-reference-fx', 'x', 'news', 'x', 'x', 'x'))


GOOD_GATES = {'status': 'match', 'gaps': [], 'conditions': [
    {'field': 'company.quality_score', 'result': True}, {'field': 'security.valuation_score', 'result': False},
    {'field': 'metrics.roe_ttm', 'result': True}]}
COMPANY = {'company_id': 'c1', 'industry_key': 'manufacturing', 'coverage_exact': '0.9'}


def test_sweet_spot_needs_all_three():
    zone = sz.classify(COMPANY, {'pe_ttm': 9}, GOOD_GATES)  # margin 1 - 9/15 = 40%
    assert zone.zone == sz.SWEET and zone.label == '甜区'
    assert zone.margin_of_safety == '0.4000'
    # valuation gate is the margin's job, not the business check's
    assert [c.passed for c in zone.checks] == [True, True, True]


def test_thin_margin_is_edge_and_expensive_is_outside():
    assert sz.classify(COMPANY, {'pe_ttm': 12}, GOOD_GATES).zone == sz.EDGE      # 20%
    assert sz.classify(COMPANY, {'pe_ttm': 14}, GOOD_GATES).zone == sz.OUTSIDE   # 6.7%
    assert sz.classify(COMPANY, {'pe_ttm': -3}, GOOD_GATES).zone == sz.EDGE      # no P/E, no proxy


def test_hard_risk_vetoes_even_when_cheap():
    gates = {'status': 'risk_excluded', 'risks': [{'risk_code': 'confirmed_fraud'}], 'conditions': [], 'gaps': []}
    zone = sz.classify(COMPANY, {'pe_ttm': 5}, gates)
    assert zone.zone == sz.OUTSIDE and '一票否决' in zone.checks[1].detail


def test_circle_whitelist_and_coverage():
    cfg = {**sz.policy(), 'circle_of_competence': {**sz.policy()['circle_of_competence'], 'industry_keys': ['biotech']}}
    assert sz.classify(COMPANY, {'pe_ttm': 9}, GOOD_GATES, cfg).zone == sz.OUTSIDE
    low = {**COMPANY, 'coverage_exact': '0.5'}
    assert sz.classify(low, {'pe_ttm': 9}, GOOD_GATES).checks[0].passed is False
    unknown = {**COMPANY, 'coverage_exact': None}
    assert sz.classify(unknown, {'pe_ttm': 9}, GOOD_GATES).zone == sz.EDGE


def test_valuation_score_proxy_when_pe_missing():
    assert sz.classify(COMPANY, {'valuation_score': 70}, GOOD_GATES).zone == sz.SWEET
    assert sz.classify(COMPANY, {'valuation_score': 40}, GOOD_GATES).zone == sz.EDGE


def test_policy_numbers_live_in_config():
    m = sz.policy()['margin_of_safety']
    assert (m['sweet_minimum'], m['fair_pe_ttm']) == ('0.30', '15')


@pytest.fixture(scope='module')
def client():
    from app.db import Base
    from app.main import app
    from app.domains.news.intake_service import import_fixture
    from services_companies import link_items, seed_companies
    engine = create_engine(os.environ['VIP_DB_URL'], future=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from scripts_seed import seed
    seed()
    with sessionmaker(bind=engine, future=True)() as s:
        seed_companies(s); import_fixture(s); link_items(s); s.commit()
    with engine.connect() as conn:
        ws = conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one()
    with TestClient(app) as c:
        yield c, str(ws)
    Base.metadata.drop_all(bind=engine)


def h(ws, login):
    return {'X-Vip-Login': login, 'X-Vip-Workspace': ws}


def test_strike_zone_board_judges_a_and_h_separately(client):
    c, ws = client
    r = c.get('/api/strike-zone', headers=h(ws, 'viewer@demo'))
    assert r.status_code == 200, r.text
    body = r.json()
    markets = {(row['company'], row['market']) for row in body['rows']}
    assert ('合成甲制造', 'CN_A') in markets and ('合成甲制造', 'HK') in markets
    assert sum(body['counts'].values()) == len(body['rows'])
    assert all(len(row['checks']) == 3 for row in body['rows'])


def test_strike_zone_company_404_uses_domain_error(client):
    c, ws = client
    r = c.get('/api/strike-zone/companies/missing', headers=h(ws, 'viewer@demo'))
    assert r.status_code == 404
    assert r.json()['error'] == {'code': 'not_found', 'message': '当前研究模式和工作区没有该公司'}
    assert r.json()['request_id'] == r.headers['x-request-id']


def test_admin_sources_requires_admin(client):
    c, ws = client
    assert c.get('/api/admin/sources', headers=h(ws, 'viewer@demo')).status_code == 403
    r = c.get('/api/admin/sources', headers=h(ws, 'data@demo'))
    assert r.status_code == 200 and any(s['key'] == 'ecb-reference-fx' for s in r.json())
    assert c.get('/api/admin/sources', headers=h(ws, 'admin@demo')).status_code == 200
