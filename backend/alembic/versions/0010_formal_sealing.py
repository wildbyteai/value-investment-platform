"""Append market/knowledge/seal records, protect immutable facts; no historical backdating."""
from alembic import op
from app.models.sealing import KnowledgeEntry, SafetyGeneration, InstalledArtifact, PrimaryListing, MarketSession, EvaluationSeal, FrozenManifest
from app.services.knowledge_clock import install, TRACKED
revision='0010_formal_sealing'
down_revision='0009_real_research_run'
branch_labels=None
depends_on=None


def upgrade():
    connection=op.get_bind()
    for cls in (KnowledgeEntry,SafetyGeneration,InstalledArtifact,PrimaryListing,MarketSession,EvaluationSeal,FrozenManifest):
        cls.__table__.create(connection)
    install(connection)
    # Existing rows are observed at migration time, never retroactively claimed known.
    for name in TRACKED:
        connection.exec_driver_sql(f"""INSERT INTO knowledge_entry(entity_type,entity_id,operation,snapshot_json,sha256)
            SELECT '{name}',id,'INSERT',(to_jsonb(t)-'payload_json'-'value_json'-'evidence_json'-'summary_text'-'reading_metadata_json'-'origin_locator_json')::text,
            encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') FROM {name} t""")


def downgrade():
    connection=op.get_bind()
    for name in ('knowledge_entry','frozen_manifest','evaluation_seal','installed_artifact','primary_listing','market_session'):
        if connection.exec_driver_sql(f'SELECT EXISTS (SELECT 1 FROM {name})').scalar():
            raise RuntimeError('Refusing downgrade with durable knowledge or sealing records; preserve evidence and use an approved recovery plan')
    for name in TRACKED:connection.exec_driver_sql(f'DROP TRIGGER IF EXISTS vip_capture ON {name}')
    for name in ('research_input','judgment_revision','item_revision','template_release','installed_artifact','market_session','primary_listing'):
        connection.exec_driver_sql(f'DROP TRIGGER IF EXISTS vip_stamp ON {name}')
    for name in ('evaluation','market_session','installed_artifact','research_input','judgment_revision','item_revision','template_release','strategy_version','primary_listing','item_observation'):
        connection.exec_driver_sql(f'DROP TRIGGER IF EXISTS vip_immutable ON {name}')
    for cls in (FrozenManifest,EvaluationSeal,MarketSession,PrimaryListing,InstalledArtifact,SafetyGeneration,KnowledgeEntry):cls.__table__.drop(connection)
    for name in ('vip_capture_knowledge','vip_stamp_knowledge','vip_immutable_record','vip_knowledge_now'):
        connection.exec_driver_sql(f'DROP FUNCTION {name}()')
