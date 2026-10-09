"""R4: the four-menu UI is served, and every API the new views call answers for the roles that see them."""
import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

STATIC = Path(__file__).resolve().parents[1] / 'static'
SRC = Path(__file__).resolve().parents[2] / 'frontend' / 'src'


def test_four_menus_and_settings():
    # Menus are served by the API (config/menus-v1.json), not baked into the bundle.
    from app.domains.identity import menus
    from app.domains.identity.permissions import VALID_ROLES, permissions_for
    labels = [m['label'] for m in menus.visible_menus(permissions_for(VALID_ROLES))]
    assert labels == ['资讯雷达', '公司档案', '策略（击球区）', '监控告警', '后台设置']
    assert (STATIC / 'app.js').exists()


def test_every_endpoint_the_ui_calls_is_routed():
    from app.main import app
    routes = set(app.openapi()['paths'])
    called = set()
    for path in SRC.rglob('*.ts*'):
        if path.name != 'api-schema.ts':
            called |= set(re.findall(r'["`](/api/[a-z\-/]+)', path.read_text(encoding='utf-8')))
    normalized = {c.rstrip('/') for c in called}
    missing = [c for c in normalized if not any(r == c or r.startswith(c + '/') for r in routes)]
    assert missing == []


@pytest.fixture(scope='module')
def client():
    from app.db import Base
    from app.main import app
    from services_companies import seed_companies
    engine = create_engine(os.environ['VIP_DB_URL'], future=True)
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    from scripts_seed import seed
    seed()
    with sessionmaker(bind=engine, future=True)() as s:
        seed_companies(s); s.commit()
    with engine.connect() as conn:
        ws = str(conn.execute(text("SELECT id FROM workspace WHERE name='演示研究组织（合成数据）'")).scalar_one())
    with TestClient(app) as c:
        yield c, ws
    Base.metadata.drop_all(bind=engine)


VIEWS = {
    'viewer@demo': ['/api/news/events?limit=80', '/api/companies', '/api/strike-zone', '/api/notifications',
                    '/api/alerts', '/api/notifications/settings', '/api/news/feeds',
                    '/api/strike-zone/companies/00000000-0000-4000-8000-000000000001',
                    '/api/news/events?company_id=00000000-0000-4000-8000-000000000001&limit=10'],
    'data@demo': ['/api/admin/sources', '/api/news/feeds'],
    'admin@demo': ['/api/admin/sources', '/api/admin/llm-providers', '/api/admin/notify', '/api/me'],
}


@pytest.mark.parametrize('login', sorted(VIEWS))
def test_views_load_for_their_roles(client, login):
    c, ws = client
    headers = {'X-Vip-Login': login, 'X-Vip-Workspace': ws}
    for path in VIEWS[login]:
        r = c.get(path, headers=headers)
        assert r.status_code == 200, (path, r.text)


def test_index_served(client):
    c, _ = client
    r = c.get('/')
    assert r.status_code == 200 and 'app.js' in r.text


def test_every_menu_tab_has_a_page():
    """config/menus-v1.json and frontend/src/pages/index.tsx must name the same tabs."""
    from app.domains.identity import menus
    registry = (SRC / 'pages' / 'index.tsx').read_text(encoding='utf-8')
    pages = set(re.findall(r'^  "?([a-z\-]+)"?: \(p\) =>', registry, re.M))
    assert pages == set(menus.tab_keys())


def test_navigation_is_a_left_sidebar_without_top_tabs():
    """纯左右布局（docs/23 §2.1）：页面切换只在左侧两级导航里，外壳不再有顶部页签条。"""
    shell = (SRC / 'shell' / 'workspace.tsx').read_text(encoding='utf-8')
    nav = (SRC / 'shell' / 'sidenav.tsx').read_text(encoding='utf-8')
    css = (SRC / 'shell' / 'style.css').read_text(encoding='utf-8')
    assert 'subtabs' not in shell and 'role="tablist"' not in shell and '.subtabs' not in css
    assert '<SideNav' in shell and 'aria-current' in nav and 'vip-nav-collapsed' in nav
    assert 'role="tab"' not in nav
    assert '.subtabs' not in (STATIC / 'app.css').read_text(encoding='utf-8')


def test_style_uses_design_tokens():
    """界面规范（docs/23 §6，基于 Ant Design）：令牌块之后只用令牌字号、字重与颜色。"""
    css = (SRC / 'shell' / 'style.css').read_text(encoding='utf-8')
    body = css[css.index('* { box-sizing'):]
    assert ':root {' in css and ':root[data-theme="dark"] {' in css
    sizes = set(re.findall(r'font-size:\s*([^;}]+)', body))
    assert sizes <= {'var(--fs-sm)', 'var(--fs)', 'var(--fs-lg)', 'var(--fs-xl)', 'var(--fs-xxl)', '0'}, sizes
    assert set(re.findall(r'font-weight:\s*([^;}]+)', body)) <= {'var(--fw)', 'var(--fw-strong)', 'var(--fw-num)'}
    assert re.findall(r'#[0-9a-fA-F]{3,8}\b', body) == []
    assert re.findall(r'rgba?\(', body) == []
