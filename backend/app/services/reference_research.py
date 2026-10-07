"""Read-only reference calculations. Never consumed by the formal seal worker."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.services.scoring_service import calculation, config, dec, numeric, q, linear
from app.services.strategy_service import gates
from app.services.ecb_fx import matching_fx
from app.services import algorithm_versions


def algorithm_basis():
    return {'version': 'reference-research-v1', 'source_hashes': {
        name: algorithm_versions.fingerprint(name)
        for name in ('reference_research.py', 'scoring_service.py', 'strategy_service.py', 'ecb_fx.py')},
        'valuation_config_hash': hashlib.sha256((Path(__file__).resolve().parents[3] / 'config/scoring-standard-v1.json').read_bytes()).hexdigest()}


def evidence(payload):
    # Legacy synthetic inputs stored a text label instead of structured refs.
    value = payload.get('evidence')
    return [r for r in value if isinstance(r, dict)] if isinstance(value, list) else []


def quality_reference(company):
    return {'score_exact': company['observed_quality'], 'coverage_exact': company['coverage_exact'],
        'known_dimensions': company['known_dimensions'],
        'missing_dimensions': [d for d, value in company['dimensions'].items() if value['score'] is None],
        'partial': company['quality_exact'] is None, 'as_of': company['as_of'],
        'knowledge_cutoff': company['knowledge_cutoff'],
        'meaning': '仅已覆盖维度按模板权重归一；未覆盖维度未计分，不能代表完整经营质量。'}


@calculation
def valuation_reference(security, rows, as_of, cutoff):
    """Rows must already pass workspace, source-rights and bitemporal checks."""
    selected = [(row, json.loads(row.payload_json)) for row in rows]
    financial_row, financial = next(((r, p) for r, p in selected if r.kind == 'financials'), (None, None))
    price_row, price = next(((r, p) for r, p in selected if r.input_key == 'price:' + security.ticker), (None, None))
    result = {'pe_exact': None, 'valuation_exact': None, 'status': 'MISSING_DATA',
        'as_of': as_of.isoformat(), 'knowledge_cutoff': cutoff.isoformat(),
        'basis': None, 'assumptions': [], 'missing_data': [], 'input_refs': []}
    gaps = result['missing_data']
    if not financial: gaps.append('缺少可追溯的普通股TTM财务口径')
    if not price: gaps.append('缺少本证券价格')
    if gaps: return result
    # Choose a capital balance at or before the quote date, never a later balance.
    report_day = max((f['period_end'] for f in financial.get('lineage', {}).get('facts', [])
        if f['key'] == 'ordinary_shares'), default=None)
    capital = [(r, p) for r, p in selected if r.kind == 'share_capital'
        and p['shares_as_of'] <= price['session'] and (not report_day or p['shares_as_of'] >= report_day)]
    share_row, shares = max(capital, key=lambda pair: (pair[1]['shares_as_of'], pair[0].id)) if capital else (financial_row, financial)
    share_day = shares.get('shares_as_of', report_day)
    if share_day and share_day > price['session']: gaps.append('股本结存日晚于价格日期，不能用于该日参考估值')
    profit_day = max((f['period_end'] for f in financial.get('lineage', {}).get('facts', [])
        if f['key'] == 'ordinary_profit'), default=None)
    if profit_day and profit_day > price['session']: gaps.append('利润期间晚于价格日期，不能用于该日参考估值')
    fx_ref = price.get('fx_reference')
    fx_row = None
    if security.currency == 'HKD' and not price.get('fx_per_cny'):
        fx_row, fx_ref = matching_fx(rows, price['session'])
        if fx_ref: price = {**price, 'fx_per_cny': fx_ref['value']}
    if price.get('currency') != security.currency: gaps.append('价格币种与本证券不符')
    if financial.get('currency') != 'CNY' or financial.get('scope') != 'matching_ordinary_equity':
        gaps.append('财务币种或普通股权益口径未确认')
    if security.currency not in ('CNY', 'HKD'): gaps.append('尚未支持该币种的参考换算')
    if not evidence(price): gaps.append('价格原文依据不完整')
    if not evidence(financial): gaps.append('财务原文依据不完整')
    if not shares.get('equivalent_share_rights') or not evidence(shares): gaps.append('同权普通股范围或原文依据未确认')
    if as_of >= datetime.fromisoformat(financial['obligation_valid_until']): gaps.append('财务报告已超过有效期限')
    values = [price.get('raw_close'), financial.get('ordinary_profit_ttm'), shares.get('ordinary_shares'), price.get('fx_per_cny')]
    if values[1] is not None and dec(values[1]).is_finite() and dec(values[1]) <= 0:
        result['status'] = 'NOT_APPLICABLE'
        gaps.append('普通股TTM利润非正，PE估值不适用；需适合该企业的估值方法')
    if any(v is None or not dec(v).is_finite() or dec(v) <= 0 for v in values):
        gaps.append('价格、利润、股数及同日汇率必须是有效正数')
    if security.currency == 'CNY' and price.get('fx_per_cny') is not None and dec(price['fx_per_cny']) != 1:
        gaps.append('人民币证券的换算率应为1')
    if fx_ref and fx_ref.get('session') != price['session']: gaps.append('参考汇率日期与价格日期不一致')
    # Retain rejected basis and dates so the user can understand a missing result.
    result['basis'] = {'price_session': price['session'], 'raw_close': price.get('raw_close'),
        'currency': security.currency, 'ordinary_profit_ttm': financial.get('ordinary_profit_ttm'),
        'profit_period_end': profit_day, 'ordinary_shares': shares.get('ordinary_shares'),
        'shares_as_of': share_day, 'shares_verified_through': shares.get('ordinary_shares_verified_through'),
        'shares_valid_until': shares.get('ordinary_shares_valid_until'), 'fx_per_cny': price.get('fx_per_cny'),
        'fx_reference': fx_ref, 'evidence': evidence(financial) + evidence(shares) + evidence(price) + evidence(fx_ref or {})}
    result['input_refs'] = [{'id': r.id, 'hash': r.content_hash} for r in (financial_row, share_row, price_row, fx_row) if r]
    assumptions = result['assumptions']
    if not price.get('is_final'): assumptions.append('使用未核验正式最终性的参考日线价格，不作为正式策略用价')
    if price['session'] != as_of.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat(): assumptions.append('价格为所列交易日的历史参考价，不代表当前实时价格')
    through = shares.get('ordinary_shares_verified_through')
    if not through or price['session'] > through:
        assumptions.append('假设所列股本结存日至价格日期股数未变；覆盖期外未经确认')
    deadlines = [p.get('ordinary_shares_valid_until') for p in (financial, shares) if p.get('ordinary_shares_valid_until')]
    if any((not share_day or share_day < datetime.fromisoformat(day).date().isoformat())
           and price['session'] >= datetime.fromisoformat(day).date().isoformat() for day in deadlines):
        assumptions.append('已知结存后存在股数变动，此处仍按历史结存情景计算，不能视为该日实际PE')
    if fx_ref: assumptions.append('使用价格同日参考汇率；不代表香港收盘时点汇率')
    if gaps: return result
    eps = q(dec(financial['ordinary_profit_ttm']) / dec(shares['ordinary_shares']))
    converted = q(eps * dec(price['fx_per_cny']))
    if converted <= 0:
        gaps.append('换算EPS低于数值精度，无法计算PE'); return result
    pe = q(dec(price['raw_close']) / converted)
    policy = config('scoring-standard-v1.json')['valuation']
    result.update(pe_exact=numeric(pe), valuation_exact=numeric(linear(pe, policy['zero_score_at'], policy['full_score_at'])),
        status='REFERENCE', basis={**result['basis'], 'eps': numeric(eps), 'converted_eps': numeric(converted)})
    return result


def strategy_reference(rules, company, security, valuation, release=None):
    # Reuse the exact published comparison logic, never override formal price/rights flags.
    observed = {**company, 'quality_exact': company['observed_quality']}
    compared = gates(rules, observed, {**security, 'valuation_exact': valuation['valuation_exact']})
    conditions = [{**c, 'basis': 'covered_dimensions' if c['field'] == 'company.quality_score'
        else 'reference_valuation' if c['field'] == 'security.valuation_score' else 'verified_input'} for c in compared['conditions']]
    # Remove only final-market requirements; all evidence, coverage, binding and risk gates remain visible.
    evidence_gaps = [g for g in compared['gaps'] if g not in (
        '正式收盘价或对应交易日未核验', '币种、股本或财务估值口径未满足', '普通股权利范围未确认')]
    evidence_gaps += valuation['missing_data']
    if not release: evidence_gaps.append('尚无已发布策略，不能给出发布规则结论')
    result = 'PARTIAL' if evidence_gaps or any(c['result'] is None for c in conditions) else 'NO_MATCH' if any(c['result'] is False for c in conditions) else 'MATCH'
    result = {'risk_excluded': 'RISK_EXCLUDED', 'not_applicable': 'NOT_APPLICABLE', 'suspended': 'SUSPENDED'}.get(compared['status'], result)
    if not release: result = 'NO_RELEASE'
    return {'result': result, 'conditions': conditions, 'gaps': list(dict.fromkeys(evidence_gaps)),
        'risks': compared.get('risks', []), 'assumptions': valuation['assumptions'],
        'release_id': release.id if release else None, 'release_version': release.version if release else None,
        'applied': False, 'meaning': '逐项参考比较，不代表正式入选；覆盖不足时仅展示已可计算的条件。'}
