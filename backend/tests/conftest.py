"""Guard destructive fixtures before application/engine imports."""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app.config import get_settings

original=make_url(get_settings().db_url)
target=make_url(os.environ.get('VIP_TEST_DB_URL') or str(original.set(database='vip_v0001_test').render_as_string(hide_password=False)))
if target.host not in ('127.0.0.1','localhost') or target.database!='vip_v0001_test':
    raise RuntimeError('Tests require this project local synthetic database; refusing destructive fixtures')
os.environ['VIP_DEMO_MODE']='true'
# Most tests use the header mock identities; test_auth.py switches to real sessions itself.
os.environ['VIP_AUTH_MODE']='dev'
os.environ['VIP_LLM_ALLOWED_HOSTS']='api.example.com'
os.environ['VIP_DB_URL']=target.render_as_string(hide_password=False)
get_settings.cache_clear()


def pytest_sessionstart(session):
    with create_engine(target).connect() as conn:
        actual=conn.execute(text('SELECT current_database(), inet_server_addr()::text, inet_server_port()')).one()
        if actual[0]!='vip_v0001_test' or actual[1] not in ('127.0.0.1/32','::1/128'):
            raise RuntimeError('Actual server location/target mismatch')
        exists=conn.execute(text("SELECT to_regclass('public.source_registry')")).scalar()
        if exists:
            keys=conn.execute(text('SELECT source_key FROM source_registry')).scalars().all()
            if any(k!='local-fixture' for k in keys):
                raise RuntimeError('Test database contains non-synthetic sources; refusing reset')
