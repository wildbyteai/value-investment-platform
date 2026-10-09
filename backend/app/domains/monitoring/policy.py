from app.core.paths import CONFIG_DIR
import json
from functools import lru_cache
from pathlib import Path

CONFIG = CONFIG_DIR / 'alerts-v1.json'


@lru_cache
def policy() -> dict:
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def sender_address() -> str:
    from app.config import get_settings
    return get_settings().alert_sender or policy()['sender']['address']
