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


def test_0015_model_scenes_up_and_down(migrated):
    """0015 adds llm_scene_binding + encrypted key columns; downgrade drops them (page keys are
    not representable in the old schema) and restores api_key_env NOT NULL."""
    def columns():
        with engine.connect() as conn:
            return set(conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='llm_provider'")).scalars())

    def has_table():
        with engine.connect() as conn:
            return conn.execute(text("SELECT to_regclass('public.llm_scene_binding')")).scalar() is not None

    assert {'api_key_ciphertext', 'api_key_hint'} <= columns() and has_table()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO llm_provider (id, workspace_id, provider_key, name, base_url, model, api_key_env, "
                          "is_default, enabled, options_json, search_mode, api_key_ciphertext, api_key_hint) VALUES "
                          "('p1','w1','qwen','Q','https://x','m',NULL,true,true,'{}','none','v1:abc','abcd')"))
        conn.execute(text("INSERT INTO llm_scene_binding (id, workspace_id, scene_key, provider_id) VALUES ('b1','w1','news_collect','p1')"))
    command.downgrade(migrated, '0014_auth_sessions')
    assert not ({'api_key_ciphertext', 'api_key_hint'} & columns()) and not has_table()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT api_key_env FROM llm_provider WHERE id='p1'")).scalar() == 'VIP_UNSET_API_KEY'
        assert conn.execute(text("SELECT is_nullable FROM information_schema.columns WHERE table_name='llm_provider' "
                                 "AND column_name='api_key_env'")).scalar() == 'NO'
    command.upgrade(migrated, 'head')
    assert {'api_key_ciphertext', 'api_key_hint'} <= columns() and has_table()
