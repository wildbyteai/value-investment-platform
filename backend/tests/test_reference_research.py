"""Reference maths and boundaries; formal flags and decisions are never promoted."""
import copy
import json
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest

from app.services.reference_research import valuation_reference, quality_reference, strategy_reference
from app.services.scoring_service import config
from app.services.strategy_service import gates
from app.services.transactions import digest

AT = datetime(2026, 10, 6, tzinfo=timezone.utc)
SEC = SimpleNamespace(ticker='TEST.HK', currency='HKD')


def row(kind, payload, key=None):
    return SimpleNamespace(id=kind, kind=kind, input_key=key or kind, payload_json=json.dumps(payload), content_hash=digest(payload))


def basis():
    evidence=[{'source_revision_id':'fixed', 'hash':'a'*64, 'locator':'p1'}]
    return [row('financials', {'ordinary_profit_ttm':'1000','ordinary_shares':'100', 'currency':'CNY','scope':'matching_ordinary_equity',
        'equivalent_share_rights':True,'obligation_valid_until':'2027-01-01T00:00:00+00:00',
        'ordinary_shares_verified_through':'2026-06-30','evidence':evidence,
        'lineage':{'facts':[{'key':'ordinary_shares','period_end':'2026-06-30'}, {'key':'ordinary_profit','period_end':'2026-06-30'}]}}),
        row('price', {'raw_close':'20','currency':'HKD','session':'2026-09-30', 'fx_per_cny':'2',
            'is_final':False,'evidence':evidence}, 'price:TEST.HK')]


def replace(rows, index, **values):
    p=json.loads(rows[index].payload_json);p.update(values)
    rows[index]=row(rows[index].kind, p, rows[index].input_key)


def test_reference_math_and_historical_share_assumption():
    rows=basis();before=copy.deepcopy([r.payload_json for r in rows])
    result=valuation_reference(SEC, rows, AT, AT)
    assert result['pe_exact']=='1.000000000000' and result['valuation_exact']=='100.000000000000'
    assert result['basis']['shares_as_of']=='2026-06-30'
    assert any('股数未变' in a for a in result['assumptions'])
    assert any('参考日线' in a for a in result['assumptions'])
    assert [r.payload_json for r in rows]==before


def test_legacy_evidence_label_cannot_break_or_prove_reference_basis():
    rows=basis();replace(rows,0,evidence='legacy fixture label')
    result=valuation_reference(SEC,rows,AT,AT)
    assert result['pe_exact'] is None and '财务原文依据不完整' in result['missing_data']


@pytest.mark.parametrize('defect',['fx','currency','rights','negative','expired','nan','zero','fx_day','future_shares','future_profit'])
def test_no_invented_pe_when_basis_invalid(defect):
    rows=basis()
    if defect=='fx': replace(rows,1,fx_per_cny=None)
    if defect=='currency':replace(rows,1,currency='CNY')
    if defect=='rights':replace(rows,0,equivalent_share_rights=False)
    if defect=='negative':replace(rows,0,ordinary_profit_ttm='-1')
    if defect=='expired':replace(rows,0,obligation_valid_until='2026-10-01T00:00:00+00:00')
    if defect=='nan':replace(rows,1,raw_close='NaN')
    if defect=='zero':replace(rows,1,raw_close='0')
    if defect=='fx_day':replace(rows,1,fx_reference={'session':'2026-09-29','evidence':[]})
    if defect.startswith('future_'):
        p=json.loads(rows[0].payload_json)
        p['lineage']['facts'][0 if defect=='future_shares' else 1]['period_end']='2026-10-01'
        replace(rows,0,lineage=p['lineage'])
    result=valuation_reference(SEC,rows,AT,AT)
    assert result['pe_exact'] is None and result['missing_data']
    if defect=='negative':assert result['status']=='NOT_APPLICABLE'


def test_same_day_fx_and_separate_a_h():
    hk=basis();replace(hk,1,fx_per_cny=None)
    fx={'provider':'ecb','pair':'HKD_PER_CNY','evidence':[],
        'rows':[{'session':'2026-09-30','value':'2','method':'cross','components':{'HKD':{'row_index':0},'CNY':{'row_index':1}}}]}
    hk.append(row('fx',fx));h=valuation_reference(SEC,hk,AT,AT)
    assert h['pe_exact']=='1.000000000000' and h['basis']['fx_reference']['session']=='2026-09-30'
    a=basis();replace(a,1,currency='CNY',fx_per_cny='1',raw_close='30');a[1].input_key='price:TEST.SZ'
    assert valuation_reference(SimpleNamespace(ticker='TEST.SZ',currency='CNY'),a,AT,AT)['pe_exact']=='3.000000000000'
    fx['rows'][0]['session']='2026-09-29';hk[-1]=row('fx',fx)
    assert valuation_reference(SEC,hk,AT,AT)['pe_exact'] is None


def test_new_balance_used_and_known_change_marked_without_rewriting_financials():
    rows=basis();replace(rows,0,ordinary_shares_valid_until='2026-07-01T00:00:00+08:00')
    rows.append(row('share_capital', {'ordinary_shares':'200','shares_as_of':'2026-09-17',
        'ordinary_shares_verified_through':'2026-09-17','equivalent_share_rights':True,'evidence':[{'locator':'balance'}]}))
    v=valuation_reference(SEC,rows,AT,AT)
    assert v['pe_exact']=='2.000000000000'
    assert not any('已知结存后' in a for a in v['assumptions'])
    rows.pop();v=valuation_reference(SEC,rows,AT,AT)
    assert any('已知结存后' in a for a in v['assumptions']) and v['pe_exact']=='1.000000000000'


def test_partial_reference_conditions_use_published_threshold_and_leave_formal_unknown():
    rules=config('strategy-standard-v1.json');rules['enter']['all'][0]['value']='75'
    c={'quality_exact':None,'observed_quality':'90','coverage_exact':'0.50','known_dimensions':['profit_quality','financial_resilience'],
        'dimensions':{'profit_quality':{'score':'90'},'financial_resilience':{'score':'90'},'business_model':{'score':None}},
        'metrics':{'roe_ttm':'0.20','cfo_profit_3y':'1','net_debt_ebitda':'1'},'financial_valid':True,
        'as_of':AT.isoformat(),'knowledge_cutoff':AT.isoformat()}
    s={'market':'HK','common_equity':False,'approved_inputs':True,'price_final':False,'valuation_exact':None,'price_lag_sessions':None}
    before=copy.deepcopy((c,s));formal=gates(rules,c,s)
    v=valuation_reference(SEC,basis(),AT,AT)
    ref=strategy_reference(rules,c,s,v,SimpleNamespace(id='published',version=5))
    assert ref['result']=='PARTIAL' and not ref['applied'] and ref['release_version']==5
    assert ref['conditions'][0]['actual']=='90' and ref['conditions'][0]['expected']=='75'
    assert ref['conditions'][2]['result'] is True
    assert '经营依据覆盖不足' in ref['gaps']
    assert quality_reference(c)['score_exact']=='90' and quality_reference(c)['missing_dimensions']==['business_model']
    assert (c,s)==before and gates(rules,c,s)==formal and formal['passes'] is None
    assert strategy_reference(rules,c,s,v)['result']=='NO_RELEASE'
    c['hard_risks']=[{'confirmed':True,'risk_code':'confirmed_fraud','target_kind':'company'}]
    assert strategy_reference(rules,c,s,v,SimpleNamespace(id='published',version=5))['result']=='RISK_EXCLUDED'
