"""R1 guardrail: the Alembic chain must build exactly the schema the models declare.

Other modules build their schema with ``Base.metadata.create_all`` for speed, so on
their own they cannot notice a model change that has no migration. This test runs the
real migration chain on the disposable test database and fails on any drift.
"""
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from pathlib import Path
from sqlalchemy import text
import pytest
from app.db import Base, engine
import app.models  # noqa: F401

BACKEND = Path(__file__).resolve().parents[1]


def _reset():
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.execute(text('DROP TABLE IF EXISTS alembic_version'))


@pytest.fixture()
def migrated():
    _reset()
    cfg = Config(str(BACKEND / 'alembic.ini'))
    cfg.set_main_option('script_location', str(BACKEND / 'alembic'))
    command.upgrade(cfg, 'head')
    yield cfg
    _reset()


def test_migration_chain_matches_models(migrated):
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], f'models and migrations drifted; add a migration: {diff}'


def test_migration_chain_installs_knowledge_clock(migrated):
    with engine.connect() as conn:
        functions = set(conn.execute(text(
            "SELECT proname FROM pg_proc WHERE proname IN ('vip_knowledge_now','vip_capture_knowledge','vip_stamp_knowledge')")).scalars())
        triggers = conn.execute(text("SELECT count(*) FROM pg_trigger WHERE tgname IN ('vip_capture','vip_stamp')")).scalar()
    assert functions == {'vip_knowledge_now', 'vip_capture_knowledge', 'vip_stamp_knowledge'}
    assert triggers > 0
