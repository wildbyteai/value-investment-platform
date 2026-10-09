"""news→company matching foundation: watchlist, aliases, mentions, match jobs (ADR 0016)

Schema
  * new tables watch_company, company_alias, news_mention, match_job
  * news_event_company + mention_id, match_method, rule_version
  * news_event + extract_status, extract_version, extracted_at
  * collector_task + scope_kind, target_company_ids, industry
  * llm_scene_binding + reasoning_effort

Data (behaviour preserved)
  * every existing company becomes an active watch_company in every workspace that has news_event
    or collector_task rows (or, when there is none, the oldest workspace) — matching used to look at
    all companies, so the watchlist starts as "all companies";
  * company_alias seeded from company.name, every security.ticker and config/company-aliases-v1.json;
  * news_event.extract_status mirrors ai_status (scored → done);
  * llm_scene_binding scene 'news_analysis' → 'news_extract' (the scene was renamed; the old key stays
    an alias in config/model-scenes-v1.json).

Downgrade drops the new tables/columns (watchlist, aliases, mentions and jobs are lost) and renames
the scene binding back; bindings of scenes the old code does not know are deleted.

Revision ID: 0016_news_company_matching
Revises: 0015_model_scenes_keys
"""
import json
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0016_news_company_matching'
down_revision: Union[str, Sequence[str], None] = '0015_model_scenes_keys'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_SCENES = ('news_reassess', 'company_digest', 'zone_review')


def upgrade() -> None:
    op.create_table('watch_company',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('company_id', sa.String(length=36), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
    sa.Column('note', sa.Text(), server_default='', nullable=False),
    sa.Column('added_by', sa.String(length=36), nullable=True),
    sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('workspace_id', 'company_id', name='uq_watch_company')
    )
    op.create_index(op.f('ix_watch_company_workspace_id'), 'watch_company', ['workspace_id'], unique=False)
    op.create_table('company_alias',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('company_id', sa.String(length=36), nullable=False),
    sa.Column('alias', sa.String(length=200), nullable=False),
    sa.Column('alias_norm', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('market', sa.String(length=10), nullable=True),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('company_id', 'alias_norm', name='uq_company_alias_norm')
    )
    op.create_index('ix_company_alias_alias_norm', 'company_alias', ['alias_norm'], unique=False)
    op.create_table('news_mention',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('event_id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('name_norm', sa.String(length=200), nullable=False),
    sa.Column('ticker_raw', sa.String(length=60), nullable=True),
    sa.Column('ticker_norm', sa.String(length=30), nullable=True),
    sa.Column('market', sa.String(length=10), nullable=True),
    sa.Column('relevance', sa.Numeric(precision=6, scale=4), nullable=True),
    sa.Column('impact', sa.Numeric(precision=6, scale=4), nullable=True),
    sa.Column('key_point', sa.String(length=200), server_default='', nullable=False),
    sa.Column('evidence', sa.Text(), server_default='', nullable=False),
    sa.Column('extractor', sa.String(length=160), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['event_id'], ['news_event.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_id', 'name_norm', name='uq_news_mention_event_name')
    )
    op.create_index(op.f('ix_news_mention_workspace_id'), 'news_mention', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_news_mention_event_id'), 'news_mention', ['event_id'], unique=False)
    op.create_index(op.f('ix_news_mention_name_norm'), 'news_mention', ['name_norm'], unique=False)
    op.create_index(op.f('ix_news_mention_ticker_norm'), 'news_mention', ['ticker_norm'], unique=False)
    op.create_table('match_job',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.String(length=36), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('params', sa.Text(), server_default='{}', nullable=False),
    sa.Column('status', sa.String(length=20), server_default='queued', nullable=False),
    sa.Column('total', sa.Integer(), server_default='0', nullable=False),
    sa.Column('processed', sa.Integer(), server_default='0', nullable=False),
    sa.Column('links_added', sa.Integer(), server_default='0', nullable=False),
    sa.Column('links_updated', sa.Integer(), server_default='0', nullable=False),
    sa.Column('estimated_calls', sa.Integer(), server_default='0', nullable=False),
    sa.Column('error', sa.String(length=1000), nullable=True),
    sa.Column('created_by', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_match_job_workspace_id'), 'match_job', ['workspace_id'], unique=False)

    op.add_column('news_event_company', sa.Column('mention_id', sa.String(length=36), nullable=True))
    op.add_column('news_event_company', sa.Column('match_method', sa.String(length=20), nullable=True))
    op.add_column('news_event_company', sa.Column('rule_version', sa.String(length=20), nullable=True))
    op.create_foreign_key('news_event_company_mention_id_fkey', 'news_event_company', 'news_mention', ['mention_id'], ['id'])
    op.add_column('news_event', sa.Column('extract_status', sa.String(length=20), server_default='pending', nullable=False))
    op.add_column('news_event', sa.Column('extract_version', sa.String(length=60), nullable=True))
    op.add_column('news_event', sa.Column('extracted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('collector_task', sa.Column('scope_kind', sa.String(length=20), server_default='general', nullable=False))
    op.add_column('collector_task', sa.Column('target_company_ids', sa.Text(), server_default='[]', nullable=False))
    op.add_column('collector_task', sa.Column('industry', sa.String(length=80), nullable=True))
    op.add_column('llm_scene_binding', sa.Column('reasoning_effort', sa.String(length=20), nullable=True))

    _migrate_data(op.get_bind())


def _migrate_data(conn) -> None:
    from app.core.paths import CONFIG_DIR
    from app.domains.news.matching.normalize import alias_norm, normalize_name, ticker_market

    # 1. watchlist = all companies, in every workspace that uses the news radar (or the oldest one)
    workspaces = [r[0] for r in conn.execute(sa.text(
        'SELECT workspace_id FROM news_event UNION SELECT workspace_id FROM collector_task ORDER BY 1'))]
    if not workspaces:
        first = conn.execute(sa.text('SELECT id FROM workspace ORDER BY created_at, id LIMIT 1')).scalar()
        workspaces = [first] if first else []
    companies = conn.execute(sa.text('SELECT id, name FROM company ORDER BY name')).all()
    for ws in workspaces:
        for company_id, _ in companies:
            conn.execute(sa.text(
                "INSERT INTO watch_company (id, workspace_id, company_id, status, note) "
                "VALUES (:id, :ws, :c, 'active', :note)"),
                {'id': str(uuid.uuid4()), 'ws': ws, 'c': company_id, 'note': '迁移 0016：沿用原“全部公司参与匹配”'})

    # 2. aliases: company name, security tickers, then the seed config
    seen: set[tuple[str, str]] = set()

    def add(company_id, alias, kind, market=None):
        norm = alias_norm(alias, kind, market)
        if not norm or (company_id, norm) in seen:
            return
        seen.add((company_id, norm))
        conn.execute(sa.text(
            "INSERT INTO company_alias (id, company_id, alias, alias_norm, kind, market, source) "
            "VALUES (:id, :c, :a, :n, :k, :m, 'seed')"),
            {'id': str(uuid.uuid4()), 'c': company_id, 'a': alias[:200], 'n': norm[:200], 'k': kind,
             'm': ticker_market(norm) if kind == 'ticker' else market})

    by_name: dict[str, str] = {}
    by_ticker: dict[str, str] = {}
    for company_id, name in companies:
        add(company_id, name, 'name')
        by_name[normalize_name(name)] = company_id
    for company_id, ticker, market in conn.execute(sa.text('SELECT company_id, ticker, market FROM security')).all():
        add(company_id, ticker, 'ticker', market)
        norm = alias_norm(ticker, 'ticker', market)
        if norm:
            by_ticker[norm] = company_id
    seed = json.loads((CONFIG_DIR / 'company-aliases-v1.json').read_text(encoding='utf-8'))
    for entry in seed['companies']:
        company_id = by_name.get(normalize_name(entry['name']))
        if company_id is None:
            for a in entry['aliases']:
                if a['kind'] == 'ticker' and alias_norm(a['alias'], 'ticker', a.get('market')) in by_ticker:
                    company_id = by_ticker[alias_norm(a['alias'], 'ticker', a.get('market'))]
                    break
        if company_id is None:
            continue  # not in the company tables yet; seed-aliases (R11) adds it once the company exists
        add(company_id, entry['name'], 'name')
        for a in entry['aliases']:
            add(company_id, a['alias'], a['kind'], a.get('market'))

    # 3. stage-1 status mirrors the old AI status
    conn.execute(sa.text(
        "UPDATE news_event SET extract_status = CASE ai_status WHEN 'scored' THEN 'done' "
        "WHEN 'rule_only' THEN 'rule_only' WHEN 'failed' THEN 'failed' ELSE 'pending' END"))

    # 4. scene rename: news_analysis → news_extract
    conn.execute(sa.text("UPDATE llm_scene_binding SET scene_key = 'news_extract' WHERE scene_key = 'news_analysis'"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text('DELETE FROM llm_scene_binding WHERE scene_key IN :keys').bindparams(
        sa.bindparam('keys', expanding=True)), {'keys': list(NEW_SCENES)})
    conn.execute(sa.text("UPDATE llm_scene_binding SET scene_key = 'news_analysis' WHERE scene_key = 'news_extract'"))
    op.drop_column('llm_scene_binding', 'reasoning_effort')
    op.drop_column('collector_task', 'industry')
    op.drop_column('collector_task', 'target_company_ids')
    op.drop_column('collector_task', 'scope_kind')
    op.drop_column('news_event', 'extracted_at')
    op.drop_column('news_event', 'extract_version')
    op.drop_column('news_event', 'extract_status')
    op.drop_constraint('news_event_company_mention_id_fkey', 'news_event_company', type_='foreignkey')
    op.drop_column('news_event_company', 'rule_version')
    op.drop_column('news_event_company', 'match_method')
    op.drop_column('news_event_company', 'mention_id')
    op.drop_index(op.f('ix_match_job_workspace_id'), table_name='match_job')
    op.drop_table('match_job')
    op.drop_index(op.f('ix_news_mention_ticker_norm'), table_name='news_mention')
    op.drop_index(op.f('ix_news_mention_name_norm'), table_name='news_mention')
    op.drop_index(op.f('ix_news_mention_event_id'), table_name='news_mention')
    op.drop_index(op.f('ix_news_mention_workspace_id'), table_name='news_mention')
    op.drop_table('news_mention')
    op.drop_index('ix_company_alias_alias_norm', table_name='company_alias')
    op.drop_table('company_alias')
    op.drop_index(op.f('ix_watch_company_workspace_id'), table_name='watch_company')
    op.drop_table('watch_company')
