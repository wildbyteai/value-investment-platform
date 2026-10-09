"""Deployment hardening: real sign-in, sessions, CSRF, headers, and keeping model keys at home."""
import os

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core import passwords, secret_guard
from app.domains.news import llm

PW = 'correct horse battery'
CSRF = {'X-Requested-With': 'vip'}


@pytest.fixture(scope='module')
def env():
    from app.config import get_settings
    from app.db import Base
    from app.main import app
    from app.models.identity import User
    engine = create_engine(os.environ['VIP_DB_URL'], future=True)
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    from scripts_seed import seed
    seed()
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        for u in s.scalars(select(User).where(User.login.in_(['research@demo', 'viewer@demo', 'admin@demo']))):
            u.password_hash = passwords.hash_password(PW)
        s.commit()
    with engine.connect() as conn:
        ws = str(conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one())
        other = str(conn.execute(text("SELECT id FROM workspace WHERE id <> :w LIMIT 1"), {'w': ws}).scalar_one())
    settings = get_settings()
    settings.auth_mode = 'session'
    try:
        with TestClient(app, base_url='https://testserver') as c:
            yield c, ws, other, Session
    finally:
        settings.auth_mode = 'dev'
        Base.metadata.drop_all(bind=engine)


def login(c, who='research@demo', pw=PW, headers=CSRF):
    return c.post('/api/auth/login', json={'login': who, 'password': pw}, headers=headers)


def test_mock_identities_are_gone(env):
    c, ws, _, _ = env
    assert c.get('/api/identities').status_code == 404
    assert c.get('/api/me', headers={'X-Vip-Login': 'admin@demo', 'X-Vip-Workspace': ws}).status_code == 401


def test_login_session_and_workspace_check(env):
    c, ws, other, Session = env
    assert login(c, headers={}).status_code == 403          # CSRF header required
    assert login(c, pw='wrong password!!').status_code == 401
    r = login(c)
    assert r.status_code == 200 and any(w['id'] == ws for w in r.json()['workspaces'])
    cookie = r.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'secure' in cookie and 'samesite=strict' in cookie
    # The header can only pick a workspace; it cannot change who you are.
    me = c.get('/api/me', headers={'X-Vip-Workspace': ws, 'X-Vip-Login': 'admin@demo'}).json()
    assert me['user']['login'] == 'research@demo'
    from app.models.identity import AuthSession, Membership, User
    with Session() as s:
        uid = s.scalar(select(User.id).where(User.login == 'research@demo'))
        member_of_other = s.scalar(select(Membership.id).where(Membership.user_id == uid, Membership.workspace_id == other))
        stored = s.scalars(select(AuthSession.token_hash)).all()
    if not member_of_other:
        assert c.get('/api/me', headers={'X-Vip-Workspace': other}).status_code == 403
    token = c.cookies.get('vip_session')
    assert token and token not in stored and len(stored[0]) == 64   # only the hash is stored
    # Writes without the CSRF header are refused even with a valid cookie.
    assert c.post('/api/news/score', json={}, headers={'X-Vip-Workspace': ws}).status_code == 403
    assert c.post('/api/auth/logout', headers=CSRF).status_code == 200
    assert c.get('/api/me', headers={'X-Vip-Workspace': ws}).status_code == 401


def test_password_guessing_is_throttled(env):
    c, *_ = env
    for _ in range(5):
        assert login(c, 'viewer@demo', 'nope nope nope').status_code == 401
    assert login(c, 'viewer@demo').status_code == 429


def test_change_password_signs_out_other_browsers(env):
    c, ws, _, _ = env
    from app.main import app
    with TestClient(app, base_url='https://testserver') as other:
        assert login(other, 'admin@demo').status_code == 200
        assert login(c, 'admin@demo').status_code == 200
        assert c.post('/api/auth/password', json={'current': PW, 'new': 'short'}, headers=CSRF).status_code == 422
        assert c.post('/api/auth/password', json={'current': 'bad', 'new': 'another long secret'}, headers=CSRF).status_code == 403
        assert c.post('/api/auth/password', json={'current': PW, 'new': 'another long secret'}, headers=CSRF).status_code == 200
        assert c.get('/api/me', headers={'X-Vip-Workspace': ws}).status_code == 200
        assert other.get('/api/me', headers={'X-Vip-Workspace': ws}).status_code == 401


def test_security_headers(env):
    c, *_ = env
    r = c.get('/api/auth/state')
    assert r.json()['mode'] == 'session'
    for k in ('content-security-policy', 'x-content-type-options', 'x-frame-options', 'strict-transport-security'):
        assert k in r.headers
    assert r.headers['cache-control'] == 'no-store'


def test_model_keys_only_go_to_allowed_hosts(monkeypatch):
    monkeypatch.setenv('VIP_OPENAI_API_KEY', 'sk-real')
    monkeypatch.setenv('VIP_SMTP_PASSWORD', 'mail-secret')
    ok = llm.ProviderConfig('openai', 'O', 'https://api.openai.com/v1', 'm', 'VIP_OPENAI_API_KEY')
    assert ok.blocked is None and ok.api_key == 'sk-real'
    evil = llm.ProviderConfig('x', 'X', 'https://attacker.example.net/v1', 'm', 'VIP_OPENAI_API_KEY')
    assert evil.blocked and evil.api_key == '' and not evil.configured
    smtp = llm.ProviderConfig('x', 'X', 'https://api.openai.com/v1', 'm', 'VIP_SMTP_PASSWORD')
    assert smtp.blocked and smtp.api_key == ''
    assert secret_guard.base_url_problem('http://api.openai.com/v1')
    assert secret_guard.base_url_problem('https://user:pw@api.openai.com/v1')
    with pytest.raises(llm.LlmError, match='安全检查'):
        from app.domains.news import agent
        agent.chat(evil, [{'role': 'user', 'content': 'x'}])
    monkeypatch.setenv('VIP_LLM_ALLOWED_HOSTS', 'my-proxy.example.org')
    assert llm.ProviderConfig('x', 'X', 'https://my-proxy.example.org/v1', 'm', 'VIP_OPENAI_API_KEY').api_key == 'sk-real'


def test_feed_fetches_cannot_reach_internal_addresses():
    t = secret_guard.PublicOnlyTransport()
    with httpx.Client(transport=t) as client:
        for url in ('http://127.0.0.1:8766/api/health', 'http://169.254.169.254/latest/meta-data', 'http://localhost/'):
            with pytest.raises(httpx.ConnectError):
                client.get(url)
