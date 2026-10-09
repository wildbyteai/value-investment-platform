"""账号、角色、菜单与统一接口规范（错误格式、分页、请求编号）。"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.domains.identity import menus
from app.domains.identity.permissions import VALID_ROLES, catalog, permissions_for


def test_every_role_has_a_label_and_every_permission_a_name():
    cat = catalog()
    assert {r['key'] for r in cat['roles']} == set(VALID_ROLES)
    assert all(r['label'] and r['label'] != r['key'] for r in cat['roles'])
    named = {p['key'] for p in cat['permissions']}
    assert {p for r in cat['roles'] for p in r['permissions']} <= named


def test_permissions_are_the_union_of_roles():
    both = permissions_for(['viewer', 'system_admin'])
    assert 'research.read' in both and 'user.manage' in both and len(both) == len(set(both))


def test_menus_follow_permissions():
    viewer = menus.visible_menus(permissions_for(['viewer']))
    keys = {t['key'] for m in viewer for t in m['tabs']}
    assert 'users' not in keys and 'models' not in keys and 'events' in keys and 'mine' in keys
    assert 'settings' not in {m['key'] for m in viewer}
    admin = menus.visible_menus(permissions_for(['system_admin']))
    assert [m['key'] for m in admin] == ['settings']
    assert {'users', 'models', 'audit', 'tasks'} <= {t['key'] for t in admin[0]['tabs']}


def test_tab_keys_are_unique():
    keys = menus.tab_keys()
    assert len(keys) == len(set(keys))


@pytest.fixture(scope='module')
def env():
    from app.db import Base
    from app.main import app
    engine = create_engine(os.environ['VIP_DB_URL'], future=True)
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    from scripts_seed import seed
    seed()
    with engine.connect() as conn:
        ws = str(conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one())
    with TestClient(app) as c:
        yield c, ws
    Base.metadata.drop_all(bind=engine)


def h(ws, login='admin@demo'):
    return {'X-Vip-Login': login, 'X-Vip-Workspace': ws}


def test_me_returns_roles_permissions_and_menus(env):
    c, ws = env
    me = c.get('/api/me', headers=h(ws, 'viewer@demo')).json()
    assert me['roles'] == [{'key': 'viewer', 'label': '只读访客'}]
    assert 'research.read' in me['permissions']
    assert me['menus'][0]['key'] == 'radar'


def test_only_account_managers_see_accounts(env):
    c, ws = env
    assert c.get('/api/admin/users', headers=h(ws, 'research@demo')).status_code == 403
    r = c.get('/api/admin/users?limit=2', headers=h(ws))
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {'items', 'total', 'limit', 'offset'} and body['limit'] == 2 and len(body['items']) == 2
    assert body['total'] >= 5
    assert 'password_hash' not in body['items'][0] and 'has_password' in body['items'][0]
    assert c.get('/api/admin/roles', headers=h(ws)).json()['roles'][0]['key'] == 'viewer'


def test_account_lifecycle_is_audited(env):
    c, ws = env
    r = c.post('/api/admin/users', json={'login': 'New.Analyst@Example.com', 'display_name': '新研究员', 'roles': ['researcher']}, headers=h(ws))
    assert r.status_code == 201, r.text
    user = r.json()
    assert user['login'] == 'new.analyst@example.com' and user['roles'] == ['researcher'] and user['has_password']
    assert len(user['initial_password']) >= 12
    uid = user['id']
    assert c.post('/api/admin/users', json={'login': 'new.analyst@example.com', 'display_name': 'x', 'roles': ['viewer']}, headers=h(ws)).status_code == 409
    assert c.post('/api/admin/users', json={'login': 'x@example.com', 'display_name': 'x', 'roles': ['king']}, headers=h(ws)).status_code == 422
    assert c.post('/api/admin/users', json={'login': 'y@example.com', 'display_name': 'y', 'roles': ['viewer'], 'password': 'short'}, headers=h(ws)).status_code == 422

    r = c.put(f'/api/admin/users/{uid}/roles', json={'roles': ['researcher', 'strategy_manager']}, headers=h(ws))
    assert r.json()['roles'] == ['researcher', 'strategy_manager']
    me = c.get('/api/me', headers=h(ws, 'new.analyst@example.com')).json()
    assert 'strategy.publish' in me['permissions'] and 'analysis.override' in me['permissions']

    assert c.patch(f'/api/admin/users/{uid}', json={'display_name': '研究员乙'}, headers=h(ws)).json()['display_name'] == '研究员乙'
    reset = c.post(f'/api/admin/users/{uid}/password', json={}, headers=h(ws)).json()
    assert reset['ok'] and len(reset['initial_password']) >= 12
    assert c.patch(f'/api/admin/users/{uid}', json={'disabled': True}, headers=h(ws)).json()['disabled'] is True
    assert c.get('/api/me', headers=h(ws, 'new.analyst@example.com')).status_code == 401

    log = c.get('/api/admin/audit?action=identity.user', headers=h(ws)).json()
    actions = [a['action'] for a in log['items'] if a['entity_id'] == uid]
    assert {'identity.user.created', 'identity.user.roles_changed', 'identity.user.updated', 'identity.user.password_reset'} <= set(actions)
    assert all(a['actor']['login'] == 'admin@demo' for a in log['items'] if a['entity_id'] == uid)
    assert 'initial_password' not in str(log)  # one-time passwords are never logged
    assert c.get('/api/admin/audit', headers=h(ws, 'data@demo')).status_code == 403


def test_admins_cannot_lock_the_workspace_out(env):
    c, ws = env
    admin_id = next(u['id'] for u in c.get('/api/admin/users?q=admin@demo', headers=h(ws)).json()['items'])
    assert c.patch(f'/api/admin/users/{admin_id}', json={'disabled': True}, headers=h(ws)).status_code == 409
    r = c.put(f'/api/admin/users/{admin_id}/roles', json={'roles': ['viewer']}, headers=h(ws))
    assert r.status_code == 409 and r.json()['error']['code'] == 'conflict'


def test_other_workspaces_accounts_are_invisible(env):
    c, ws = env
    assert c.get('/api/admin/users/00000000-0000-0000-0000-000000000000', headers=h(ws)).status_code == 404


def test_standard_error_shape_and_request_id(env):
    c, ws = env
    r = c.get('/api/admin/users', headers=h(ws, 'viewer@demo'))
    assert r.status_code == 403
    body = r.json()
    assert body['error']['code'] == 'forbidden' and body['detail'] == body['error']['message']
    assert body['request_id'] == r.headers['x-request-id']
    r = c.get('/api/admin/users?limit=0', headers=h(ws))
    assert r.status_code == 422 and r.json()['error']['details'][0]['field'] == 'limit'
    r = c.get('/api/me', headers={'X-Request-Id': 'trace-12345678', **h(ws)})
    assert r.headers['x-request-id'] == 'trace-12345678'
    assert c.get('/api/me', headers={'X-Request-Id': 'bad id\n', **h(ws)}).headers['x-request-id'] != 'bad id\n'
    assert c.get('/api/nope', headers=h(ws)).json()['error']['code'] == 'not_found'
