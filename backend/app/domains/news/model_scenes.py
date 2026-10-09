"""按场景配置模型：每个调用大模型的地方是一个“场景”（config/model-scenes-v1.json），
工作区可以给每个场景指定一个已配置的模型。

取用顺序：场景绑定的模型（启用中）→ 工作区默认模型（is_default 优先，其次最早添加的启用模型）
→ 内置默认（环境变量密钥）。采集定时器自己选了模型时，定时器的模型优先于场景。

Never commits.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy import select

from app.core.errors import Invalid
from app.core.paths import CONFIG_DIR
from app.domains.news import llm
from app.domains.platform.transactions import record
from app.models.news import LlmProvider, LlmSceneBinding

CONFIG = CONFIG_DIR / 'model-scenes-v1.json'
NEWS_COLLECT = 'news_collect'
NEWS_ANALYSIS = 'news_analysis'
NEEDS_SEARCH = '采集需要能联网的模型：请在 模型配置 里给该模型选择联网方式（通义 / 智谱 / Kimi / OpenAI / Claude / 豆包）'


@lru_cache
def config() -> dict:
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def scenes() -> list[dict]:
    return list(config()['scenes'])


def scene(key: str) -> dict:
    for s in scenes():
        if s['key'] == key:
            return s
    raise Invalid(f'没有这个场景：{key}')


def provider_config(row: LlmProvider) -> llm.ProviderConfig:
    return llm.ProviderConfig(row.provider_key, row.name, row.base_url, row.model, row.api_key_env,
                              json.loads(row.options_json or '{}'), row.search_mode or 'none',
                              api_key_ciphertext=row.api_key_ciphertext, row_id=row.id)


def workspace_default(db, workspace_id) -> LlmProvider | None:
    return db.scalar(select(LlmProvider).where(LlmProvider.workspace_id == workspace_id, LlmProvider.enabled.is_(True))
                     .order_by(LlmProvider.is_default.desc(), LlmProvider.created_at).limit(1))


def _binding(db, workspace_id, key) -> LlmSceneBinding | None:
    return db.scalar(select(LlmSceneBinding).where(LlmSceneBinding.workspace_id == workspace_id,
                                                   LlmSceneBinding.scene_key == key))


def resolve_row(db, workspace_id, key: str) -> tuple[LlmProvider | None, str]:
    """(row, source) with source 'scene' | 'workspace_default' | 'builtin' (row is None)."""
    scene(key)
    b = _binding(db, workspace_id, key)
    if b is not None:
        row = db.get(LlmProvider, b.provider_id)
        if row is not None and row.enabled and row.workspace_id == workspace_id:
            return row, 'scene'
    row = workspace_default(db, workspace_id)
    return (row, 'workspace_default') if row is not None else (None, 'builtin')


def resolve(db, workspace_id, key: str) -> llm.ProviderConfig:
    row, _ = resolve_row(db, workspace_id, key)
    return provider_config(row) if row is not None else llm.default_provider()


def search_row_for_collect(db, workspace_id) -> LlmProvider:
    """The model a collector without its own model will use; must be able to search the web."""
    row, _ = resolve_row(db, workspace_id, NEWS_COLLECT)
    if row is None or (row.search_mode or 'none') == 'none':
        raise Invalid('场景“资讯采集”当前没有能联网的模型：请在 模型配置 › 按场景配置模型 里为“资讯采集”选择能联网的模型，或给定时器单独选模型')
    return row


# ---------------------------------------------------------------- page / API

def _label(row: LlmProvider | None) -> dict | None:
    if row is None:
        return None
    cfg = provider_config(row)
    return {'id': row.id, 'name': row.name, 'model': row.model, 'search_mode': row.search_mode or 'none',
            'key_configured': cfg.configured, 'key_source': cfg.key_source}


def view(db, workspace_id) -> dict:
    builtin = llm.default_provider()
    items = []
    for s in scenes():
        b = _binding(db, workspace_id, s['key'])
        row, source = resolve_row(db, workspace_id, s['key'])
        effective = _label(row) or {'id': None, 'name': f'{builtin.name}（内置默认）', 'model': builtin.model,
                                    'search_mode': builtin.search_mode, 'key_configured': builtin.configured,
                                    'key_source': builtin.key_source}
        problem = None
        if b is not None and source != 'scene':
            problem = '绑定的模型已停用或已删除，暂时改用默认模型'
        if s['requires_search'] and effective['search_mode'] == 'none':
            problem = '当前生效的模型不能联网，采集会失败：请选择能联网的模型'
        elif not effective['key_configured']:
            problem = problem or '当前生效的模型没有可用的 API Key'
        items.append({'key': s['key'], 'label': s['label'], 'description': s['description'],
                      'requires_search': bool(s['requires_search']), 'provider_id': b.provider_id if b else None,
                      'source': source, 'effective': effective, 'problem': problem})
    return {'version': config()['version'], 'items': items}


def save(db, workspace_id, actor_id, bindings: dict[str, str | None]) -> dict:
    """Replace this workspace's scene bindings; ``None`` = use the default model."""
    known = {s['key']: s for s in scenes()}
    unknown = [k for k in bindings if k not in known]
    if unknown:
        raise Invalid(f"没有这些场景：{'、'.join(unknown)}")
    for key, provider_id in bindings.items():
        if not provider_id:
            continue
        row = db.get(LlmProvider, provider_id)
        if row is None or row.workspace_id != workspace_id:
            raise Invalid(f"场景“{known[key]['label']}”选择的模型不存在")
        if not row.enabled:
            raise Invalid(f"场景“{known[key]['label']}”选择的模型已停用")
        if known[key]['requires_search'] and (row.search_mode or 'none') == 'none':
            raise Invalid(f"场景“{known[key]['label']}”需要能联网的模型，{row.name} 没有设置联网方式")
    now = datetime.now(timezone.utc)
    changed = {}
    for key in known:
        provider_id = bindings.get(key) or None
        b = _binding(db, workspace_id, key)
        before = b.provider_id if b else None
        if provider_id is None and b is not None:
            db.delete(b)
        elif provider_id is not None and b is None:
            db.add(LlmSceneBinding(workspace_id=workspace_id, scene_key=key, provider_id=provider_id,
                                   updated_by=actor_id, updated_at=now))
        elif provider_id is not None and b.provider_id != provider_id:
            b.provider_id, b.updated_by, b.updated_at = provider_id, actor_id, now
        if before != provider_id:
            changed[key] = {'from': before, 'to': provider_id}
    db.flush()
    record(db, workspace_id, actor_id, 'admin.model_scene.saved', 'model_scene', config()['policy_key'],
           {'bindings': {k: (bindings.get(k) or None) for k in known}, 'changed': changed})
    return view(db, workspace_id)


def scenes_using(db, workspace_id, provider_id) -> list[dict]:
    rows = db.scalars(select(LlmSceneBinding).where(LlmSceneBinding.workspace_id == workspace_id,
                                                    LlmSceneBinding.provider_id == provider_id)).all()
    known = {s['key']: s for s in scenes()}
    return [known[r.scene_key] for r in rows if r.scene_key in known]
