"""Append market/knowledge/seal records, protect immutable facts; no historical backdating.

R1 (2026-10-07): this migration used to build its tables from the live ORM models and
install triggers from the live ``knowledge_clock`` module, so any later model or trigger
edit silently changed what a fresh database got. Both are now frozen here as explicit
DDL, byte-for-byte equivalent to what 985fcd9 produced (verified with pg_dump -s).
Future schema or trigger changes need a new migration.
"""
from alembic import op
import sqlalchemy as sa
revision='0010_formal_sealing'
down_revision='0009_real_research_run'
branch_labels=None
depends_on=None

TRACKED=('research_input','judgment_revision','judgment_slot','item_revision','item_observation',
         'source_registry','item_company_link','company','security','template_release','strategy_version',
         'primary_listing','market_session','installed_artifact')
DDL="""
CREATE OR REPLACE FUNCTION vip_knowledge_now() RETURNS timestamptz LANGUAGE plpgsql AS $$
BEGIN
  IF current_database()='vip_v0001_test' AND nullif(current_setting('vip.test_clock',true),'') IS NOT NULL THEN
    RETURN current_setting('vip.test_clock',true)::timestamptz;
  END IF;
  RETURN clock_timestamp();
END $$;
CREATE OR REPLACE FUNCTION vip_capture_knowledge() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE body jsonb; stamp timestamptz; safety boolean;
BEGIN
  -- Serialize safety mutations before stamping, so lock waits cannot backdate knowledge.
  PERFORM generation FROM safety_generation WHERE key='safety' FOR UPDATE;
  stamp := vip_knowledge_now();
  IF TG_OP='DELETE' THEN body:=to_jsonb(OLD); ELSE body:=to_jsonb(NEW); END IF;
  INSERT INTO knowledge_entry(entity_type,entity_id,operation,snapshot_json,sha256,recorded_at)
    VALUES(TG_TABLE_NAME,body->>'id',TG_OP,
      (body-'payload_json'-'value_json'-'evidence_json'-'summary_text'-'reading_metadata_json'-'origin_locator_json')::text,
      encode(sha256(convert_to(body::text,'UTF8')),'hex'),stamp);
  safety := TG_TABLE_NAME IN ('source_registry','item_company_link','company','security','primary_listing','market_session','template_release','strategy_version');
  IF TG_TABLE_NAME IN ('judgment_revision','judgment_slot') THEN
    IF TG_TABLE_NAME='judgment_slot' THEN safety:=body->>'kind'='risk';
    ELSE SELECT kind='risk' INTO safety FROM judgment_slot WHERE id=body->>'slot_id'; END IF;
  END IF;
  IF safety THEN
    INSERT INTO safety_generation(key,generation) VALUES('safety',1)
    ON CONFLICT(key) DO UPDATE SET generation=safety_generation.generation+1;
  END IF;
  IF TG_OP='DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION vip_stamp_knowledge() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  -- No caller may backdate real knowledge. Existing synthetic tests remain disposable.
  IF current_database()<>'vip_v0001_test' OR coalesce(current_setting('vip.force_immutable',true),'')='on' THEN
    IF TG_TABLE_NAME='research_input' THEN NEW.known_at:=vip_knowledge_now();
    ELSIF TG_TABLE_NAME='installed_artifact' THEN NEW.installed_at:=vip_knowledge_now();
    ELSE NEW.created_at:=vip_knowledge_now(); END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION vip_immutable_record() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_database()='vip_v0001_test' AND TG_TABLE_NAME IN ('research_input','judgment_revision','item_revision','template_release','strategy_version','primary_listing','item_observation')
     AND coalesce(current_setting('vip.force_immutable',true),'')<>'on' THEN
    IF TG_OP='DELETE' THEN RETURN OLD; END IF; RETURN NEW;
  END IF;
  RAISE EXCEPTION 'immutable research record';
END $$;
"""


def install(connection):
    connection.exec_driver_sql(DDL)
    for table in TRACKED:
        connection.exec_driver_sql(f'DROP TRIGGER IF EXISTS vip_capture ON {table}')
        connection.exec_driver_sql(f'CREATE CONSTRAINT TRIGGER vip_capture AFTER INSERT OR UPDATE OR DELETE ON {table} DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION vip_capture_knowledge()')
    for table in ('research_input','judgment_revision','item_revision','template_release','installed_artifact','market_session','primary_listing'):
        connection.exec_driver_sql(f'DROP TRIGGER IF EXISTS vip_stamp ON {table}')
        connection.exec_driver_sql(f'CREATE TRIGGER vip_stamp BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION vip_stamp_knowledge()')
    for table in ('frozen_manifest','knowledge_entry','evaluation','market_session','installed_artifact','research_input','judgment_revision','item_revision','template_release','strategy_version','primary_listing','item_observation'):
        connection.exec_driver_sql(f'DROP TRIGGER IF EXISTS vip_immutable ON {table}')
        connection.exec_driver_sql(f'CREATE TRIGGER vip_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION vip_immutable_record()')
    connection.exec_driver_sql("INSERT INTO safety_generation(key,generation) VALUES('safety',0) ON CONFLICT DO NOTHING")


def ts(name,nullable=False,clock=False):
    return sa.Column(name,sa.DateTime(timezone=True),nullable=nullable,server_default=sa.text('clock_timestamp()') if clock else None)


def upgrade():
    connection=op.get_bind()
    op.create_table('knowledge_entry',
        sa.Column('sequence',sa.BigInteger(),sa.Identity(),primary_key=True),
        sa.Column('entity_type',sa.String(60),nullable=False),
        sa.Column('entity_id',sa.String(36),nullable=False),
        sa.Column('operation',sa.String(10),nullable=False),
        sa.Column('snapshot_json',sa.Text(),nullable=False),
        sa.Column('sha256',sa.String(64),nullable=False),
        ts('recorded_at',clock=True))
    op.create_table('safety_generation',
        sa.Column('key',sa.String(40),primary_key=True),
        sa.Column('generation',sa.BigInteger(),nullable=False))
    op.create_table('installed_artifact',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('artifact_key',sa.String(120),nullable=False),
        sa.Column('sha256',sa.String(64),nullable=False),
        sa.Column('payload_json',sa.Text(),nullable=False),
        ts('installed_at',clock=True),
        sa.UniqueConstraint('artifact_key','sha256',name='uq_installed_artifact'))
    op.create_table('primary_listing',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('security_id',sa.String(36),sa.ForeignKey('security.id'),nullable=False,unique=True),
        sa.Column('exchange',sa.String(30),nullable=False),
        sa.Column('currency',sa.String(10),nullable=False),
        sa.Column('calendar_ref',sa.String(120),nullable=False),
        sa.Column('close_policy_json',sa.Text(),nullable=False),
        ts('created_at',clock=True))
    op.create_table('market_session',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('calendar_ref',sa.String(120),nullable=False),
        sa.Column('market_session',sa.String(40),nullable=False),
        sa.Column('ordinal',sa.Integer(),nullable=False),
        sa.Column('previous_session',sa.String(40),nullable=True),
        ts('final_market_at'),
        sa.Column('evidence_json',sa.Text(),nullable=False),
        ts('created_at',clock=True),
        sa.UniqueConstraint('calendar_ref','market_session',name='uq_market_session'))
    op.create_table('evaluation_seal',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('workspace_id',sa.String(36),nullable=False),
        sa.Column('release_id',sa.String(36),sa.ForeignKey('strategy_version.id'),nullable=False),
        sa.Column('security_id',sa.String(36),sa.ForeignKey('security.id'),nullable=False),
        sa.Column('listing_id',sa.String(36),sa.ForeignKey('primary_listing.id'),nullable=False),
        sa.Column('market_session',sa.String(40),nullable=False),
        sa.Column('mode',sa.String(20),nullable=False),
        sa.Column('state',sa.String(40),nullable=False),
        sa.Column('generation',sa.Integer(),nullable=False),
        sa.Column('fence',sa.Integer(),nullable=False),
        sa.Column('lease_owner',sa.String(120),nullable=True),
        ts('lease_until',nullable=True),
        sa.Column('manifest_id',sa.String(36),nullable=True),
        sa.Column('evaluation_id',sa.String(36),nullable=True),
        ts('evaluation_as_of'),
        ts('knowledge_cutoff'),
        sa.Column('finalization_token',sa.String(36),nullable=False,unique=True),
        sa.UniqueConstraint('workspace_id','release_id','security_id','market_session','mode',name='uq_evaluation_seal'))
    op.create_table('frozen_manifest',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('seal_id',sa.String(36),sa.ForeignKey('evaluation_seal.id'),nullable=False),
        sa.Column('generation',sa.Integer(),nullable=False),
        sa.Column('manifest_json',sa.Text(),nullable=False),
        sa.Column('manifest_hash',sa.String(64),nullable=False),
        sa.Column('snapshot_json',sa.Text(),nullable=False),
        sa.Column('snapshot_hash',sa.String(64),nullable=False),
        sa.Column('safety_generation',sa.BigInteger(),nullable=False),
        ts('frozen_at',clock=True),
        sa.UniqueConstraint('seal_id','generation',name='uq_frozen_generation'))
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
    for name in ('frozen_manifest','evaluation_seal','market_session','primary_listing','installed_artifact','safety_generation','knowledge_entry'):op.drop_table(name)
    for name in ('vip_capture_knowledge','vip_stamp_knowledge','vip_immutable_record','vip_knowledge_now'):
        connection.exec_driver_sql(f'DROP FUNCTION {name}()')
