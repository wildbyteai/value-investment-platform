"""Explicit transaction boundary.

Rule for new code (news / strategy zone / monitoring): services only ``add`` and
``flush``; the caller that owns the request or job opens exactly one unit of work::

    with unit_of_work(db):
        service.do_something(db, ...)

Legacy routes still call ``db.commit()`` themselves; they move to this helper as
their layer is migrated (see docs/21-backend-layers.md).
"""
from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def unit_of_work(db):
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
