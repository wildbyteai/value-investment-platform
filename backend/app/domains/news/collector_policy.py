from app.core.paths import CONFIG_DIR
import json
from functools import lru_cache
from pathlib import Path

CONFIG = CONFIG_DIR / 'news-collector-v1.json'


@lru_cache
def policy() -> dict:
    return json.loads(CONFIG.read_text(encoding='utf-8'))
