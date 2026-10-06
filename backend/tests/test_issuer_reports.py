"""Original synthetic excerpts, never copied issuer values or source PDFs."""
from copy import deepcopy
from datetime import datetime,timezone
import pytest
from app.services.issuer_reports import validate,analysis

def bundle():
    line='合并净利润 1,234.56 2,345.67'
    return {'ticker':'000651.SZ','issuer':'珠海格力电器股份有限公司','documents':[{
        'key':'fixture-report','url':'https://static.cninfo.com.cn/finalpage/2026-08-01/100.PDF',
        'disclosure_date':'2026-08-01','observed_at':datetime.now(timezone.utc).isoformat(),
        'pdf_sha256':'a'*64,'page_count':2,'money_unit':'yuan','unit_basis_page':1,
        'pages':[{'number':1,'text':'原创合成夹具：珠海格力电器股份有限公司\n合并资产负债表 单位：人民币元\n'+line}]}],
        'facts':[{'key':'consolidated_profit','period_start':'2026-01-01','period_end':'2026-06-30',
            'currency':'CNY','statement_scope':'consolidated','reviewed':True,'unit':'yuan','original_value':'1,234.56',
            'document_key':'fixture-report','page':1,'label':'合并净利润','column_label':'2026年上半年','column_index':0,'original_line':line}],
        'missing_data':['原创合成夹具缺普通股口径']}

def test_original_unit_and_evidence_row_survive():
    b=bundle();validate(b);a=analysis(b,{'item_id':'test','source_revision_id':'test'})
    assert a['periods'][0]['values']['consolidated_profit']=='1234.56'
    assert a['original_statement'] and not a['standard_metrics_eligible']
    assert b['facts'][0]['original_value']=='1,234.56'

@pytest.mark.parametrize('label',['单位:元 币种:人民币','单位:\t人民币元','单位：人民币元'])
def test_explicit_unit_colon_layout_variants(label):
    b=bundle();d=b['documents'][0]
    d['pages'][0]['text']=d['pages'][0]['text'].replace('单位：人民币元',label)
    validate(b)
    d['pages'][0]['text']=d['pages'][0]['text'].replace(label,'单位:万元')
    with pytest.raises(ValueError,match='单位原文'):validate(b)

def test_hk_company_financials_remain_cny_with_separate_security_currency():
    from app.services.issuer_reports import SECURITY_CURRENCIES
    b=bundle();b['ticker']='09969.HK';b['issuer']='诺诚健华医药有限公司'
    b['documents'][0]['pages'][0]['text']=b['documents'][0]['pages'][0]['text'].replace('珠海格力电器股份有限公司',b['issuer'])
    validate(b)
    assert b['facts'][0]['currency']=='CNY' and SECURITY_CURRENCIES[b['ticker']]=='HKD'
    b['issuer']='另一家公司'
    with pytest.raises(ValueError):validate(b)

@pytest.mark.parametrize('defect',['column','row','unit','scope','nan','page','duplicate','unreviewed','host','future','missing_gap'])
def test_misread_or_unreviewed_original_rejected(defect):
    b=deepcopy(bundle());r=b['facts'][0];d=b['documents'][0]
    if defect=='column':r['column_index']=1
    if defect=='row':r['original_line']='合并净利润 9,999.99'
    if defect=='unit':r['unit']='thousand_yuan'
    if defect=='scope':r['statement_scope']='parent_only'
    if defect=='nan':r['original_value']='NaN'
    if defect=='page':r['page']=2
    if defect=='duplicate':b['facts'].append(deepcopy(r))
    if defect=='unreviewed':r['reviewed']=False
    if defect=='host':d['url']='https://other.example/report.PDF'
    if defect=='future':d['observed_at']='2099-01-01T00:00:00+00:00'
    if defect=='missing_gap':b['missing_data']=[]
    with pytest.raises(ValueError):validate(b)

def test_adjacent_pdf_columns_do_not_merge_decimal_digits():
    b=bundle();r=b['facts'][0];old=r['original_line'];new='合并净利润 1,234.562,345.67'
    b['documents'][0]['pages'][0]['text']=b['documents'][0]['pages'][0]['text'].replace(old,new);r['original_line']=new
    validate(b)
    r.update(column_index=1,original_value='2,345.67');validate(b)

def test_small_ungrouped_amount_remains_an_original_column():
    b=bundle();r=b['facts'][0];old=r['original_line'];new='合并净利润 12.34 56.78'
    b['documents'][0]['pages'][0]['text']=b['documents'][0]['pages'][0]['text'].replace(old,new)
    r.update(original_line=new,original_value='12.34',column_tokenization='grouped_or_small_amounts_v1');validate(b)
    r.update(column_index=1,original_value='56.78');validate(b)

def test_grouped_columns_ignore_note_numbers_for_existing_snapshots():
    b=bundle();r=b['facts'][0];old=r['original_line'];new='合并净利润 50 1,234.56 2,345.67'
    b['documents'][0]['pages'][0]['text']=b['documents'][0]['pages'][0]['text'].replace(old,new)
    r['original_line']=new;validate(b)
    r.update(column_index=1,original_value='2,345.67');validate(b)

def test_only_three_matching_complete_annuals_produce_cash_metrics():
    b=bundle();base=b['facts'][0];b['facts']=[]
    for year,profit,cash in [(2023,'1,000.00','2,000.00'),(2024,'2,000.00','0.00'),(2025,'3,000.00','4,000.00')]:
        for key,value in [('consolidated_profit',profit),('cfo',cash)]:
            b['facts'].append({**base,'key':key,'original_value':value,'period_start':f'{year}-01-01','period_end':f'{year}-12-31'})
    a=analysis(b,{'item_id':'test','source_revision_id':'test'})
    assert a['available_metrics']=={'cfo_profit_3y':'1.000000000000','positive_cfo_year_share_3y':'0.666666666667'}
    assert not a['standard_metrics_eligible']
    b['facts'].pop();assert analysis(b,{'item_id':'test','source_revision_id':'test'})['available_metrics']=={}
