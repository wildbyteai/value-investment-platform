"""Original-unit/period semantics, no provider ratios or guessed finality."""
import uuid
from decimal import Decimal
from copy import deepcopy
import pytest
from app.services.original_financials import normalize,FinancialGap
from app.services.hk_market import normalize_quote,MarketGap
from app.services.scoring_service import metrics_from_financials

def evidence():return [{'synthetic':False,'source_revision_id':str(uuid.uuid4()),'hash':'a'*64,'locator':'reviewed original fixture page 1 table A'}]

def bundle():
    b={'annual_periods':['2023-12-31','2024-12-31','2025-12-31'],'current_period_end':'2026-06-30','comparable_period_end':'2025-06-30',
       'ordinary_profit_basis_confirmed':True,'equivalent_share_rights_confirmed':True,'obligation_valid_until':'2026-10-31T00:00:00+08:00',
       'report_obligation_evidence':evidence(),'facts':[]}
    for key in ('ordinary_profit','ebit','interest_expense','depreciation_amortization'):
        for end,value in [('2025-12-31','100'),('2026-06-30','80'),('2025-06-30','50')]:
            b['facts'].append({'key':key,'period_start':end[:4]+'-01-01','period_end':end,'currency':'CNY','statement_scope':'consolidated','equity_basis':'parent_ordinary','reviewed':True,'unit':'thousand_yuan','original_value':value,'evidence':evidence()})
    for end in b['annual_periods']:
        for key,value in [('cfo','150'),('consolidated_profit','100')]:
            b['facts'].append({'key':key,'period_start':end[:4]+'-01-01','period_end':end,'currency':'CNY','statement_scope':'consolidated','reviewed':True,'unit':'thousand_yuan','original_value':value,'evidence':evidence()})
    for key,end,value in [('ordinary_equity','2026-06-30','1100'),('ordinary_equity','2025-06-30','900'),('debt','2026-06-30','100'),('cash','2026-06-30','50'),('ordinary_shares','2026-06-30','1000')]:
        b['facts'].append({'key':key,'period_start':None,'period_end':end,'currency':'CNY','statement_scope':'consolidated','equity_basis':'parent_ordinary','reviewed':True,'unit':'shares' if key=='ordinary_shares' else 'thousand_yuan','original_value':value,'evidence':evidence()})
    return b

def test_three_year_ttm_unit_equity_and_full_lineage():
    b=bundle();f=normalize(b);m=metrics_from_financials(f)
    assert f['ordinary_profit_ttm']=='130000' and f['average_ordinary_equity']=='1000000'
    assert f['ebitda_ttm']=='260000' and f['ordinary_shares']=='1000'
    assert m['roe_ttm']==Decimal('0.13') and m['cfo_profit_3y']==Decimal('1.5')
    assert len(f['lineage']['facts'])==23 and len(f['evidence'])==24

@pytest.mark.parametrize('change',[lambda b:b['facts'].pop(),lambda b:b['facts'].append(deepcopy(b['facts'][0])),
    lambda b:b['facts'][0].update(statement_scope='parent_only'),lambda b:b['facts'][0].update(unit='ratio'),
    lambda b:b.update(annual_periods=['2023-12-31']*3),lambda b:b.update(comparable_period_end='2025-09-30'),
    lambda b:b.update(equivalent_share_rights_confirmed=False),lambda b:b['facts'][0].update(original_value='NaN'),
    lambda b:b['facts'][0].update(evidence=[]),lambda b:b['facts'][0].update(equity_basis='nci_included')])
def test_original_gaps_never_filled(change):
    b=bundle();change(b)
    with pytest.raises(FinancialGap):normalize(b)

def quote():return {'ticker':'01211.HK','currency':'HKD','adjustment':'none','session':'2026-10-05',
    'observed_at':'2026-10-05T17:00:00+08:00','raw_close':'100.25','price_kind':'CAS','finality_confirmed':True,'evidence':evidence()}

def policy():return {'license':'original fixture policy','fetch':'approved API','store':'local only','analyze':'local','approved_final_price_kinds':['CAS'],'finality_basis':'published CAS definition'}

def test_hk_reference_finality_and_independent_fx():
    q=quote();p=policy();p.pop('finality_basis')
    assert normalize_quote(q,p)['is_final'] is False
    r=normalize_quote(q,policy());assert r['is_final'] is True and 'fx_per_cny' not in r
    q['fx']={'pair':'HKD_PER_CNY','session':q['session'],'value':'1.09','evidence':evidence()}
    assert normalize_quote(q,policy())['fx_per_cny']=='1.09'
    q['fx']['pair']='CNY_PER_HKD'
    with pytest.raises(MarketGap):normalize_quote(q,policy())

@pytest.mark.parametrize('change',[lambda q,p:q.update(currency='CNY'),lambda q,p:q.update(adjustment='forward'),
    lambda q,p:p.update(revoked=True),lambda q,p:p.update(store=False),lambda q,p:q.update(raw_close='NaN'),
    lambda q,p:q.update(evidence=[])])
def test_hk_wrong_basis_or_rights_rejected(change):
    q=quote();p=policy();change(q,p)
    with pytest.raises(MarketGap):normalize_quote(q,p)


def test_reviewed_components_keep_originals_and_do_not_use_claimed_result():
    b=bundle();row=b['facts'][0];first=deepcopy(row)
    first.update(key='parent_profit',coefficient=1)
    adjustment=deepcopy(first);adjustment.update(key='preferred_distribution',original_value='10',coefficient=-1)
    row.pop('original_value');row['derivation']={'method':'reviewed_signed_sum_v1','basis':'Original synthetic ordinary allocation note','components':[first,adjustment]}
    f=normalize(b)
    assert f['ordinary_profit_ttm']=='120000'
    assert f['lineage']['facts'][0]['derivation']['components'][0]['original_value']=='100'
    assert 'original_value' not in f['lineage']['facts'][0]


@pytest.mark.parametrize('defect',['period','currency','duplicate','coefficient','nested','claimed_result','shares'])
def test_component_conversion_rejects_mismatched_or_ambiguous_inputs(defect):
    b=bundle();row=b['facts'][0];c=deepcopy(row);c.update(key='parent_profit',coefficient=1)
    row.pop('original_value');row['derivation']={'method':'reviewed_signed_sum_v1','basis':'Original synthetic reviewed conversion','components':[c]}
    if defect=='period':c['period_end']='2024-12-31'
    if defect=='currency':c['currency']='HKD'
    if defect=='duplicate':row['derivation']['components'].append(deepcopy(c))
    if defect=='coefficient':c['coefficient']=True
    if defect=='nested':c['derivation']=deepcopy(row['derivation'])
    if defect=='claimed_result':row['original_value']='100'
    if defect=='shares':c.update(key='issued_ordinary_shares',unit='shares')
    with pytest.raises(FinancialGap):normalize(b)


def test_known_share_change_expires_only_valuation_at_exact_boundary():
    from types import SimpleNamespace
    from datetime import datetime,timezone,timedelta
    from app.services.scoring_service import score_security
    from app.services.transactions import canonical
    b=bundle();b['ordinary_shares_valid_until']='2026-08-18T00:00:00+08:00';b['share_change_evidence']=evidence()
    f=normalize(b);original_metrics=metrics_from_financials(f)
    s=SimpleNamespace(id='test-security',company_id='test-company',ticker='TEST',market='CN_A',currency='CNY')
    price={'ticker':'TEST','currency':'CNY','session':'2026-08-17','is_final':True,'raw_close':'10','fx_per_cny':'1','evidence':evidence()}
    rows=[SimpleNamespace(id='test-financial',kind='financials',input_key='financials',payload_json=canonical(f)),SimpleNamespace(id='test-price',kind='price',input_key='price:TEST',payload_json=canonical(price))]
    boundary=datetime.fromisoformat(b['ordinary_shares_valid_until'])
    assert score_security(None,s,'test-workspace',boundary-timedelta(microseconds=1),input_rows=rows)['valuation_score'] is not None
    expired=score_security(None,s,'test-workspace',boundary,input_rows=rows)
    assert expired['reason']=='SHARE_BASIS_EXPIRED' and expired['pe_ttm'] is None and not expired['common_equity']
    assert metrics_from_financials(f)==original_metrics


@pytest.mark.parametrize('deadline,refs',[('2026-08-18T00:00:00',True),('2026-06-30T00:00:00+08:00',True),('2026-08-18T00:00:00+08:00',False)])
def test_share_change_requires_original_evidence_and_later_zoned_time(deadline,refs):
    b=bundle();b['ordinary_shares_valid_until']=deadline;b['share_change_evidence']=evidence() if refs else []
    with pytest.raises(FinancialGap):normalize(b)
