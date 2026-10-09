"""R10a 资讯→公司匹配：名称与证券代码归一化（ADR 0016，docs/24 §3）。纯函数，不连数据库。"""
import json
from pathlib import Path

import pytest

from app.domains.news.matching.normalize import (
    MARKETS, alias_norm, find_tickers, normalize_name, normalize_ticker, ticker_market,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('raw, expected', [
    ('百济神州', '百济神州'),
    ('百济神州-B', '百济神州'),
    ('百济神州－Ｂ', '百济神州'),                 # full-width dash and letter (NFKC)
    ('英矽智能-W', '英矽智能'),
    ('某某科技-U', '某某科技'),
    ('小米集团-W', '小米'),
    ('信达生物制药（苏州）有限公司', '信达生物制药'),   # trailing bracket dropped first, then suffix
    ('翰森制药集团有限公司', '翰森制药'),
    ('中国生物制药有限公司', '中国生物制药'),
    ('上海某某医药股份有限公司', '上海某某医药'),
    ('诺诚健华（688428.SH / 09969.HK）', '诺诚健华'),
    ('诺诚健华(09969)', '诺诚健华'),
    ('BeOne Medicines Ltd.', 'beone medicines'),
    ('BeOne  Medicines,  Inc.', 'beone medicines'),
    ('Sino Biopharmaceutical Limited', 'sino biopharmaceutical'),
    ('Hansoh Pharmaceutical Group Co., Ltd.', 'hansoh pharmaceutical'),
    ('ＩｎｎｏＣａｒｅ　Ｐｈａｒｍａ', 'innocare pharma'),   # full-width letters and ideographic space
    ('  Insilico Medicine  ', 'insilico medicine'),
    ('信达（苏州）生物', '信达生物'),
    ('百济神州 BeOne', '百济神州beone'),
    ('集团', '集团'),                              # never stripped down to nothing
    ('有限公司', '有限公司'),
    ('', ''),
    (None, ''),
])
def test_normalize_name(raw, expected):
    assert normalize_name(raw) == expected


def test_normalize_name_is_idempotent():
    for raw in ('百济神州-B', 'Hansoh Pharmaceutical Group Co., Ltd.', '诺诚健华（688428.SH）', '小米集团-W'):
        once = normalize_name(raw)
        assert normalize_name(once) == once


@pytest.mark.parametrize('raw, hint, expected', [
    ('688428.SH', None, '688428.SH'),
    ('688428.sh', None, '688428.SH'),
    ('SH688428', None, '688428.SH'),
    ('600000.SS', None, '600000.SH'),
    ('688428', None, '688428.SH'),          # bare 6-digit starting 6 → SH
    ('000001', None, '1.SZ'),               # bare 0xxxxx → SZ, zeros stripped
    ('300750', None, '300750.SZ'),
    ('000001.SZ', None, '1.SZ'),
    ('SZ000001', None, '1.SZ'),
    ('830799', None, '830799.BJ'),
    ('920118.BJ', None, '920118.BJ'),
    ('09969.HK', None, '9969.HK'),          # HK leading zeros
    ('9969.HK', None, '9969.HK'),
    ('HK09969', None, '9969.HK'),
    ('09969', None, '9969.HK'),             # bare 5-digit → HK
    ('0700', None, '700.HK'),               # bare 4-digit → HK
    ('0700 HK', None, '700.HK'),
    ('HKEX:06160', None, '6160.HK'),
    ('06160.HK', None, '6160.HK'),
    ('０６１６０．ＨＫ', None, '6160.HK'),     # full width
    ('ONC', None, 'ONC.US'),
    ('onc', None, 'ONC.US'),
    ('ONC.US', None, 'ONC.US'),
    ('ONC.O', None, 'ONC.US'),
    ('NASDAQ:ONC', None, 'ONC.US'),
    ('NASDAQ: ONC', None, 'ONC.US'),
    ('BRK.B', None, 'BRK.B.US'),
    ('0001.HK', None, '1.HK'),
    ('600001', 'CN_A', '600001.SH'),        # security.market CN_A → digits decide
    ('0001', 'HK', '1.HK'),
    ('1801', 'HK', '1801.HK'),
    ('ONC', 'US', 'ONC.US'),
    ('', None, None),
    (None, None, None),
    ('HK', None, None),
    ('12', None, None),                      # too short to tell the market
    ('1234567', None, None),
    ('ABCDEFG', None, None),
    ('ONC.HK', None, None),                  # letters only exist on the US market here
    ('688428.US', None, None),
    ('诺诚健华', None, None),
])
def test_normalize_ticker(raw, hint, expected):
    assert normalize_ticker(raw, hint) == expected


def test_same_listing_written_differently_is_equal():
    forms = ['09969.HK', '9969.HK', 'HK09969', '09969', 'HKEX:09969', '０９９６９．ＨＫ']
    assert {normalize_ticker(f) for f in forms} == {'9969.HK'}
    assert {normalize_ticker(f) for f in ('688235.SH', 'SH688235', '688235', '688235.SS')} == {'688235.SH'}


def test_ticker_market():
    assert ticker_market('9969.HK') == 'HK' and ticker_market('ONC.US') == 'US'
    assert ticker_market('BRK.B.US') == 'US'
    assert ticker_market(None) is None and ticker_market('ONC') is None and ticker_market('1.XX') is None
    assert set(MARKETS) == {'SH', 'SZ', 'BJ', 'HK', 'US'}


def test_find_tickers_in_text():
    text = ('诺诚健华（688428.SH / 09969.HK）公布奥布替尼数据；百济神州 BeOne（NASDAQ: ONC，06160.HK）'
            '与英矽智能 HK03696 合作。2026.10 年报 共 12000 例，ORR 45.5%。腾讯 0700.HK')
    assert find_tickers(text) == ['688428.SH', '9969.HK', 'ONC.US', '6160.HK', '3696.HK', '700.HK']
    assert find_tickers('试验入组 300 例，市值 1200 亿，日期 20261009') == []   # bare numbers are not tickers
    assert find_tickers(None) == []


def test_alias_norm_by_kind():
    assert alias_norm('百济神州-B', 'name') == '百济神州'
    assert alias_norm('BeOne Medicines', 'en') == 'beone medicines'
    assert alias_norm('06160.HK', 'ticker') == '6160.HK'
    assert alias_norm('ONC', 'ticker', 'US') == 'ONC.US'
    assert alias_norm('有限公司', 'short') == '有限公司'
    assert alias_norm('   ', 'short') is None
    assert alias_norm('not a ticker', 'ticker') is None
    with pytest.raises(ValueError):
        alias_norm('x', 'nickname')


def test_seed_aliases_config_normalizes_cleanly():
    cfg = json.loads((ROOT / 'config/company-aliases-v1.json').read_text(encoding='utf-8'))
    names = [c['name'] for c in cfg['companies']]
    assert names == ['诺诚健华', '百济神州', '英矽智能', '信达生物', '劲方医药', '中国生物制药', '翰森制药']
    seen = {}
    for c in cfg['companies']:
        norms = [alias_norm(c['name'], 'name')]
        for a in c['aliases']:
            n = alias_norm(a['alias'], a['kind'], a.get('market'))
            assert n, a
            if a['kind'] == 'ticker':
                assert ticker_market(n) == a['market'], a
            norms.append(n)
        assert len(norms) == len(set(norms)), c['name']        # no duplicate within a company
        for n in norms:
            assert seen.setdefault(n, c['name']) == c['name'], n  # no alias shared by two companies
    expected = {'百济神州': {'ONC.US', 'BGNE.US', '6160.HK', '688235.SH', 'beone', 'beone medicines', 'beigene'},
                '英矽智能': {'3696.HK', 'insilico'}, '诺诚健华': {'688428.SH', '9969.HK'},
                '信达生物': {'1801.HK'}, '劲方医药': {'2595.HK'}, '中国生物制药': {'1177.HK', '中生制药'},
                '翰森制药': {'3692.HK'}}
    for name, norms in expected.items():
        assert norms <= {n for n, owner in seen.items() if owner == name}, name
