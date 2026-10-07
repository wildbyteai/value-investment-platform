"""R1 guardrail: fixed inputs -> fixed PE and valuation score, for both PE paths.

The formal path (scoring_service.score_security) and the reference path
(reference_research.valuation_reference) compute PE separately and pick share capital
by different rules. These cases pin the exact numbers so a refactor that unifies them
cannot silently move a result. No database: rows are plain fixed objects.
"""
from datetime import datetime, timezone
from types import SimpleNamespace
import json
import pytest
from app.services.scoring_service import score_security
from app.services.reference_research import valuation_reference

AS_OF = datetime(2026, 9, 30, 8, tzinfo=timezone.utc)
EVID = [{'synthetic': True, 'locator': 'fixed regression fixture'}]


def row(id, kind, key, payload):
    return SimpleNamespace(id=id, kind=kind, input_key=key, payload_json=json.dumps(payload),
                           content_hash='h-' + id, known_at=AS_OF)


def financials(profit='1200000000', shares='1000000000'):
    return {'ordinary_profit_ttm': profit, 'ordinary_shares': shares, 'currency': 'CNY',
            'scope': 'matching_ordinary_equity', 'equivalent_share_rights': True, 'evidence': EVID,
            'obligation_valid_until': '2027-04-30T16:00:00+00:00',
            'lineage': {'facts': [{'key': 'ordinary_shares', 'period_end': '2026-06-30'},
                                  {'key': 'ordinary_profit', 'period_end': '2026-06-30'}]}}


def price(ticker, close, currency, fx):
    return {'ticker': ticker, 'raw_close': close, 'currency': currency, 'fx_per_cny': fx, 'evidence': EVID,
            'session': '2026-09-30', 'is_final': True, 'price_kind': 'CLOSING'}


CASES = {
    # name: (security, rows, expected pe, expected valuation score)
    'a_share_cny': (SimpleNamespace(id='s1', market='CN_A', ticker='600001.SH', currency='CNY', company_id='c1'),
                    [row('f', 'financials', 'financials', financials()),
                     row('p', 'price', 'price:600001.SH', price('600001.SH', '18.00', 'CNY', '1'))]),
    'h_share_hkd_fx': (SimpleNamespace(id='s2', market='HK', ticker='01801.HK', currency='HKD', company_id='c1'),
                       [row('f', 'financials', 'financials', financials()),
                        row('p', 'price', 'price:01801.HK', price('01801.HK', '15.60', 'HKD', '1.0857'))]),
    'cheap_full_score': (SimpleNamespace(id='s3', market='CN_A', ticker='600002.SH', currency='CNY', company_id='c1'),
                         [row('f', 'financials', 'financials', financials('5000000000')),
                          row('p', 'price', 'price:600002.SH', price('600002.SH', '40.00', 'CNY', '1'))]),
}
GOLDEN = {
    # 1.2 CNY EPS at 18.00 CNY -> PE 15; score linear from PE 25 (0) to PE 10 (100).
    'a_share_cny': ('15.000000000000', '66.666666666667'),
    # 1.2 CNY EPS x 1.0857 HKD/CNY = 1.30284 HKD; 15.60 / 1.30284.
    'h_share_hkd_fx': ('11.973841761076', '86.841054926160'),
    # PE 8 is below the full-score PE of 10, so the score caps at 100.
    'cheap_full_score': ('8.000000000000', '100.000000000000'),
}


@pytest.mark.parametrize('name', sorted(CASES))
def test_formal_and_reference_pe_are_pinned_and_agree(name):
    security, rows = CASES[name]
    formal = score_security(None, security, workspace_id='ws', as_of=AS_OF, cutoff=AS_OF, input_rows=rows)
    reference = valuation_reference(security, rows, AS_OF, AS_OF)
    assert formal['reason'] is None, formal['missing_data']
    assert reference['status'] == 'REFERENCE', reference['missing_data']
    assert (formal['pe_exact'], formal['valuation_exact']) == GOLDEN[name]
    assert (reference['pe_exact'], reference['valuation_exact']) == GOLDEN[name]


def test_nonpositive_profit_has_no_pe_on_either_path():
    security = CASES['a_share_cny'][0]
    rows = [row('f', 'financials', 'financials', financials('-1')),
            row('p', 'price', 'price:600001.SH', price('600001.SH', '18.00', 'CNY', '1'))]
    assert score_security(None, security, workspace_id='ws', as_of=AS_OF, cutoff=AS_OF, input_rows=rows).get('pe_exact') is None
    reference = valuation_reference(security, rows, AS_OF, AS_OF)
    assert reference['pe_exact'] is None and reference['status'] == 'NOT_APPLICABLE'
