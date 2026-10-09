"""推理强度（reasoning effort）：哪些模型允许哪些强度，以及怎样写进各厂商的请求（ADR 0016）。

Allowed efforts live per preset in ``config/model-presets-v1.json`` (``reasoning_efforts``, optionally
``model_reasoning_efforts`` per model name). A configured model is matched to a preset by the host of
its ``base_url``; a model whose host matches no preset, or whose preset declares no efforts, never
gets an effort parameter (the request is sent exactly as before).

Request mapping (``reasoning_style`` of the preset):

* ``openai``   Chat Completions ``reasoning_effort``; Responses ``reasoning: {effort}``.
               Values none|low|medium|high|xhigh|max; gpt-6.1-sol / gpt-6-astra do not accept none.
* ``deepseek`` ``reasoning_effort`` low|high|max (medium → high, xhigh → max);
               ``none`` → ``thinking: {"type": "disabled"}``.
* other        the preset's declared efforts are passed through as ``reasoning_effort``.

An effort the model does not allow is dropped (never sent), so a stale binding cannot break a call.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from app.domains.news import model_presets

EFFORTS = ('none', 'low', 'medium', 'high', 'xhigh', 'max')
DEEPSEEK_MAP = {'none': 'none', 'minimal': 'low', 'low': 'low', 'medium': 'high', 'high': 'high',
                'xhigh': 'max', 'max': 'max'}


def _host(base_url: str | None) -> str:
    try:
        return (urlsplit(base_url or '').hostname or '').lower()
    except ValueError:
        return ''


def preset_for(base_url: str | None) -> dict | None:
    """The preset whose API host equals this model's host (raw config entry), else ``None``."""
    host = _host(base_url)
    if not host:
        return None
    for p in model_presets.config()['presets']:
        if _host(p['base_url']) == host:
            return p
    return None


def preset_key(base_url: str | None) -> str | None:
    p = preset_for(base_url)
    return p['provider_key'] if p else None


def style(base_url: str | None) -> str | None:
    p = preset_for(base_url)
    if not p or not p.get('reasoning_efforts'):
        return None
    return p.get('reasoning_style') or 'passthrough'


def allowed_efforts(base_url: str | None, model: str | None) -> list[str]:
    """Efforts this model accepts, in EFFORTS order; ``[]`` = do not send any effort."""
    p = preset_for(base_url)
    if not p:
        return []
    allowed = (p.get('model_reasoning_efforts') or {}).get(model or '', p.get('reasoning_efforts') or [])
    return [e for e in EFFORTS if e in allowed]


def effective(base_url: str | None, model: str | None, effort: str | None) -> str | None:
    """The effort that will actually be requested (after vendor mapping), or ``None``."""
    if not effort:
        return None
    s = style(base_url)
    if s is None:
        return None
    if s == 'deepseek':
        effort = DEEPSEEK_MAP.get(effort)
    return effort if effort in allowed_efforts(base_url, model) else None


def chat_params(base_url: str | None, model: str | None, effort: str | None) -> dict:
    """Extra body fields for ``POST /chat/completions``."""
    e = effective(base_url, model, effort)
    if e is None:
        return {}
    if style(base_url) == 'deepseek':
        return {'thinking': {'type': 'disabled'}} if e == 'none' else {'reasoning_effort': e}
    return {'reasoning_effort': e}


def responses_params(base_url: str | None, model: str | None, effort: str | None, assume_openai: bool = False) -> dict:
    """Extra body fields for an OpenAI-shaped ``POST /responses``.

    ``assume_openai``: the caller knows this is OpenAI's own Responses API (search mode
    ``openai_web_search``) reached through a host that matches no preset, e.g. a proxy; the effort is
    then passed through unchanged, as before ADR 0016."""
    if assume_openai and preset_for(base_url) is None:
        return {'reasoning': {'effort': effort}} if effort in EFFORTS else {}
    e = effective(base_url, model, effort)
    return {'reasoning': {'effort': e}} if e is not None else {}
