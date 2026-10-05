import json
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROLES_CONFIG = PROJECT_ROOT / "config" / "roles-standard-v1.json"


@lru_cache
def role_permissions() -> dict[str, list[str]]:
    data = json.loads(ROLES_CONFIG.read_text(encoding="utf-8"))
    return {role: list(perms) for role, perms in data["roles"].items()}


def role_has(role: str, permission: str) -> bool:
    perms = role_permissions().get(role, [])
    return permission in perms


VALID_ROLES = {"viewer", "researcher", "strategy_manager", "data_admin", "system_admin"}
