"""Explicit free-personal EODHD capture/import. No startup/background fetch."""
import argparse
import json
from pathlib import Path
from app.db import SessionLocal
from app.services.eodhd_source import (ROOT, SourceError, capture, capture_fx,
                                      import_snapshot, validate, validate_fx)


def load(filename, directory):
    path = Path(filename).resolve()
    if path.parent != (ROOT/'raw-data'/directory).resolve() or path.stat().st_size > 2_100_000:
        raise SourceError('ONLY_BOUNDED_PROJECT_SNAPSHOT_ALLOWED')
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description='比亚迪H股近30天：默认校验，--capture显式获取，--write真实入库')
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--snapshot')
    fx_options=parser.add_mutually_exclusive_group()
    fx_options.add_argument('--fx-snapshot')
    fx_options.add_argument('--capture-fx', action='store_true')
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    if args.capture == bool(args.snapshot):
        parser.error('选择--capture或--snapshot之一')
    try:
        if args.capture:
            path, snapshot = capture()
        else:
            path = Path(args.snapshot); snapshot = load(args.snapshot, 'eodhd')
        rows = validate(snapshot)
        fx = None
        if args.capture_fx:
            _, fx = capture_fx()
        elif args.fx_snapshot:
            fx = load(args.fx_snapshot, 'hkma'); validate_fx(fx)
        result = {'validated': True, 'written': False, 'rows': len(rows), 'snapshot': str(path), 'price_final': False}
        if args.write:
            with SessionLocal() as db:
                result.update(import_snapshot(db, args.workspace, snapshot, fx)); db.commit()
            result['written'] = True
        print(json.dumps(result, ensure_ascii=False))
    except SourceError as error:
        # All SourceError messages are fixed codes; never emit network exception URLs.
        raise SystemExit(str(error)) from None
    except (KeyError, TypeError, ValueError, OSError):
        raise SystemExit('INVALID_LOCAL_OR_PROVIDER_SNAPSHOT') from None


if __name__ == '__main__':
    main()
