"""Explicit personal quote-only client. OpenD itself is not quote-only.

No startup fetch, account queries, trade contexts, subscription or pagination.
SDK decoded rows are retained, not represented as original network bytes.
"""
import json
import socket
import errno
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path
from zoneinfo import ZoneInfo
from sqlalchemy import select, text, func
from app.models.company import Company, Security, ItemCompanyLink
from app.models.intake import InformationItem, SourceRegistry
from app.models.runtime import ResearchInput, ItemRevision
from app.services import data_mode
from app.services.eodhd_source import SourceError, number, save_snapshot
from app.services.hk_market import normalize_quote
from app.services.item_history import observe
from app.services.transactions import canonical, digest, record

ROOT = Path(__file__).resolve().parents[3]
SDK_VERSION = '10.11.7108'
ISSUERS = {'01211.HK': ('比亚迪股份有限公司', ('比亚迪', 'BYD')),
           '09969.HK': ('诺诚健华医药有限公司', ('诺诚健华', 'INNOCARE'))}
REQUEST = {'ktype': 'K_DAY', 'autype': 'NONE', 'max_count': 40,
           'page_req_key': None, 'extended_time': False}


def connection_ready():
    try:
        with socket.create_connection(('127.0.0.1', 11111), timeout=1):
            return True
    except OSError as error:
        if error.errno in (errno.EPERM, errno.EACCES):
            raise SourceError('FUTU_LOCAL_SOCKET_CHECK_NOT_PERMITTED') from None
        return False


def validate_rights(rights):
    # This validates a locally reviewed receipt, not a legal interpretation.
    if (rights.get('provider') != 'futu' or rights.get('reviewed') is not True
        or any(rights.get(k) is not True for k in ('fetch', 'store', 'analyze'))
        or rights.get('export') is not False or rights.get('external_model') is not False
        or rights.get('use') != 'local_personal_research'
        or not all(isinstance(rights.get(k), str) and 0 < len(rights[k]) <= 2000
                   for k in ('agreement', 'clause_locator', 'permitted_scope'))):
        raise SourceError('FUTU_PERSONAL_DATA_RIGHTS_NOT_RECORDED')
    at = datetime.fromisoformat(rights['reviewed_at'])
    if at.tzinfo is None or at > datetime.now(timezone.utc):
        raise SourceError('FUTU_RIGHTS_CLOCK_INVALID')
    return {'license': 'Futu-account-agreement-personal-only',
            'basis': rights['agreement'], 'rights_receipt_sha256': digest(rights),
            'fetch': 'explicit two authorized HK securities, 30 calendar days, no polling',
            'store': 'local personal research only', 'analyze': 'local personal deterministic research only',
            'export': 'disabled', 'external_model': False,
            'approved_final_price_kinds': [], 'finality_basis': None}


def identity(rows, ticker):
    if not isinstance(rows, list) or len(rows) != 1:
        raise SourceError('FUTU_IDENTITY_ROW_COUNT')
    row = rows[0]
    if (row.get('code') != 'HK.' + ticker[:5] or row.get('stock_type') != 'STOCK'
        or row.get('exchange_type') != 'HK_MAINBOARD' or row.get('delisting') is not False
        or not isinstance(row.get('stock_id'), str) or not row['stock_id'].isdigit()
        or int(row['stock_id']) <= 0
        or not any(name in row.get('name', '').upper() for name in ISSUERS[ticker][1])):
        raise SourceError('FUTU_ISSUER_IDENTITY_NOT_CONFIRMED')
    return row


def window(start, end, observed):
    # Last completed calendar day avoids treating today's open bar as a close.
    if (observed.tzinfo is None or observed > datetime.now(timezone.utc) + timedelta(seconds=1)
        or not 0 <= (end - start).days <= 29
        or end >= observed.astimezone(ZoneInfo('Asia/Hong_Kong')).date()):
        raise SourceError('FUTU_INVALID_WINDOW_OR_CLOCK')


def validate(snapshot):
    ticker = snapshot.get('ticker')
    if (snapshot.get('provider') != 'futu' or ticker not in ISSUERS
        or snapshot.get('sdk_version') != SDK_VERSION or snapshot.get('request') != REQUEST
        or snapshot.get('representation') != 'sdk_decoded_rows'
        or snapshot.get('next_page_present') is not False):
        raise SourceError('FUTU_SOURCE_OR_UNADJUSTED_REQUEST_MISMATCH')
    validate_rights(snapshot['rights'])
    observed = datetime.fromisoformat(snapshot['observed_at'])
    start, end = date.fromisoformat(snapshot['start']), date.fromisoformat(snapshot['end'])
    window(start, end, observed)
    for key in ('identity_rows', 'bars_rows'):
        if (not isinstance(snapshot[key], list) or len(canonical(snapshot[key]).encode()) > 100_000
            or digest(snapshot[key]) != snapshot[key + '_sha256']):
            raise SourceError('FUTU_DECODED_ROWS_HASH_MISMATCH')
    identity(snapshot['identity_rows'], ticker)
    rows = snapshot['bars_rows']
    if not 1 <= len(rows) <= 30:
        raise SourceError('FUTU_BAR_ROW_COUNT')
    result, seen = [], set()
    for index, row in enumerate(rows):
        if row.get('code') != 'HK.' + ticker[:5]:
            raise SourceError('FUTU_BAR_CODE_MISMATCH')
        timestamp = datetime.fromisoformat(row['time_key'])
        day = timestamp.date()
        if (timestamp.tzinfo is not None or timestamp.time().isoformat() != '00:00:00'
            or not start <= day <= end or day in seen):
            raise SourceError('FUTU_DUPLICATE_OR_OUT_OF_WINDOW')
        seen.add(day)
        values = {k: number(row[k], k != 'volume') for k in ('open', 'high', 'low', 'close', 'volume')}
        if (Decimal(values['high']) < max(Decimal(values['open']), Decimal(values['close']), Decimal(values['low']))
            or Decimal(values['low']) > min(Decimal(values['open']), Decimal(values['close']))
            or Decimal(values['volume']) != Decimal(values['volume']).to_integral_value()):
            raise SourceError('FUTU_INCONSISTENT_BAR')
        result.append({'date': day.isoformat(), **values, 'row_index': index})
    return sorted(result, key=lambda row: row['date'])


def decoded_rows(frame, fields):
    rows = frame.to_dict(orient='records')
    # Convert only explicit scalar columns. No private gateway/account state.
    return [{k: (bool(row[k]) if k == 'delisting' else str(row[k])) for k in fields} for row in rows]


def capture(start, end, rights):
    validate_rights(rights)
    window(start, end, datetime.now(timezone.utc))
    if not connection_ready():
        raise SourceError('FUTU_OPEND_NOT_LISTENING_127_0_0_1_11111')
    try:
        installed_version = version('futu-api')
    except Exception:
        raise SourceError('FUTU_OPTIONAL_SDK_NOT_INSTALLED') from None
    if installed_version != SDK_VERSION:
        raise SourceError('FUTU_SDK_VERSION_MISMATCH')
    # Import is deliberately lazy: normal application startup never loads SDK.
    try:
        from futu import OpenQuoteContext, Market, SecurityType, KLType, AuType, KL_FIELD, RET_OK
        from futu.common.ft_logger import logger
        import logging
        logger.enable_console_log(False)
        logger.file_level = logging.CRITICAL
    except Exception:
        raise SourceError('FUTU_SDK_INITIALIZATION_FAILED') from None
    context = None
    snapshots = []
    try:
        context = OpenQuoteContext(host='127.0.0.1', port=11111, is_async_connect=True)
        context.set_sync_query_connect_timeout(5)
        codes = ['HK.' + ticker[:5] for ticker in ISSUERS]
        ret, frame = context.get_stock_basicinfo(Market.HK, stock_type=SecurityType.STOCK, code_list=codes)
        if ret != RET_OK:
            raise SourceError('FUTU_BASICINFO_FAILED_CHECK_LOCAL_LOGIN_AND_PERMISSIONS')
        infos = decoded_rows(frame, ('code', 'name', 'stock_type', 'exchange_type', 'delisting', 'stock_id'))
        if len(infos) != 2 or {r['code'] for r in infos} != set(codes):
            raise SourceError('FUTU_IDENTITY_ROW_COUNT')
        # Validate both identities before requesting either history.
        for ticker in ISSUERS:
            identity([r for r in infos if r['code'] == 'HK.' + ticker[:5]], ticker)
        for ticker in ISSUERS:
            code = 'HK.' + ticker[:5]
            ret, bars, next_key = context.request_history_kline(
                code, start=start.isoformat(), end=end.isoformat(), ktype=KLType.K_DAY,
                autype=AuType.NONE, max_count=40, page_req_key=None, extended_time=False,
                fields=[KL_FIELD.DATE_TIME, KL_FIELD.OPEN, KL_FIELD.HIGH, KL_FIELD.LOW, KL_FIELD.CLOSE, KL_FIELD.VOLUME])
            if ret != RET_OK:
                raise SourceError('FUTU_HISTORY_FAILED_CHECK_LOCAL_PERMISSIONS_OR_QUOTA')
            if next_key is not None:
                raise SourceError('FUTU_UNEXPECTED_PAGINATION_STOPPED')
            info_rows = [r for r in infos if r['code'] == code]
            bar_rows = decoded_rows(bars, ('code', 'time_key', 'open', 'high', 'low', 'close', 'volume'))
            snapshot = {'provider': 'futu', 'ticker': ticker, 'sdk_version': SDK_VERSION,
                        'representation': 'sdk_decoded_rows', 'request': REQUEST.copy(),
                        'start': start.isoformat(), 'end': end.isoformat(), 'rights': rights,
                        'observed_at': datetime.now(timezone.utc).isoformat(), 'next_page_present': False,
                        'identity_rows': info_rows, 'bars_rows': bar_rows,
                        'identity_rows_sha256': digest(info_rows), 'bars_rows_sha256': digest(bar_rows)}
            validate(snapshot)
            snapshots.append(snapshot)
    except SourceError:
        raise
    except Exception:
        raise SourceError('FUTU_QUOTE_CAPTURE_FAILED') from None
    finally:
        if context is not None:
            context.close()
    # Save only after both bounded requests pass. No currency is inferred.
    return [(save_snapshot(s, ROOT / 'raw-data/futu'), s) for s in snapshots]


def currency_evidence(db, workspace, company_id, ticker, basis):
    if (basis.get('ticker') != ticker or basis.get('currency') != 'HKD' or basis.get('reviewed') is not True
        or not basis.get('excerpt') or len(basis['excerpt']) > 3000
        or not data_mode.real_evidence(db, basis.get('evidence'), workspace, company_id)):
        raise SourceError('FUTU_INDEPENDENT_QUOTE_CURRENCY_EVIDENCE_REQUIRED')
    # Review binds the denomination claim to a verbatim readable source passage.
    if not any(basis['excerpt'] in json.loads(db.get(ItemRevision, ref['source_revision_id']).payload_json).get('readable_text', '')
               for ref in basis['evidence']):
        raise SourceError('FUTU_CURRENCY_PASSAGE_NOT_IN_SOURCE')
    return basis['evidence']


def import_snapshot(db, workspace_id, snapshot, basis):
    actual = db.execute(text('SELECT current_database(), inet_server_addr()::text')).one()
    if (actual[0] != 'vip_v0001_local' and not (actual[0] == 'vip_v0001_test' and data_mode.fixture_mode())) or actual[1] not in ('127.0.0.1/32', '::1/128'):
        raise SourceError('FUTU_UNAPPROVED_DATABASE')
    rows = validate(snapshot)
    ticker = snapshot['ticker']
    security = db.scalar(select(Security).where(Security.ticker == ticker))
    company = db.get(Company, security.company_id) if security else None
    if (not company or company.name != ISSUERS[ticker][0] or security.currency != 'HKD' or security.market != 'HK'):
        raise SourceError('FUTU_REGISTERED_IDENTITY_MISMATCH')
    data_mode.require_company(db, company.id, workspace_id)
    currency_refs = currency_evidence(db, workspace_id, company.id, ticker, basis)
    policy = validate_rights(snapshot['rights'])
    key = 'futu-personal-hk'
    db.execute(select(func.pg_advisory_xact_lock(int(digest({'source': key})[:15], 16))))
    source = db.scalar(select(SourceRegistry).where(SourceRegistry.source_key == key))
    if source and json.loads(source.policy_json) != policy:
        raise SourceError('FUTU_SOURCE_POLICY_CHANGED_OR_REVOKED')
    if not source:
        source = SourceRegistry(source_key=key, name='富途 OpenAPI｜本机个人用途', policy_json=canonical(policy))
        db.add(source); db.flush()
    entry = ticker + ':' + snapshot['start'] + ':' + snapshot['end']
    item = db.scalar(select(InformationItem).where(InformationItem.workspace_id == workspace_id, InformationItem.source_id == source.id, InformationItem.entry_key == entry).with_for_update())
    if not item:
        item = InformationItem(workspace_id=workspace_id, source_id=source.id, entry_key=entry, title=company.name + '｜真实港股日线', content_kind='dataset')
        db.add(item); db.flush()
    item.summary_text = f'{len(rows)}条富途未复权日线；参考价，限本机个人研究。'
    item.body_state = 'available'; item.body_url = None
    item.publication_json = canonical({'date': None, 'precision': 'unknown', 'meaning': '按实际取得时点可知；不回填供应商发布时间'})
    item.reading_metadata_json = canonical({'data_mode': 'real_public', 'material_type': 'market_daily', 'license': policy['license'], 'attribution': 'Futu OpenAPI', 'source_observed_at': snapshot['observed_at']})
    retained = {k: v for k, v in snapshot.items() if k != 'observed_at'}
    readable = 'date,open,high,low,close,volume\n' + '\n'.join(','.join(r[k] for k in ('date', 'open', 'high', 'low', 'close', 'volume')) for r in rows)
    rev = observe(db, item, {'readable_text': readable, 'raw_capture': retained, 'source_policy': policy})
    if not db.scalar(select(ItemCompanyLink.id).where(ItemCompanyLink.item_id == item.id, ItemCompanyLink.company_id == company.id)):
        db.add(ItemCompanyLink(item_id=item.id, company_id=company.id, status='accepted', label_text=company.name, relevance=1, confidence=1)); db.flush()
    latest = rows[-1]
    ref = {'synthetic': False, 'source_revision_id': rev.id, 'hash': rev.content_hash, 'item_id': item.id, 'locator': f"raw_capture.bars_rows[{latest['row_index']}].close"}
    quote = {'ticker': ticker, 'currency': 'HKD', 'adjustment': 'none', 'session': latest['date'], 'observed_at': snapshot['observed_at'], 'raw_close': latest['close'], 'price_kind': 'provider_daily_bar_close', 'finality_confirmed': False, 'evidence': [ref] + currency_refs}
    payload = normalize_quote(quote, policy)
    payload.pop('observed_at'); payload['lineage'].pop('snapshot_hash')
    payload['lineage'].update(provider='futu', sdk_version=SDK_VERSION, representation='sdk_decoded_rows', raw_sha256=snapshot['bars_rows_sha256'], currency_basis_hash=digest(basis))
    payload['finality_reason'] = 'FINAL_CLOSE_POLICY_NOT_VERIFIED'
    sha = digest(payload)
    old = db.scalar(select(ResearchInput).where(ResearchInput.workspace_id == workspace_id, ResearchInput.input_key == 'price:' + ticker, ResearchInput.content_hash == sha))
    reused = old is not None
    if not old:
        old = ResearchInput(workspace_id=workspace_id, company_id=company.id, input_key='price:' + ticker, kind='price', payload_json=canonical(payload), content_hash=sha, effective_at=datetime.fromisoformat(latest['date'] + 'T00:00:00+08:00'), published_at=datetime.fromisoformat(snapshot['observed_at']), synthetic=False)
        db.add(old); db.flush()
        record(db, workspace_id, None, 'research.futu_imported', 'research_input', old.id, {'hash': sha, 'rows': len(rows), 'final': False})
    return {'ticker': ticker, 'input_id': old.id, 'item_id': item.id, 'revision_id': rev.id, 'rows': len(rows), 'last_session': latest['date'], 'price_final': False, 'reused': reused, 'hash': sha}
