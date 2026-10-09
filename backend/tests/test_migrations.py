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


def test_0016_news_company_matching_data_migration(migrated):
    """0016: existing companies become an active watchlist of every workspace that uses the news radar,
    aliases are seeded (name + tickers + config/company-aliases-v1.json), extract_status mirrors
    ai_status, the news_analysis binding moves to news_extract; downgrade reverses it."""
    def tables():
        with engine.connect() as conn:
            return {t for t in ('watch_company', 'company_alias', 'news_mention', 'match_job')
                    if conn.execute(text(f"SELECT to_regclass('public.{t}')")).scalar() is not None}

    assert tables() == {'watch_company', 'company_alias', 'news_mention', 'match_job'}
    command.downgrade(migrated, '0015_model_scenes_keys')
    assert tables() == set()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO workspace (id, name) VALUES ('w-news','有资讯'), ('w-idle','空闲'), ('w-coll','有采集')"))
        conn.execute(text("INSERT INTO company (id, name, industry_key) VALUES ('c-bg','百济神州-B','biotech'), "
                          "('c-in','诺诚健华','biotech'), ('c-x','合成甲制造','manufacturing')"))
        conn.execute(text("INSERT INTO security (id, company_id, market, ticker, currency) VALUES "
                          "('s1','c-bg','HK','06160.HK','HKD'), ('s2','c-in','CN_A','688428.SH','CNY'), "
                          "('s3','c-x','CN_A','600001','CNY')"))
        conn.execute(text("INSERT INTO news_event (id, workspace_id, title, summary, fingerprint, item_count, ai_status) VALUES "
                          "('e1','w-news','t','', 't', 1, 'scored'), ('e2','w-news','u','', 'u', 1, 'rule_only'), "
                          "('e3','w-news','v','', 'v', 1, 'pending')"))
        conn.execute(text("INSERT INTO news_feed (id, workspace_id, feed_key, name, kind, enabled, config_json) VALUES "
                          "('f1','w-coll','agent-1','A','agent',true,'{}')"))
        conn.execute(text("INSERT INTO collector_task (id, workspace_id, name, prompt, feed_id, schedule_json, enabled) VALUES "
                          "('t1','w-coll','A','p','f1','{}',true)"))
        conn.execute(text("INSERT INTO llm_provider (id, workspace_id, provider_key, name, base_url, model, api_key_env, "
                          "is_default, enabled, options_json, search_mode) VALUES "
                          "('p1','w-news','deepseek','D','https://api.deepseek.com','deepseek-flash','K',true,true,'{}','none')"))
        conn.execute(text("INSERT INTO llm_scene_binding (id, workspace_id, scene_key, provider_id) VALUES "
                          "('b1','w-news','news_analysis','p1')"))
    command.upgrade(migrated, '0016_news_company_matching')
    with engine.connect() as conn:
        watch = set(conn.execute(text("SELECT workspace_id, company_id, status FROM watch_company")).all())
        aliases = {(r[0], r[1]): (r[2], r[3], r[4]) for r in conn.execute(text(
            "SELECT company_id, alias_norm, kind, market, source FROM company_alias")).all()}
        status = dict(conn.execute(text("SELECT id, extract_status FROM news_event")).all())
        scene = conn.execute(text("SELECT scene_key, reasoning_effort FROM llm_scene_binding WHERE id='b1'")).one()
        task = conn.execute(text("SELECT scope_kind, target_company_ids, industry FROM collector_task WHERE id='t1'")).one()
    assert watch == {(ws, c, 'active') for ws in ('w-news', 'w-coll') for c in ('c-bg', 'c-in', 'c-x')}
    assert aliases[('c-bg', '百济神州')] == ('name', None, 'seed')          # '百济神州-B' normalized
    assert aliases[('c-bg', '6160.HK')] == ('ticker', 'HK', 'seed')
    assert aliases[('c-bg', 'ONC.US')] == ('ticker', 'US', 'seed')          # from the seed config
    assert {('c-bg', 'beone medicines'), ('c-bg', 'beigene'), ('c-in', '9969.HK'), ('c-in', 'innocare pharma'),
            ('c-in', '688428.SH'), ('c-x', '600001.SH'), ('c-x', '合成甲制造')} <= set(aliases)
    assert not any(c == 'c-x' and n == 'beone' for c, n in aliases)
    assert status == {'e1': 'done', 'e2': 'rule_only', 'e3': 'pending'}
    assert tuple(scene) == ('news_extract', None)
    assert tuple(task) == ('general', '[]', None)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO llm_scene_binding (id, workspace_id, scene_key, provider_id, reasoning_effort) "
                          "VALUES ('b2','w-news','zone_review','p1','max')"))
    command.downgrade(migrated, '0015_model_scenes_keys')
    with engine.connect() as conn:
        assert dict(conn.execute(text("SELECT id, scene_key FROM llm_scene_binding")).all()) == {'b1': 'news_analysis'}
    assert tables() == set()
    command.upgrade(migrated, 'head')
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []
