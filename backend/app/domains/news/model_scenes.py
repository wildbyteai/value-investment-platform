"""按场景配置模型：每个调用大模型的地方是一个“场景”（config/model-scenes-v1.json），
工作区可以给每个场景指定一个已配置的模型。

取用顺序：场景绑定的模型（启用中）→ 工作区默认模型（is_default 优先，其次最早添加的启用模型）
→ 内置默认（环境变量密钥）。采集定时器自己选了模型时，定时器的模型优先于场景。

推理强度（ADR 0016）：场景绑定里填的强度（只对绑定的那个模型生效）→ 模型自身 options.reasoning_effort
（旧配置，兼容）→ 场景对该模型/厂商的推荐强度（config recommended）→ 不发送；最后按模型允许的
强度过滤并按厂商映射（reasoning.py）。旧场景键 news_analysis 是 news_extract 的别名。

Never commits.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy import select

from app.core.errors import Invalid
from app.core.paths import CONFIG_DIR
from app.domains.news import llm, model_presets, reasoning
from app.domains.platform.transactions import record
from app.models.news import LlmProvider, LlmSceneBinding

CONFIG = CONFIG_DIR / 'model-scenes-v1.json'
NEWS_COLLECT = 'news_collect'
NEWS_EXTRACT = 'news_extract'
NEWS_REASSESS = 'news_reassess'
COMPANY_DIGEST = 'company_digest'
ZONE_REVIEW = 'zone_review'
NEWS_ANALYSIS = NEWS_EXTRACT  # old key (ADR 0015); resolves to news_extract
NEEDS_SEARCH = '采集需要能联网的模型：请在 模型配置 里给该模型选择联网方式（通义 / 智谱 / Kimi / OpenAI / Claude / 豆包）'


@lru_cache
def config() -> dict:
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def scenes() -> list[dict]:
    return list(config()['scenes'])


def canonical_key(key: str) -> str:
    """The current key for ``key`` (an old alias such as ``news_analysis`` maps to ``news_extract``)."""
    for s in scenes():
        if key == s['key'] or key in (s.get('aliases') or []):
            return s['key']
    raise Invalid(f'没有这个场景：{key}')


def scene(key: str) -> dict:
    key = canonical_key(key)
    return next(s for s in scenes() if s['key'] == key)


def recommended_effort(key: str, base_url: str | None, model: str | None) -> str | None:
    """The scene's recommended effort for this model: an entry for the same model name first, then
    the first entry for the same preset (vendor host); ``None`` when the scene recommends nothing
    for this vendor."""
    recs = scene(key).get('recommended') or []
    preset = reasoning.preset_key(base_url)
    for r in recs:
        if r.get('model') == model and (preset is None or r.get('preset') == preset):
            return r.get('reasoning_effort')
    for r in recs:
        if preset is not None and r.get('preset') == preset:
            return r.get('reasoning_effort')
    return None


def effort_for(key: str, cfg: llm.ProviderConfig, binding: 'LlmSceneBinding | None' = None) -> tuple[str | None, str]:
    """(requested effort before vendor mapping, source) with source
    'scene' | 'provider_options' | 'recommended' | 'none'. ``binding`` counts only when it binds
    this very model."""
    if binding is not None and binding.reasoning_effort and binding.provider_id == cfg.row_id:
        return binding.reasoning_effort, 'scene'
    own = (cfg.options or {}).get('reasoning_effort')
    if own:
        return own, 'provider_options'
    rec = recommended_effort(key, cfg.base_url, cfg.model)
    return (rec, 'recommended') if rec else (None, 'none')


def provider_config(row: LlmProvider) -> llm.ProviderConfig:
    return llm.ProviderConfig(row.provider_key, row.name, row.base_url, row.model, row.api_key_env,
                              json.loads(row.options_json or '{}'), row.search_mode or 'none',
                              api_key_ciphertext=row.api_key_ciphertext, row_id=row.id)


def workspace_default(db, workspace_id) -> LlmProvider | None:
    return db.scalar(select(LlmProvider).where(LlmProvider.workspace_id == workspace_id, LlmProvider.enabled.is_(True))
                     .order_by(LlmProvider.is_default.desc(), LlmProvider.created_at).limit(1))


def _binding(db, workspace_id, key) -> LlmSceneBinding | None:
    return db.scalar(select(LlmSceneBinding).where(LlmSceneBinding.workspace_id == workspace_id,
                                                   LlmSceneBinding.scene_key == canonical_key(key)))


def resolve_row(db, workspace_id, key: str) -> tuple[LlmProvider | None, str]:
    """(row, source) with source 'scene' | 'workspace_default' | 'builtin' (row is None)."""
    key = canonical_key(key)
    b = _binding(db, workspace_id, key)
    if b is not None:
        row = db.get(LlmProvider, b.provider_id)
        if row is not None and row.enabled and row.workspace_id == workspace_id:
            return row, 'scene'
    row = workspace_default(db, workspace_id)
    return (row, 'workspace_default') if row is not None else (None, 'builtin')


def with_effort(db, workspace_id, key: str, cfg: llm.ProviderConfig) -> llm.ProviderConfig:
    """``cfg`` with ``reasoning_effort`` resolved for scene ``key``."""
    cfg.reasoning_effort, _ = effort_for(key, cfg, _binding(db, workspace_id, key))
    return cfg


def resolve(db, workspace_id, key: str) -> llm.ProviderConfig:
    """The model (with its reasoning effort) scene ``key`` uses in this workspace."""
    row, _ = resolve_row(db, workspace_id, key)
    cfg = provider_config(row) if row is not None else llm.default_provider()
    return with_effort(db, workspace_id, key, cfg)


def provider_config_for_scene(db, workspace_id, key: str, row: LlmProvider) -> llm.ProviderConfig:
    """A specific model (e.g. a collector's own model) used for scene ``key``: effort per the scene."""
    return with_effort(db, workspace_id, key, provider_config(row))


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


def _recommended(s: dict) -> list[dict]:
    names = {p['provider_key']: p['name'] for p in model_presets.config()['presets']}
    return [{'preset': r['preset'], 'preset_name': names.get(r['preset'], r['preset']), 'model': r['model'],
             'reasoning_effort': r.get('reasoning_effort'), 'why': r.get('why', '')}
            for r in s.get('recommended') or []]


def view(db, workspace_id) -> dict:
    builtin = llm.default_provider()
    items = []
    for s in scenes():
        b = _binding(db, workspace_id, s['key'])
        row, source = resolve_row(db, workspace_id, s['key'])
        cfg = provider_config(row) if row is not None else builtin
        effective = _label(row) or {'id': None, 'name': f'{builtin.name}（内置默认）', 'model': builtin.model,
                                    'search_mode': builtin.search_mode, 'key_configured': builtin.configured,
                                    'key_source': builtin.key_source}
        effort, effort_source = effort_for(s['key'], cfg, b)
        problem = None
        if b is not None and source != 'scene':
            problem = '绑定的模型已停用或已删除，暂时改用默认模型'
        if s['requires_search'] and effective['search_mode'] == 'none':
            problem = '当前生效的模型不能联网，采集会失败：请选择能联网的模型'
        elif not effective['key_configured']:
            problem = problem or '当前生效的模型没有可用的 API Key'
        items.append({'key': s['key'], 'label': s['label'], 'description': s['description'],
                      'aliases': list(s.get('aliases') or []), 'status': s.get('status', 'active'),
                      'planned_in': s.get('planned_in'),
                      'requires_search': bool(s['requires_search']), 'provider_id': b.provider_id if b else None,
                      'reasoning_effort': b.reasoning_effort if b else None,
                      'source': source, 'effective': effective, 'problem': problem,
                      'effective_reasoning_effort': reasoning.effective(cfg.base_url, cfg.model, effort),
                      'effort_source': effort_source,
                      'allowed_efforts': reasoning.allowed_efforts(cfg.base_url, cfg.model),
                      'recommended': _recommended(s), 'cost_note': s.get('cost_note', '')})
    rows = db.scalars(select(LlmProvider).where(LlmProvider.workspace_id == workspace_id)).all()
    return {'version': config()['version'], 'efforts': list(reasoning.EFFORTS),
            'allowed_efforts_by_provider': {r.id: reasoning.allowed_efforts(r.base_url, r.model) for r in rows},
            'items': items}


def _normalize_bindings(bindings: dict) -> dict[str, tuple[str | None, str | None]]:
    """{scene: provider_id | None | {'provider_id', 'reasoning_effort'} | (provider_id, effort)} →
    {canonical scene: (provider_id, effort)}; old scene keys are mapped, duplicates rejected."""
    out: dict[str, tuple[str | None, str | None]] = {}
    unknown = []
    for key, value in bindings.items():
        try:
            canon = canonical_key(key)
        except Invalid:
            unknown.append(key)
            continue
        if canon in out:
            raise Invalid('同一个场景只能出现一次')
        if isinstance(value, dict):
            out[canon] = (value.get('provider_id') or None, value.get('reasoning_effort') or None)
        elif isinstance(value, tuple):
            out[canon] = (value[0] or None, value[1] or None)
        else:
            out[canon] = (value or None, None)
    if unknown:
        raise Invalid(f"没有这些场景：{'、'.join(unknown)}")
    return out


def save(db, workspace_id, actor_id, bindings: dict) -> dict:
    """Replace this workspace's scene bindings. A value is a provider id (``None`` = use the default
    model), or ``{'provider_id', 'reasoning_effort'}``; an effort needs a bound model and must be one
    the model allows (``reasoning.allowed_efforts``); ``None`` = the scene's recommended effort."""
    wanted = _normalize_bindings(bindings)
    known = {s['key']: s for s in scenes()}
    for key, (provider_id, effort) in wanted.items():
        label = known[key]['label']
        if effort and effort not in reasoning.EFFORTS:
            raise Invalid(f"场景“{label}”的推理强度只能是 {' / '.join(reasoning.EFFORTS)}")
        if not provider_id:
            if effort:
                raise Invalid(f"场景“{label}”设置推理强度时需要指定模型（使用默认模型时按场景推荐强度）")
            continue
        row = db.get(LlmProvider, provider_id)
        if row is None or row.workspace_id != workspace_id:
            raise Invalid(f"场景“{label}”选择的模型不存在")
        if not row.enabled:
            raise Invalid(f"场景“{label}”选择的模型已停用")
        if known[key]['requires_search'] and (row.search_mode or 'none') == 'none':
            raise Invalid(f"场景“{label}”需要能联网的模型，{row.name} 没有设置联网方式")
        if effort:
            allowed = reasoning.allowed_efforts(row.base_url, row.model)
            if not allowed:
                raise Invalid(f"场景“{label}”选择的模型 {row.name} · {row.model} 不支持设置推理强度")
            if effort not in allowed:
                raise Invalid(f"场景“{label}”选择的模型 {row.name} · {row.model} 不支持推理强度 {effort}，可选：{' / '.join(allowed)}")
    now = datetime.now(timezone.utc)
    changed = {}
    for key in known:
        provider_id, effort = wanted.get(key, (None, None))
        b = _binding(db, workspace_id, key)
        before = b.provider_id if b else None
        before_effort = b.reasoning_effort if b else None
        if provider_id is None and b is not None:
            db.delete(b)
        elif provider_id is not None and b is None:
            db.add(LlmSceneBinding(workspace_id=workspace_id, scene_key=key, provider_id=provider_id,
                                   reasoning_effort=effort, updated_by=actor_id, updated_at=now))
        elif provider_id is not None and (b.provider_id != provider_id or b.reasoning_effort != effort):
            b.provider_id, b.reasoning_effort, b.updated_by, b.updated_at = provider_id, effort, actor_id, now
        if before != provider_id:
            changed[key] = {'from': before, 'to': provider_id}
        if (before_effort or None) != (effort if provider_id else None):
            changed.setdefault(key, {})['reasoning_effort'] = {'from': before_effort, 'to': effort if provider_id else None}
    db.flush()
    record(db, workspace_id, actor_id, 'admin.model_scene.saved', 'model_scene', config()['policy_key'],
           {'bindings': {k: wanted.get(k, (None, None))[0] for k in known},
            'efforts': {k: wanted[k][1] for k in wanted if wanted[k][1]}, 'changed': changed})
    return view(db, workspace_id)


def scenes_using(db, workspace_id, provider_id) -> list[dict]:
    rows = db.scalars(select(LlmSceneBinding).where(LlmSceneBinding.workspace_id == workspace_id,
                                                    LlmSceneBinding.provider_id == provider_id)).all()
    known = {s['key']: s for s in scenes()}
    return [known[r.scene_key] for r in rows if r.scene_key in known]
