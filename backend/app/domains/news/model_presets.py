"""内置模型预设（config/model-presets-v1.json）：模型配置页“添加模型”的唯一来源。

Each preset only pre-fills the form; nothing is saved until an administrator saves it. The
preset hosts also seed the API-key host allowlist (app/core/secret_guard.py).
"""
from __future__ import annotations

import json
from functools import lru_cache

from app.core.paths import CONFIG_DIR

CONFIG = CONFIG_DIR / 'model-presets-v1.json'
FIELDS = ('provider_key', 'name', 'vendor', 'base_url', 'model', 'api_key_env', 'search_mode', 'note', 'doc_url')


@lru_cache
def config() -> dict:
    return json.loads(CONFIG.read_text(encoding='utf-8'))


OPTIONAL = {'reasoning_style': None, 'reasoning_efforts': [], 'model_reasoning_efforts': {}}


def presets() -> list[dict]:
    return [{**{k: p.get(k) for k in FIELDS}, **{k: p.get(k, d) for k, d in OPTIONAL.items()}} for p in config()['presets']]
