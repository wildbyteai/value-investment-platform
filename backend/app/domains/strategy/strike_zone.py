"""击球区 (strike zone) classification.

A ball (a security at a moment, possibly hit by an event) is judged on three things:

1. 能力圈 circle of competence: company/industry on the whitelist and the evidence
   coverage high enough that we actually understand it.
2. 好生意 good business: the strategy's own quality gates pass (everything except the
   valuation and coverage gates, which belong to 3 and 1) and there is no confirmed hard risk. Hard risk vetoes everything.
3. 安全边际 margin of safety: ``1 - pe_ttm / fair_pe_ttm`` (config). If P/E is missing,
   the published valuation score is used as a proxy.

Result: ``sweet`` (甜区, act), ``edge`` (边角球, watch) or ``outside`` (区外, record only).
Pure function: no database, no clock, so it is trivially testable. All numbers come
from config/strike-zone-v1.json.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[4] / 'config' / 'strike-zone-v1.json'

SWEET, EDGE, OUTSIDE = 'sweet', 'edge', 'outside'
LABELS = {SWEET: '甜区', EDGE: '边角球', OUTSIDE: '区外'}


@lru_cache
def policy() -> dict:
    return json.loads(CONFIG.read_text(encoding='utf-8'))


@dataclass
class Check:
    key: str
    label: str
    passed: bool | None  # None = not enough evidence yet
    detail: str

    def as_dict(self):
        return {'key': self.key, 'label': self.label, 'passed': self.passed, 'detail': self.detail}


@dataclass
class Zone:
    zone: str
    checks: list[Check] = field(default_factory=list)
    margin_of_safety: str | None = None

    @property
    def label(self):
        return LABELS[self.zone]

    def as_dict(self):
        return {'zone': self.zone, 'label': self.label, 'margin_of_safety': self.margin_of_safety,
                'checks': [c.as_dict() for c in self.checks]}


def _dec(value):
    return None if value is None else Decimal(str(value))


def circle(company: dict, cfg: dict) -> Check:
    c = cfg['circle_of_competence']
    on_list = ((not c['industry_keys'] and not c['company_ids'])
               or company.get('industry_key') in c['industry_keys']
               or company.get('company_id') in c['company_ids'])
    if not on_list:
        return Check('circle', '能力圈', False, '不在能力圈白名单内')
    coverage = _dec(company.get('coverage_exact'))
    minimum = Decimal(c['minimum_coverage'])
    if coverage is None:
        return Check('circle', '能力圈', None, '经营依据覆盖度未知')
    if coverage < minimum:
        return Check('circle', '能力圈', False, f'依据覆盖度 {coverage:.2f} 低于 {minimum}')
    return Check('circle', '能力圈', True, f'在白名单内，覆盖度 {coverage:.2f}')


def good_business(gate_result: dict, cfg: dict) -> Check:
    if gate_result.get('status') == 'risk_excluded':
        codes = '、'.join(r.get('risk_code', '') for r in gate_result.get('risks', []))
        return Check('business', '好生意', False, f'硬风险一票否决：{codes}')
    if gate_result.get('status') == 'not_applicable':
        return Check('business', '好生意', False, '不属于策略适用范围')
    ignore = set(cfg['good_business']['ignore_fields'])
    conditions = [r for r in gate_result.get('conditions', []) if r['field'] not in ignore]
    failed = [r['field'] for r in conditions if r['result'] is False]
    if failed:
        return Check('business', '好生意', False, '未达门槛：' + '、'.join(failed))
    unknown = [r['field'] for r in conditions if r['result'] is None]
    gaps = [g for g in gate_result.get('gaps', []) if '估值' not in g and '收盘价' not in g]
    if unknown or gaps:
        return Check('business', '好生意', None, '依据不全：' + '、'.join(unknown + gaps))
    return Check('business', '好生意', True, '经营与财务门槛全部达标，无硬风险')


def margin_of_safety(security: dict, cfg: dict) -> tuple[Check, Decimal | None]:
    m = cfg['margin_of_safety']
    sweet, edge = Decimal(m['sweet_minimum']), Decimal(m['edge_minimum'])
    pe = _dec(security.get('pe_exact') if security.get('pe_exact') is not None else security.get('pe_ttm'))
    if pe is not None and pe > 0:
        margin = (1 - pe / Decimal(m['fair_pe_ttm'])).quantize(Decimal('0.0001'))
        passed = True if margin >= sweet else None if margin >= edge else False
        return Check('margin', '安全边际', passed,
                     f'P/E {pe.quantize(Decimal("0.01"))}，合理 P/E {m["fair_pe_ttm"]}，安全边际 {margin:.0%}，要求 ≥{sweet:.0%}'), margin
    score = _dec(security.get('valuation_exact') if security.get('valuation_exact') is not None else security.get('valuation_score'))
    if score is not None:
        minimum = Decimal(m['valuation_score_proxy_minimum'])
        return Check('margin', '安全边际', True if score >= minimum else None,
                     f'暂无 P/E，以估值分 {score} 代理（要求 ≥{minimum}）'), None
    return Check('margin', '安全边际', None, '缺少估值依据'), None


def classify(company: dict, security: dict, gate_result: dict, cfg: dict | None = None) -> Zone:
    cfg = cfg or policy()
    checks = [circle(company, cfg), good_business(gate_result, cfg)]
    margin_check, margin = margin_of_safety(security, cfg)
    checks.append(margin_check)
    margin_text = None if margin is None else str(margin)
    if any(c.passed is False for c in checks):
        return Zone(OUTSIDE, checks, margin_text)
    if all(c.passed is True for c in checks):
        return Zone(SWEET, checks, margin_text)
    return Zone(EDGE, checks, margin_text)
