import json
from functools import lru_cache
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[4] / 'config' / 'news-radar-v1.json'


@lru_cache
def policy() -> dict:
    return json.loads(CONFIG.read_text(encoding='utf-8'))
