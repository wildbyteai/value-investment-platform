"""The left-hand menus and their tabs (config/menus-v1.json), filtered by what the caller may see.

The server decides; the UI only draws what it gets. Hiding a tab is a convenience, not the
security boundary: every API still checks its own permission.
"""
import json
from functools import lru_cache

from app.core.paths import CONFIG_DIR

DEFAULT_PERMISSION = 'research.read'


@lru_cache
def _config() -> dict:
    return json.loads((CONFIG_DIR / 'menus-v1.json').read_text(encoding='utf-8'))


def tab_keys() -> list[str]:
    return [t['key'] for m in _config()['menus'] for t in m['tabs']]


def visible_menus(permissions) -> list[dict]:
    allowed = set(permissions)
    out = []
    for menu in _config()['menus']:
        tabs = [{'key': t['key'], 'label': t['label']} for t in menu['tabs']
                if allowed & set(t.get('permissions') or [DEFAULT_PERMISSION])]
        if tabs:
            out.append({'key': menu['key'], 'label': menu['label'], 'icon': menu.get('icon', ''), 'tabs': tabs})
    return out
