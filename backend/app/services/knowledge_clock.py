"""PG owns knowledge timestamps/sequences. Disposable tests alone may inject a clock."""
from sqlalchemy import event

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


def register_metadata_triggers(metadata):
    if not getattr(metadata,'_vip_knowledge_registered',False):
        event.listen(metadata,'after_create',lambda metadata,connection,**kw: install(connection))
        metadata._vip_knowledge_registered=True
