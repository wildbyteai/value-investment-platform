"""Roles and permissions. The five roles and what each may do live in config/roles-standard-v1.json.

A user can hold several roles in one workspace; their permissions are the union.
"""
import json
from functools import lru_cache

from app.core.paths import CONFIG_DIR

ROLES_CONFIG = CONFIG_DIR / 'roles-standard-v1.json'


@lru_cache
def _config() -> dict:
    return json.loads(ROLES_CONFIG.read_text(encoding='utf-8'))


def role_permissions() -> dict[str, list[str]]:
    return {role: list(perms) for role, perms in _config()['roles'].items()}


VALID_ROLES = frozenset(_config()['roles'])


def permissions_for(roles) -> list[str]:
    """Union of the permissions of ``roles``, in a stable order."""
    table = role_permissions()
    out: list[str] = []
    for role in roles:
        for p in table.get(role, []):
            if p not in out:
                out.append(p)
    return out


def role_has(role: str, permission: str) -> bool:
    return permission in role_permissions().get(role, [])


def catalog() -> dict:
    """Roles with their labels and permissions, for the settings page and role pickers."""
    cfg = _config()
    labels = cfg.get('permission_labels', {})
    return {
        'roles': [{'key': r, 'label': cfg['role_labels'].get(r, r), 'description': cfg.get('role_descriptions', {}).get(r, ''),
                   'permissions': perms} for r, perms in cfg['roles'].items()],
        'permissions': [{'key': k, 'label': v} for k, v in labels.items()],
    }


def role_label(role: str) -> str:
    return _config()['role_labels'].get(role, role)
