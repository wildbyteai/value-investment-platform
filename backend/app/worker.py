"""python -m app.worker: bounded polling with durable lease/fencing, no sending."""
import argparse
import time
import uuid
from app.db import SessionLocal
from app.domains.platform.worker_service import claim, complete


def run(once=False):
    owner = 'local-worker-' + str(uuid.uuid4())
    while True:
        with SessionLocal() as db:
            token = claim(db, owner)
            db.commit()
        if token:
            with SessionLocal() as db:
                try:
                    complete(db, token)
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    from app.models.audit import Outbox
                    from sqlalchemy import select
                    row=db.scalar(select(Outbox).where(Outbox.id==token['id']).with_for_update())
                    if row and row.generation==token['fence'] and row.lease_owner==token['owner']:
                        row.last_error=type(exc).__name__
                        db.commit()
        if once:
            return
        if not token:
            time.sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    run(parser.parse_args().once)
