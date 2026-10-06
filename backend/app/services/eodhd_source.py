"""Explicit, bounded personal-use BYD H-share capture. Never log authenticated URLs.

The provider's close is a reference price until a separate final-close policy is
verified. Raw response bytes, adjusted_close and actual observation time survive.
"""
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from zoneinfo import ZoneInfo
from sqlalchemy import select, text, func
from app.config import get_settings
from app.models.company import Company, Security, ItemCompanyLink
from app.models.intake import InformationItem, SourceRegistry
from app.models.runtime import ResearchInput
from app.services.item_history import observe
from app.services.transactions import canonical, digest, record
from app.services.hk_market import normalize_quote

ROOT = Path(__file__).resolve().parents[3]
TICKER = '01211.HK'
POLICY = {
    'license': 'EODHD-personal-use-only',
    'basis': 'https://eodhd.com/financial-apis/terms-conditions',
    'fetch': 'explicit BYD HK identity search and last 30 calendar days EOD, no polling',
    'store': 'local personal research only',
    'analyze': 'account owner personal deterministic investment research only',
    'export': 'disabled', 'external_model': False,
    'approved_final_price_kinds': [],
    'finality_basis': None,
}
FX_POLICY = {
    'license': 'HKMA-attributed-public-information',
    'basis': 'https://www.hkma.gov.hk/eng/other-information/terms-and-conditions.shtml',
    'fetch': 'explicit daily FX API, bounded 40 rows',
    'store': 'local attributed research', 'analyze': 'local accurate deterministic research',
    'export': 'disabled', 'external_model': False,
}
FX_URL = 'https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/er-eeri-daily'


class SourceError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # An API key must never follow redirects to another host.
        return None


def request_json(url, params, token=None, direct=False):
    query = dict(params)
    if token:
        query['api_token'] = token
    try:
        req = Request(url + '?' + urlencode(query), headers={'Accept': 'application/json'})
        handlers=[NoRedirect()]+([ProxyHandler({})] if direct else [])
        with build_opener(*handlers).open(req, timeout=20) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise SourceError('RESPONSE_TOO_LARGE')
        decoded = raw.decode('utf-8')
        if token and token in decoded:
            raise SourceError('RESPONSE_CONTAINS_CREDENTIAL')
        parse_json(decoded)
        return decoded
    except HTTPError as error:
        raise SourceError('PROVIDER_HTTP_' + str(error.code)) from None
    except (URLError, TimeoutError, OSError):
        raise SourceError('PROVIDER_CONNECTION_FAILED') from None
    except (UnicodeError, json.JSONDecodeError):
        raise SourceError('PROVIDER_INVALID_JSON') from None


def parse_json(raw):
    return json.loads(raw, parse_float=str)


def number(value, positive=False):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise SourceError('INVALID_DECIMAL')
    try:
        d = Decimal(value)
    except (InvalidOperation, TypeError):
        raise SourceError('INVALID_DECIMAL') from None
    if not d.is_finite() or d < 0 or (positive and d == 0):
        raise SourceError('INVALID_DECIMAL')
    return str(value)


def identity(raw):
    rows = parse_json(raw)
    if not isinstance(rows, list) or len(rows) > 10:
        raise SourceError('IDENTITY_RESPONSE_SHAPE')
    matches = [r for r in rows if isinstance(r, dict)
               and r.get('Code') in ('1211', '01211') and r.get('Exchange') == 'HK'
               and r.get('Currency') == 'HKD' and r.get('Type') == 'Common Stock'
               and 'BYD' in r.get('Name', '').upper()]
    if len(matches) != 1:
        raise SourceError('BYD_HK_IDENTITY_NOT_CONFIRMED')
    return matches[0]


def validate(snapshot):
    if snapshot.get('provider') != 'eodhd' or snapshot.get('ticker') != TICKER:
        raise SourceError('SOURCE_IDENTITY_MISMATCH')
    issuer = identity(snapshot['identity_raw'])
    if snapshot.get('provider_symbol') != issuer['Code'] + '.HK':
        raise SourceError('PROVIDER_SYMBOL_MISMATCH')
    start = date.fromisoformat(snapshot['start']); end = date.fromisoformat(snapshot['end'])
    observed = datetime.fromisoformat(snapshot['observed_at'])
    if (observed.tzinfo is None or end < start or (end-start).days > 29
        or observed > datetime.now(timezone.utc) + timedelta(seconds=1)
        or end > observed.astimezone(ZoneInfo('Asia/Hong_Kong')).date()):
        raise SourceError('INVALID_WINDOW_OR_CLOCK')
    for key in ('identity_raw', 'bars_raw'):
        if len(snapshot[key].encode()) > 1_000_000 or hashlib.sha256(snapshot[key].encode()).hexdigest() != snapshot[key + '_sha256']:
            raise SourceError('RAW_RESPONSE_HASH_MISMATCH')
    rows = parse_json(snapshot['bars_raw'])
    if not isinstance(rows, list) or not 1 <= len(rows) <= 30:
        raise SourceError('INVALID_ROW_COUNT')
    result = []; seen = set()
    for index, row in enumerate(rows):
        session = date.fromisoformat(row['date'])
        if session in seen or not start <= session <= end:
            raise SourceError('DUPLICATE_OR_OUT_OF_WINDOW')
        seen.add(session)
        values = {k: number(row[k], k != 'volume') for k in ('open', 'high', 'low', 'close', 'adjusted_close', 'volume')}
        if (Decimal(values['high']) < max(Decimal(values['open']), Decimal(values['close']), Decimal(values['low']))
            or Decimal(values['low']) > min(Decimal(values['open']), Decimal(values['close']))):
            raise SourceError('INCONSISTENT_BAR')
        result.append({'date': row['date'], **values, 'row_index': index})
    return sorted(result, key=lambda r: r['date'])


def save_snapshot(snapshot, directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (digest(snapshot) + '.json')
    if not path.exists():
        path.write_text(canonical(snapshot))
    return path


def capture(end=None):
    token = get_settings().eodhd_api_token.get_secret_value().strip()
    if not token or token == 'demo':
        raise SourceError('PERSONAL_EODHD_TOKEN_REQUIRED')
    end = end or datetime.now(ZoneInfo('Asia/Hong_Kong')).date()
    start = end-timedelta(days=29)
    raw_exchanges = request_json('https://eodhd.com/api/exchanges-list', {'fmt': 'json'}, token)
    save_snapshot({'provider': 'eodhd', 'exchanges_raw': raw_exchanges,
                   'observed_at': datetime.now(timezone.utc).isoformat()}, ROOT/'raw-data/eodhd/identity')
    exchanges = parse_json(raw_exchanges)
    if not isinstance(exchanges, list) or not any(isinstance(e, dict) and e.get('Code') == 'HK' for e in exchanges):
        raise SourceError('PROVIDER_HK_EXCHANGE_NOT_SUPPORTED')
    raw_identity = request_json('https://eodhd.com/api/search/1211', {'exchange': 'HK', 'type': 'stock', 'limit': 10, 'fmt': 'json'}, token)
    save_snapshot({'provider': 'eodhd', 'identity_raw': raw_identity,
                   'observed_at': datetime.now(timezone.utc).isoformat()}, ROOT/'raw-data/eodhd/identity')
    selected = identity(raw_identity); symbol = selected['Code'] + '.HK'
    raw_bars = request_json('https://eodhd.com/api/eod/' + symbol, {'from': start.isoformat(), 'to': end.isoformat(), 'period': 'd', 'order': 'a', 'fmt': 'json'}, token)
    snapshot = {'provider': 'eodhd', 'ticker': TICKER, 'provider_symbol': symbol,
                'start': start.isoformat(), 'end': end.isoformat(), 'observed_at': datetime.now(timezone.utc).isoformat(),
                'identity_raw': raw_identity, 'bars_raw': raw_bars,
                'identity_raw_sha256': hashlib.sha256(raw_identity.encode()).hexdigest(),
                'bars_raw_sha256': hashlib.sha256(raw_bars.encode()).hexdigest()}
    validate(snapshot)
    return save_snapshot(snapshot, ROOT/'raw-data/eodhd'), snapshot


def validate_fx(snapshot):
    if snapshot.get('provider') != 'hkma' or snapshot.get('url') != FX_URL:
        raise SourceError('FX_SOURCE_MISMATCH')
    raw = snapshot['raw']; observed = datetime.fromisoformat(snapshot['observed_at'])
    if (observed.tzinfo is None or observed > datetime.now(timezone.utc) + timedelta(seconds=1)
        or len(raw.encode()) > 1_000_000 or hashlib.sha256(raw.encode()).hexdigest() != snapshot['raw_sha256']):
        raise SourceError('FX_HASH_OR_CLOCK_MISMATCH')
    data = parse_json(raw)
    if data.get('header', {}).get('success') is not True:
        raise SourceError('FX_PROVIDER_ERROR')
    rows = data.get('result', {}).get('records', [])
    if not 1 <= len(rows) <= 40:
        raise SourceError('FX_RESPONSE_ROW_BOUND')
    result = {}; current = observed.astimezone(ZoneInfo('Asia/Hong_Kong')).date()
    for index, row in enumerate(rows):
        day = date.fromisoformat(row['end_of_day'])
        if day > current or day.isoformat() in result:
            raise SourceError('FX_DUPLICATE_OR_FUTURE')
        if row.get('cny') is not None:
            result[day.isoformat()] = {'value': number(row['cny'], True), 'row_index': index}
    return result


def capture_fx():
    params={'offset': 0, 'pagesize': 40, 'sortby': 'end_of_day', 'sortorder': 'desc'}
    try:
        raw = request_json(FX_URL, params)
    except SourceError as error:
        # One read-only direct retry for observed proxy transport failures;
        # never retry authentication/permission/rate-limit responses.
        if str(error) not in ('PROVIDER_HTTP_502','PROVIDER_HTTP_503','PROVIDER_CONNECTION_FAILED'):raise
        raw = request_json(FX_URL, params, direct=True)
    snapshot = {'provider': 'hkma', 'url': FX_URL, 'raw': raw, 'raw_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                'observed_at': datetime.now(timezone.utc).isoformat()}
    validate_fx(snapshot)
    return save_snapshot(snapshot, ROOT/'raw-data/hkma'), snapshot


def import_snapshot(db, workspace_id, snapshot, fx_snapshot=None):
    from app.services import data_mode
    actual = db.execute(text('SELECT current_database(), inet_server_addr()::text')).one()
    if actual[0] != 'vip_v0001_local' and not (actual[0] == 'vip_v0001_test' and data_mode.fixture_mode()):
        raise SourceError('UNAPPROVED_DATABASE')
    if actual[1] not in ('127.0.0.1/32', '::1/128'):
        raise SourceError('NONLOCAL_DATABASE')
    rows = validate(snapshot)
    company = db.scalar(select(Company).where(Company.name == '比亚迪股份有限公司'))
    security = db.scalar(select(Security).where(Security.ticker == TICKER))
    if not company or not security or security.company_id != company.id or security.currency != 'HKD' or security.market != 'HK':
        raise SourceError('REGISTERED_IDENTITY_MISMATCH')
    data_mode.require_company(db, company.id, workspace_id)
    db.execute(select(func.pg_advisory_xact_lock(int(digest({'source': 'eodhd-byd-hk'})[:15], 16))))

    def evidence(key, name, policy, entry, title, raw_capture, readable, observed):
        source = db.scalar(select(SourceRegistry).where(SourceRegistry.source_key == key))
        if source and json.loads(source.policy_json) != policy:
            raise SourceError('SOURCE_POLICY_CHANGED_OR_REVOKED')
        if not source:
            source = SourceRegistry(source_key=key, name=name, policy_json=canonical(policy)); db.add(source); db.flush()
        item = db.scalar(select(InformationItem).where(InformationItem.workspace_id == workspace_id, InformationItem.source_id == source.id, InformationItem.entry_key == entry).with_for_update())
        if not item:
            item = InformationItem(workspace_id=workspace_id, source_id=source.id, entry_key=entry, title=title, content_kind='dataset'); db.add(item); db.flush()
        item.summary_text = title + '；原始响应可追溯，仅本机个人研究。'
        item.body_state = 'available'; item.body_url = None
        item.publication_json = canonical({'date': None, 'precision': 'unknown', 'meaning': '系统按实际取得时间可知，不伪造供应商发布时间'})
        item.reading_metadata_json = canonical({'data_mode': 'real_public', 'material_type': 'market_daily' if key.startswith('eodhd') else 'fx_daily', 'license': policy['license'], 'attribution': name, 'source_observed_at': observed})
        rev = observe(db, item, {'readable_text': readable, 'raw_capture': raw_capture, 'source_policy': policy})
        if not db.scalar(select(ItemCompanyLink.id).where(ItemCompanyLink.item_id == item.id, ItemCompanyLink.company_id == company.id)):
            db.add(ItemCompanyLink(item_id=item.id, company_id=company.id, status='accepted', label_text=company.name, relevance=1, confidence=1)); db.flush()
        return {'synthetic': False, 'source_revision_id': rev.id, 'hash': rev.content_hash, 'item_id': item.id, 'locator': 'raw_capture'}

    retained = {k: v for k, v in snapshot.items() if k != 'observed_at'}
    ref = evidence('eodhd-byd-hk', 'EODHD 港股｜个人用途', POLICY,
                   TICKER + ':' + snapshot['start'] + ':' + snapshot['end'], '比亚迪｜真实港股日线', retained,
                   'date,open,high,low,close,adjusted_close,volume\n' + '\n'.join(','.join(r[k] for k in ('date','open','high','low','close','adjusted_close','volume')) for r in rows), snapshot['observed_at'])
    latest = rows[-1]
    quote = {'ticker': TICKER, 'currency': 'HKD', 'adjustment': 'none', 'raw_close': latest['close'],
             'session': latest['date'], 'observed_at': snapshot['observed_at'], 'price_kind': 'provider_daily_bar_close',
             'finality_confirmed': False, 'tradestatus': '1', 'evidence': [{**ref, 'locator': f"raw_capture.bars_raw / array[{latest['row_index']}].close"}]}
    fx_rows = {}
    if fx_snapshot:
        fx_rows = validate_fx(fx_snapshot)
        matching = fx_rows.get(latest['date'])
        # Stale FX remains local raw evidence; it is not imported as today's FX.
        if matching:
            fx_ref = evidence('hkma-daily-fx', '香港金融管理局｜每日汇率', FX_POLICY,
                              'daily:' + snapshot['start'] + ':' + snapshot['end'], '香港金管局｜同日人民币港元汇率',
                              {k: v for k, v in fx_snapshot.items() if k != 'observed_at'}, fx_snapshot['raw'], fx_snapshot['observed_at'])
            quote['fx'] = {'pair': 'HKD_PER_CNY', 'session': latest['date'], 'value': matching['value'],
                           'evidence': [{**fx_ref, 'locator': f"raw_capture.raw / result.records[{matching['row_index']}].cny"}]}
    payload = normalize_quote(quote, POLICY)
    payload['finality_reason'] = 'FINAL_CLOSE_POLICY_NOT_VERIFIED'
    # Hash excludes repeated acquisition time; same raw revision/effect is reused.
    payload.pop('observed_at'); payload['lineage'].pop('snapshot_hash')
    payload['lineage'].update(provider='eodhd', provider_symbol=snapshot['provider_symbol'], raw_sha256=snapshot['bars_raw_sha256'])
    sha = digest(payload)
    old = db.scalar(select(ResearchInput).where(ResearchInput.workspace_id == workspace_id, ResearchInput.input_key == 'price:' + TICKER, ResearchInput.content_hash == sha))
    if not old:
        old = ResearchInput(workspace_id=workspace_id, company_id=company.id, input_key='price:' + TICKER, kind='price', payload_json=canonical(payload), content_hash=sha,
                            effective_at=datetime.fromisoformat(latest['date']+'T00:00:00+08:00'), published_at=datetime.fromisoformat(snapshot['observed_at']), synthetic=False)
        db.add(old); db.flush()
        record(db, workspace_id, None, 'research.eodhd_imported', 'research_input', old.id, {'hash': sha, 'rows': len(rows), 'final': False})
        reused = False
    else:
        reused = True
    return {'input_id': old.id, 'item_id': ref['item_id'], 'revision_id': ref['source_revision_id'], 'rows': len(rows), 'last_session': latest['date'], 'price_final': False,
            'same_day_fx': 'fx' in quote, 'latest_fx_session': max(fx_rows) if fx_rows else None, 'reused': reused, 'hash': sha}
