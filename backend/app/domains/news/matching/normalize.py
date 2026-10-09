"""Normalization of company names and tickers for news→company matching (ADR 0016, docs/24 §3).

Pure functions, no database, no LLM. Stage 2 (``resolve.py``) compares ``news_mention.name_norm`` /
``ticker_norm`` with ``company_alias.alias_norm``; both sides MUST be produced by this module so the
comparison is exact. Changing a rule here changes what matches: bump ``NORM_VERSION`` and run a
re-match (job kind ``rematch``) after the alias table has been re-normalized.

Name rules (``normalize_name``)
  1. NFKC (full-width → half-width letters/digits/brackets), then lower-case.
  2. Drop bracketed qualifiers: ``诺诚健华（688428.SH）`` → ``诺诚健华``, ``信达生物制药（苏州）有限公司`` →
     ``信达生物制药有限公司``.
  3. Drop punctuation ``. , ' " · • 、 ( ) [ ] 【 】`` and collapse whitespace to one space; no space
     is kept next to a CJK character (``信达 生物`` → ``信达生物``).
  4. Strip listing / legal-form suffixes repeatedly (``-b``, ``-w``, ``-sw``, ``-u``, ``股份有限公司``,
     ``有限责任公司``, ``有限公司``, ``集团``, ``inc``, ``ltd``, ``co``, ``corp`` …), never down to empty.

Ticker rules (``normalize_ticker``) produce ``CODE.MARKET`` with MARKET in SH SZ BJ HK US:
  * suffix or prefix forms: ``688428.SH`` ``SH688428`` ``600000.SS`` ``09969.HK`` ``HK09969``
    ``HKEX:06160`` ``NASDAQ:ONC`` ``ONC.US`` ``ONC.O``;
  * a bare number gets its market from its shape (before zeros are stripped): 4–5 digits → HK,
    6 digits starting 6 or 9 → SH, 0/2/3 → SZ, 4/8 (and 92) → BJ;
  * leading zeros are stripped from numeric codes: ``09969.HK`` → ``9969.HK``,
    ``000001.SZ`` → ``1.SZ`` (the market keeps the code unique);
  * bare letters (1–5, optionally ``.X`` class) → US; anything else → ``None`` (not a ticker).
"""
from __future__ import annotations

import re
import unicodedata

NORM_VERSION = 'norm:v1'

MARKETS = ('SH', 'SZ', 'BJ', 'HK', 'US')

# Exchange spellings seen in news text and data vendors → our five markets.
MARKET_ALIASES = {
    'SH': 'SH', 'SS': 'SH', 'SHA': 'SH', 'SSE': 'SH', 'SHSE': 'SH', 'XSHG': 'SH',
    'SZ': 'SZ', 'SZA': 'SZ', 'SZSE': 'SZ', 'SHE': 'SZ', 'XSHE': 'SZ',
    'BJ': 'BJ', 'BSE': 'BJ', 'BJSE': 'BJ',
    'HK': 'HK', 'HKG': 'HK', 'HKEX': 'HK', 'SEHK': 'HK', 'XHKG': 'HK',
    'US': 'US', 'O': 'US', 'N': 'US', 'OQ': 'US', 'NASDAQ': 'US', 'NYSE': 'US', 'AMEX': 'US', 'XNAS': 'US', 'XNYS': 'US',
}
# security.market values used by the company tables (CN_A is resolved from the digits).
SECURITY_MARKETS = {'CN_A': None, 'A': None, 'HK': 'HK', 'US': 'US', 'SH': 'SH', 'SZ': 'SZ', 'BJ': 'BJ'}

# Longest first; matched at the end of the (already lower-cased, punctuation-free) name.
NAME_SUFFIXES = (
    '股份有限公司', '有限责任公司', '集团股份有限公司', '集团有限公司', '有限公司', '股份公司', '集团公司', '集团',
    '-sw', '-b', '-w', '-u',
    ' incorporated', ' corporation', ' company', ' limited', ' holdings', ' holding', ' group',
    ' inc', ' ltd', ' co', ' corp', ' plc', ' ag', ' sa', ' se', ' nv', ' llc',
)
_PUNCT = re.compile(r"[.,'\"·•、()\[\]【】<>《》:;!?，。；：！？“”‘’]")
_BRACKET = re.compile(r'\s*[(\[【][^()\[\]【】]*[)\]】]\s*')
_SPACES = re.compile(r'\s+')
_CJK_SPACE = re.compile(r'(?<=[\u3400-\u9fff])\s+|\s+(?=[\u3400-\u9fff])')


def nfkc(text: str | None) -> str:
    return unicodedata.normalize('NFKC', text or '')


def normalize_name(name: str | None) -> str:
    """Normalized company name for exact comparison; ``''`` for blank input."""
    s = nfkc(name).strip().lower()
    while True:  # 诺诚健华（688428.SH / 09969.HK） → 诺诚健华；信达生物制药（苏州）有限公司 → 信达生物制药有限公司
        stripped = _BRACKET.sub(' ', s).strip()
        if stripped == s or not stripped:
            break
        s = stripped
    s = _CJK_SPACE.sub('', _SPACES.sub(' ', _PUNCT.sub(' ', s))).strip()
    changed = True
    while changed:
        changed = False
        for suffix in NAME_SUFFIXES:
            if s.endswith(suffix) and len(s) > len(suffix):
                s = s[:-len(suffix)].rstrip(' -')
                changed = True
                break
    return s


def _bare_number_market(digits: str) -> str | None:
    if len(digits) in (4, 5):
        return 'HK'
    if len(digits) == 6:
        if digits.startswith('92') or digits[0] in '48':
            return 'BJ'
        if digits[0] in '69':
            return 'SH'
        if digits[0] in '023':
            return 'SZ'
    return None


def _join(code: str, market: str | None) -> str | None:
    if market is None:
        return None
    if code.isdigit():
        if market == 'US':
            return None
        code = code.lstrip('0') or '0'
    elif market != 'US':
        return None  # letters only exist on the US market here
    return f'{code}.{market}'


_SUFFIX = re.compile(r'^(\d{1,6}|[A-Z]{1,6})[.\s:_-]?([A-Z]{1,6})$')
_PREFIX = re.compile(r'^([A-Z]{1,6})[.\s:_-]?(\d{1,6}|[A-Z]{1,6})$')


def normalize_ticker(raw: str | None, market_hint: str | None = None) -> str | None:
    """``CODE.MARKET`` (e.g. ``9969.HK``, ``688428.SH``, ``ONC.US``) or ``None`` if not a ticker.

    ``market_hint`` may be one of our markets, an exchange spelling, or a ``security.market`` value
    (``CN_A`` / ``HK``); it is used only when the text itself carries no market."""
    s = nfkc(raw).strip().upper().replace(' ', '')
    if not s:
        return None
    hint = None
    if market_hint:
        h = nfkc(market_hint).strip().upper()
        hint = SECURITY_MARKETS.get(h, MARKET_ALIASES.get(h))
    if s.isdigit():
        return _join(s, hint or _bare_number_market(s))
    letters = re.fullmatch(r'[A-Z]{1,5}(?:\.([A-Z]))?', s)
    if letters and s not in MARKET_ALIASES and not (letters.group(1) and letters.group(1) in MARKET_ALIASES):
        return _join(s, hint or 'US')
    m = _SUFFIX.match(s)
    if m and m.group(2) in MARKET_ALIASES:
        return _join(m.group(1), MARKET_ALIASES[m.group(2)])
    m = _PREFIX.match(s)
    if m and m.group(1) in MARKET_ALIASES:
        return _join(m.group(2), MARKET_ALIASES[m.group(1)])
    m = re.fullmatch(r'([A-Z]{1,5}\.[A-Z])\.US', s)  # BRK.B.US
    if m:
        return f'{m.group(1)}.US'
    return None


def ticker_market(ticker_norm: str | None) -> str | None:
    """Market part of a normalized ticker (``9969.HK`` → ``HK``)."""
    if not ticker_norm or '.' not in ticker_norm:
        return None
    market = ticker_norm.rsplit('.', 1)[1]
    return market if market in MARKETS else None


# Tickers written with an explicit market in running text. Bare numbers are not picked up from
# free text (dates, amounts and trial sizes would all look like tickers).
_TEXT_TICKERS = re.compile(
    r'(?<![A-Za-z0-9])(?:'
    r'(?P<code>\d{4,6})\.(?P<sfx>SH|SZ|BJ|HK|SS)'
    r'|(?P<pfx>SH|SZ|BJ|HK)(?P<code2>\d{4,6})'
    r'|(?P<ex>NASDAQ|NYSE|HKEX|SEHK|SSE|SZSE)\s*[:：]\s*(?P<code3>[A-Z]{1,5}|\d{4,6})'
    r'|(?P<us>[A-Z]{1,5})\.(?:US|O|N|OQ)'
    r')(?![A-Za-z0-9])')


def find_tickers(text: str | None) -> list[str]:
    """Normalized tickers that appear in ``text`` with an explicit market, in order, no repeats."""
    out: list[str] = []
    for m in _TEXT_TICKERS.finditer(nfkc(text).upper()):
        if m.group('code'):
            t = normalize_ticker(f"{m.group('code')}.{m.group('sfx')}")
        elif m.group('code2'):
            t = normalize_ticker(f"{m.group('pfx')}{m.group('code2')}")
        elif m.group('code3'):
            t = normalize_ticker(f"{m.group('ex')}:{m.group('code3')}")
        else:
            t = normalize_ticker(f"{m.group('us')}.US")
        if t and t not in out:
            out.append(t)
    return out


ALIAS_KINDS = ('name', 'short', 'en', 'former', 'ticker')


def alias_norm(alias: str, kind: str, market: str | None = None) -> str | None:
    """``company_alias.alias_norm`` for one alias: tickers via ``normalize_ticker``, everything
    else via ``normalize_name``. ``None`` when the alias normalizes to nothing usable."""
    if kind not in ALIAS_KINDS:
        raise ValueError(f'unknown alias kind: {kind}')
    if kind == 'ticker':
        return normalize_ticker(alias, market)
    return normalize_name(alias) or None
