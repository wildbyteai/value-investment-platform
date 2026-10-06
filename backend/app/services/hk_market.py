"""Licensed-provider snapshots -> independent HK reference or FINAL input.

No scraping endpoint is assumed licensed. Registration and capture are explicit.
"""
from datetime import date,datetime
from decimal import Decimal,InvalidOperation
from app.services.transactions import digest

class MarketGap(ValueError):pass

def positive(value):
    try:v=Decimal(value)
    except (InvalidOperation,TypeError):raise MarketGap('价格/汇率不是有效原始数值')
    if not isinstance(value,str) or not v.is_finite() or v<=0:raise MarketGap('价格/汇率必须为正数值字符串')
    return value

def normalize_quote(snapshot,policy):
    if any(not policy.get(k) or policy[k]=='disabled' for k in ('license','fetch','store','analyze')) or policy.get('revoked'):raise MarketGap('行情来源使用范围未确认或已撤销')
    if snapshot.get('ticker') not in ('01211.HK','09969.HK') or snapshot.get('currency')!='HKD' or snapshot.get('adjustment')!='none':raise MarketGap('本切片只接入比亚迪/诺诚健华港股原始未复权HKD日线')
    session=date.fromisoformat(snapshot['session']);observed=datetime.fromisoformat(snapshot['observed_at'])
    if observed.tzinfo is None or observed.date()<session:raise MarketGap('实际取得时点必须明确且不早于交易日')
    refs=snapshot.get('evidence',[])
    if not refs or any(not r.get('locator') or not r.get('source_revision_id') or not r.get('hash') or r.get('synthetic') is not False for r in refs):raise MarketGap('港股报价原文修订/hash/定位不完整')
    kinds=policy.get('approved_final_price_kinds',[])
    final=bool(snapshot.get('finality_confirmed') is True and snapshot.get('price_kind') in kinds and policy.get('finality_basis'))
    result={'ticker':snapshot['ticker'],'currency':'HKD','raw_close':positive(snapshot['raw_close']),
        'session':snapshot['session'],'is_final':final,'price_kind':snapshot.get('price_kind','REFERENCE'),
        'tradestatus':snapshot.get('tradestatus','1'),'evidence':refs,
        'observed_at':snapshot['observed_at'],'lineage':{'snapshot_hash':digest(snapshot),'adjustment':'none'}}
    fx=snapshot.get('fx')
    if fx:
        if fx.get('pair')!='HKD_PER_CNY' or fx.get('session')!=snapshot['session'] or not fx.get('evidence') or any(not r.get('source_revision_id') or not r.get('hash') or not r.get('locator') or r.get('synthetic') is not False for r in fx.get('evidence',[])):raise MarketGap('港股汇率需要同交易日、明确HKD/CNY方向和独立证据')
        result['fx_per_cny']=positive(fx['value']);result['fx_evidence']=fx['evidence'];result['evidence']=refs+fx['evidence']
    # Missing FX stays missing; no assumed HKD=CNY conversion.
    return result
