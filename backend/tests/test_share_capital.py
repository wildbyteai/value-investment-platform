"""Original disposable share counts; no real quantities in fixtures."""
from types import SimpleNamespace
from datetime import datetime
from copy import deepcopy
from decimal import Decimal
import pytest
from app.services.share_capital import normalize
from app.services.original_financials import FinancialGap
from app.services.scoring_service import score_security,metrics_from_financials
from app.services.transactions import canonical
from test_original_inputs import bundle as financial_bundle,evidence
from app.services.original_financials import normalize as financials


def bundle():
    return {'scope':'parent_ordinary','shares_as_of':'2026-09-17','ordinary_shares_verified_through':'2026-09-17',
        'complete_classes_confirmed':True,'equivalent_share_rights_confirmed':True,
        'rights_basis':'original disposable same economic rights note','share_basis_evidence':evidence(),
        'classes':[{'class_key':'H','reviewed':True,'unit':'shares','outstanding_shares':'1,200','treasury_shares':'100','issued_shares':'1,300',
                    'original_line':'Closing balance 2026-09-17 1,200 100 1,300','column_basis':'outstanding, treasury, issued','evidence':evidence()},
                   {'class_key':'A','reviewed':True,'unit':'shares','outstanding_shares':'300','treasury_shares':'0','issued_shares':'300',
                    'original_line':'Closing balance 2026-09-17 300 0 300','column_basis':'outstanding, treasury, issued','evidence':evidence()}]}


def test_explicit_outstanding_sum_no_double_treasury_subtraction():
    b=bundle();s=normalize(b)
    assert s['ordinary_shares']=='1500' and s['classes']==b['classes']
    assert s['ordinary_shares_verified_through']=='2026-09-17'


@pytest.mark.parametrize('defect',['duplicate','total','negative','fraction','unit','quote','rights','scope','coverage','until'])
def test_share_basis_rejects_wrong_or_unproved_scope(defect):
    b=bundle()
    if defect=='duplicate':b['classes'][1]['class_key']='H'
    if defect=='total':b['classes'][0]['issued_shares']='1,299'
    if defect=='negative':b['classes'][1]['treasury_shares']='-1'
    if defect=='fraction':b['classes'][1].update(outstanding_shares='300.5',issued_shares='300.5')
    if defect=='unit':b['classes'][0]['unit']='yuan'
    if defect=='quote':b['classes'][0]['original_line']='unmatched 100 1,200 1,300'
    if defect=='rights':b['equivalent_share_rights_confirmed']=False
    if defect=='scope':b['complete_classes_confirmed']=False
    if defect=='coverage':b['ordinary_shares_verified_through']='2026-09-30'
    if defect=='until':b['ordinary_shares_valid_until']='2026-09-16T00:00:00+08:00'
    with pytest.raises(FinancialGap):normalize(b)


def scoring_rows():
    b=financial_bundle();b.update(ordinary_shares_verified_through='2026-06-30',share_basis_evidence=evidence(),
        ordinary_shares_valid_until='2026-07-09T00:00:00+08:00',share_change_evidence=evidence())
    f=financials(b);share=normalize(bundle())
    p={'currency':'CNY','session':'2026-09-17','is_final':True,'raw_close':'10','fx_per_cny':'1','evidence':evidence()}
    return f,[SimpleNamespace(id=id,kind=kind,input_key=key,payload_json=canonical(payload)) for id,kind,key,payload in
        [('f','financials','financials',f),('s','share_capital','share_capital:c:2026-09-17',share),('p','price','price:TEST',p)]]


def test_capital_supersedes_expired_report_shares_only_within_verified_day():
    s=SimpleNamespace(id='test',company_id='c',ticker='TEST',market='CN_A',currency='CNY')
    f,rows=scoring_rows();old=deepcopy(f)
    exact=score_security(None,s,'ws',datetime.fromisoformat('2026-09-17T15:00:00+08:00'),input_rows=rows)
    assert Decimal(exact['pe_exact'])==(Decimal('10')/(Decimal(f['ordinary_profit_ttm'])/1500)).quantize(Decimal('0.000000000001'))
    assert exact['share_capital']['input_id']=='s' and exact['basis']['ordinary_shares']=='1500'
    later=score_security(None,s,'ws',datetime.fromisoformat('2026-09-18T00:00:00+08:00'),input_rows=rows)
    assert later['reason']=='SHARE_BASIS_NOT_CURRENT' and later['pe_ttm'] is None
    assert f==old and metrics_from_financials(f)==metrics_from_financials(old)


def test_later_known_change_not_cleared_by_old_independent_balance():
    s=SimpleNamespace(id='test',company_id='c',ticker='TEST',market='CN_A',currency='CNY')
    f,rows=scoring_rows();f['ordinary_shares_valid_until']='2026-09-18T00:00:00+08:00';rows[0].payload_json=canonical(f)
    capital=__import__('json').loads(rows[1].payload_json);capital['ordinary_shares_verified_through']='2026-09-30';rows[1].payload_json=canonical(capital)
    value=score_security(None,s,'ws',datetime.fromisoformat('2026-09-18T00:00:00+08:00'),input_rows=rows)
    assert value['reason']=='SHARE_BASIS_EXPIRED' and value['pe_ttm'] is None
