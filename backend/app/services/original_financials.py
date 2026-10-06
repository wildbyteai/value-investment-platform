"""Normalize reviewed original statement facts. Never infer originals from ratios.

Capture/OCR is separate: facts must already carry the original report revision,
page/table locator, scope, currency, unit, and value. Incomplete data stays a gap.
"""
from datetime import date,datetime
from decimal import Decimal,InvalidOperation,localcontext
from app.services.transactions import digest

MONEY_UNITS={'yuan':Decimal(1),'thousand_yuan':Decimal(1000),'ten_thousand_yuan':Decimal(10000),'million_yuan':Decimal(1000000)}
FLOW={'ordinary_profit','consolidated_profit','cfo','ebit','interest_expense','depreciation_amortization'}
STOCK={'ordinary_equity','debt','cash','ordinary_shares'}

class FinancialGap(ValueError):pass

def number(value):
    if not isinstance(value,str):raise FinancialGap('原值必须为字符串，避免浮点精度损失')
    try:v=Decimal(value.replace(',','').replace('，',''))
    except InvalidOperation:raise FinancialGap('原始科目不是有效数值')
    if not v.is_finite():raise FinancialGap('原始科目不是有限数值')
    return v

def fact(row,key,period_start,period_end):
    if row.get('key')!=key or row.get('period_end')!=period_end or row.get('period_start')!=period_start:
        raise FinancialGap('期间/科目不匹配：'+key)
    if row.get('currency')!='CNY' or row.get('statement_scope')!='consolidated':raise FinancialGap('仅支持已核验的合并人民币原始科目：'+key)
    if key in ('ordinary_profit','ordinary_equity','ordinary_shares') and row.get('equity_basis')!='parent_ordinary':raise FinancialGap('归母普通股权益口径未确认：'+key)
    if row.get('reviewed') is not True:raise FinancialGap('原始科目尚未核对：'+key)
    evidence=row.get('evidence',[])
    if not evidence or any(not e.get('source_revision_id') or not e.get('hash') or not e.get('locator') or e.get('synthetic') is not False for e in evidence):raise FinancialGap('原文修订/hash/定位不完整：'+key)
    unit=row.get('unit')
    multiplier=Decimal(1) if key=='ordinary_shares' and unit=='shares' else MONEY_UNITS.get(unit) if key!='ordinary_shares' else None
    if multiplier is None:raise FinancialGap('科目单位不支持：'+key)
    return number(row.get('original_value'))*multiplier,evidence

def normalize(bundle):
    """Three annuals + current/comparable interim; all periods explicit.

    No preference-dividend adjustment, debt netting, or same-rights assumption is
    made silently. The report reviewer must confirm those bases in the bundle.
    """
    with localcontext() as ctx:
        ctx.prec=50
        return _normalize(bundle)

def _normalize(bundle):
    annuals=bundle.get('annual_periods',[])
    if len(annuals)!=3 or len(set(annuals))!=3 or annuals!=sorted(annuals):raise FinancialGap('需要三个独立、连续的年末报告期')
    ends=[date.fromisoformat(v) for v in annuals]
    if any((d.month,d.day)!=(12,31) for d in ends) or [d.year for d in ends]!=list(range(ends[0].year,ends[0].year+3)):raise FinancialGap('三年期间必须连续且同会计年度')
    current=date.fromisoformat(bundle['current_period_end']);prior=date.fromisoformat(bundle['comparable_period_end'])
    if current.year!=ends[-1].year+1 or prior.year!=ends[-1].year or (current.month,current.day)!=(prior.month,prior.day) or current.month not in (3,6,9):raise FinancialGap('TTM中期与同期必须同期间且紧接最近年末')
    if not bundle.get('ordinary_profit_basis_confirmed') or not bundle.get('equivalent_share_rights_confirmed'):raise FinancialGap('普通股利润或等权股本范围未确认')
    until=bundle.get('obligation_valid_until')
    try:deadline=datetime.fromisoformat(until)
    except (ValueError,TypeError):raise FinancialGap('报告义务到期时点缺失或格式错误')
    if deadline.tzinfo is None:raise FinancialGap('报告义务时点必须有时区')
    obligations=bundle.get('report_obligation_evidence',[])
    if not obligations or any(not e.get('source_revision_id') or not e.get('hash') or not e.get('locator') or e.get('synthetic') is not False for e in obligations):raise FinancialGap('报告义务到期依据缺失')
    rows=bundle.get('facts',[]);selected=[];refs=[]
    def get(key,end,start=None):
        matches=[r for r in rows if r.get('key')==key and r.get('period_end')==end and r.get('period_start')==start]
        if len(matches)!=1:raise FinancialGap('缺失或冲突原始科目：'+key+' '+end)
        value,evidence=fact(matches[0],key,start,end);selected.append(matches[0]);refs.extend(evidence);return value
    def flow(key,end):return get(key,end,end[:4]+'-01-01')
    def ttm(key):return flow(key,annuals[-1])+flow(key,current.isoformat())-flow(key,prior.isoformat())
    ordinary_profit=ttm('ordinary_profit');ebit=ttm('ebit');interest=ttm('interest_expense');da=ttm('depreciation_amortization')
    equity=(get('ordinary_equity',current.isoformat())+get('ordinary_equity',prior.isoformat()))/2
    output={'currency':'CNY','scope':'matching_ordinary_equity','ordinary_profit_ttm':str(ordinary_profit),
        'average_ordinary_equity':str(equity),'annual_periods':annuals,
        'consolidated_cfo_3y':[str(flow('cfo',end)) for end in annuals],
        'consolidated_profit_3y':[str(flow('consolidated_profit',end)) for end in annuals],
        'debt':str(get('debt',current.isoformat())),'cash':str(get('cash',current.isoformat())),
        'ebit_ttm':str(ebit),'ebitda_ttm':str(ebit+da),'interest_expense_ttm':str(interest),
        'ordinary_shares':str(get('ordinary_shares',current.isoformat())),'equivalent_share_rights':True,
        'obligation_valid_until':until,'evidence':[],
        'lineage':{'method':'annual_plus_current_minus_comparable_v1','facts':selected,'bundle_hash':digest(bundle)}}
    refs.extend(bundle['report_obligation_evidence'])
    unique={digest(ref):ref for ref in refs};output['evidence']=list(unique.values())
    return output
