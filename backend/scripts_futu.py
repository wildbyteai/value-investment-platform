"""Bounded manual capture/replay. No credentials in arguments or output."""
import argparse
import json
from datetime import date
from pathlib import Path
from app.services.futu_source import (ROOT, SourceError, connection_ready, capture,
                                      validate, import_snapshot)


def load(filename, directory):
    path = Path(filename).resolve()
    root = (ROOT / directory).resolve()
    if not path.is_relative_to(root) or path.stat().st_size > 200_000:
        raise SourceError('FUTU_BOUNDED_PROJECT_FILE_REQUIRED')
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description='富途两只港股，只读行情；正常启动不采集')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--capture', action='store_true')
    group.add_argument('--snapshot', action='append')
    parser.add_argument('--start', type=date.fromisoformat)
    parser.add_argument('--end', type=date.fromisoformat)
    parser.add_argument('--rights', help='本机已阅读API协议的个人保存分析范围记录，不含账号/密码')
    parser.add_argument('--currency-basis', help='已入库原文修订的独立币种依据JSON数组')
    parser.add_argument('--workspace')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    if args.check:
        if args.write:
            parser.error('--check不写库')
        try:
            listening = connection_ready()
        except SourceError as error:
            raise SystemExit(str(error)) from None
        print(json.dumps({'listening': listening, 'host': '127.0.0.1', 'port': 11111,
                          'authenticated': 'not_checked', 'quote_permissions': 'not_checked'}))
        return
    try:
        if args.capture:
            if not args.start or not args.end or not args.rights:
                parser.error('--capture需--start、--end、--rights')
            pairs = capture(args.start, args.end, load(args.rights, 'local-data/futu'))
        else:
            if not 1 <= len(args.snapshot) <= 2:
                parser.error('--snapshot最多两份')
            pairs = [(Path(p), load(p, 'raw-data/futu')) for p in args.snapshot]
        if len({s['ticker'] for _, s in pairs}) != len(pairs):
            raise SourceError('FUTU_DUPLICATE_SECURITY_SNAPSHOT')
        result = {'written': False, 'validated': True, 'price_final': False,
                  'snapshots': [{'path': str(p), 'ticker': s['ticker'], 'rows': len(validate(s)),
                                 'last_session': validate(s)[-1]['date']} for p, s in pairs]}
        if args.write:
            if not args.workspace or not args.currency_basis:
                parser.error('--write需--workspace和--currency-basis')
            bases = load(args.currency_basis, 'local-data/futu')
            if not isinstance(bases, list) or not 1 <= len(bases) <= 2 or len({b['ticker'] for b in bases}) != len(bases):
                raise SourceError('FUTU_CURRENCY_BASIS_BOUND')
            by_ticker = {b['ticker']: b for b in bases}
            from app.db import SessionLocal
            with SessionLocal() as db:
                result['inputs'] = [import_snapshot(db, args.workspace, s, by_ticker.get(s['ticker'], {})) for _, s in pairs]
                db.commit()
            result['written'] = True
        print(json.dumps(result, ensure_ascii=False))
    except SourceError as error:
        raise SystemExit(str(error)) from None
    except (KeyError, ValueError, TypeError, OSError):
        raise SystemExit('FUTU_INVALID_LOCAL_OR_PROVIDER_SNAPSHOT') from None


if __name__ == '__main__':
    main()
