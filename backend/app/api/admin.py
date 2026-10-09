"""后台设置 API: 数据源、资讯源、模型配置、告警发送."""
import json
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select, update

from app.api.deps import Principal, require, require_any
from app.core.errors import Conflict, Invalid, NotFound
from app.core.uow import unit_of_work
from app.db import get_db
from app.domains.news import llm, model_scenes
from app.domains.news.collector_policy import policy as collector_policy
from app.models.news import LlmProvider, NewsFeed
from app.domains.platform.transactions import canonical, record
from app.domains.market_data import registry

router = APIRouter(prefix='/api/admin', tags=['后台设置'])

ADMIN = ('source.manage', 'system.configure')


@router.get('/sources')
def sources(principal: Principal = Depends(require_any(*ADMIN))) -> list[dict]:
    return [s.as_dict() for s in registry.all_sources()]


# ------------------------------------------------------------------ 资讯源

class FeedIn(BaseModel):
    feed_key: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    kind: str = Field('rss', pattern='^(rss|excel_upload)$')
    url: str | None = Field(None, max_length=1000)
    schedule: str | None = Field(None, max_length=60)
    enabled: bool = True


def _feed(f: NewsFeed) -> dict:
    return {'id': f.id, 'feed_key': f.feed_key, 'name': f.name, 'kind': f.kind, 'url': f.url,
            'schedule': f.schedule, 'enabled': f.enabled, 'last_status': f.last_status,
            'last_run_at': f.last_run_at.isoformat() if f.last_run_at else None}


@router.get('/news-feeds')
def list_feeds(principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    return [_feed(f) for f in db.scalars(select(NewsFeed).where(NewsFeed.workspace_id == principal.workspace.id).order_by(NewsFeed.name)).all()]


@router.post('/news-feeds')
def create_feed(body: FeedIn, principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    with unit_of_work(db):
        if db.scalar(select(NewsFeed.id).where(NewsFeed.workspace_id == principal.workspace.id, NewsFeed.feed_key == body.feed_key)):
            raise Conflict('资讯源标识已存在')
        feed = NewsFeed(workspace_id=principal.workspace.id, config_json='{}', **body.model_dump())
        db.add(feed); db.flush()
        record(db, principal.workspace.id, principal.user.id, 'admin.news_feed.created', 'news_feed', feed.id, body.model_dump())
        out = _feed(feed)
    return out


@router.put('/news-feeds/{feed_id}')
def update_feed(feed_id: str, body: FeedIn, principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    with unit_of_work(db):
        feed = db.get(NewsFeed, feed_id)
        if feed is None or feed.workspace_id != principal.workspace.id:
            raise NotFound('没有该资讯源')
        for k, v in body.model_dump().items():
            setattr(feed, k, v)
        record(db, principal.workspace.id, principal.user.id, 'admin.news_feed.updated', 'news_feed', feed.id, body.model_dump())
        out = _feed(feed)
    return out


# ------------------------------------------------------------------ 模型配置

class ProviderIn(BaseModel):
    provider_key: str = Field(min_length=1, max_length=80, pattern=r'^[a-z0-9_\-]+$')
    name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=8, max_length=500, pattern=r'^https?://')
    model: str = Field(min_length=1, max_length=120)
    api_key_env: str | None = Field(None, max_length=120, pattern=r'^([A-Z][A-Z0-9_]*)?$',
                                    description='可选：密钥所在的环境变量名（页面保存的 Key 优先）')
    api_key: SecretStr | None = Field(None, max_length=500, json_schema_extra={'writeOnly': True},
                                      description='只写：在页面填写的 API Key，加密后入库，任何接口都不再返回；留空表示不修改')
    is_default: bool = False
    enabled: bool = True
    temperature: float = Field(0, ge=0, le=2)
    search_mode: str = Field('none', pattern='^(none|qwen_enable_search|zhipu_web_search|kimi_search|openai_web_search)$')


def _provider(p: LlmProvider) -> dict:
    cfg = model_scenes.provider_config(p)
    return {'id': p.id, 'provider_key': p.provider_key, 'name': p.name, 'base_url': p.base_url, 'model': p.model,
            'api_key_env': p.api_key_env, 'key_configured': cfg.configured, 'key_source': cfg.key_source,
            'key_saved': bool(p.api_key_ciphertext), 'key_hint': f'••••{p.api_key_hint}' if p.api_key_hint else None,
            'key_problem': cfg.key_problem, 'blocked': cfg.blocked, 'is_default': p.is_default,
            'enabled': p.enabled, 'options': json.loads(p.options_json or '{}'), 'search_mode': p.search_mode or 'none'}


@router.get('/llm-providers')
def list_providers(principal: Principal = Depends(require('model.configure')), db=Depends(get_db)):
    from app.core import secret_box
    rows = db.scalars(select(LlmProvider).where(LlmProvider.workspace_id == principal.workspace.id).order_by(LlmProvider.provider_key)).all()
    default = llm.default_provider()
    active = model_scenes.workspace_default(db, principal.workspace.id)
    return {'providers': [_provider(p) for p in rows],
            'builtin_default': {'provider_key': default.provider_key, 'name': default.name, 'base_url': default.base_url,
                                'model': default.model, 'api_key_env': default.api_key_env, 'key_configured': default.configured},
            'search_modes': {k: v['label'] for k, v in collector_policy()['search_modes'].items()},
            'presets': collector_policy()['provider_presets'],
            'secret_key_ready': secret_box.available(), 'secret_key_problem': secret_box.problem(),
            'active': active.provider_key if active else None}


def _host(url: str | None) -> str:
    return (urlsplit(url or '').hostname or '').lower()


def _save_provider(db, principal, body: ProviderIn, row: LlmProvider | None):
    from app.core import secret_box
    from app.core.secret_guard import base_url_problem, key_env_problem
    problem = base_url_problem(body.base_url) or (key_env_problem(body.api_key_env) if body.api_key_env else None)
    if problem:
        raise Invalid(problem)
    new_key = body.api_key.get_secret_value().strip() if body.api_key is not None else ''
    if body.api_key is not None and new_key and len(new_key) < 8:
        raise Invalid('API Key 太短，请检查是否粘贴完整')
    data = body.model_dump(exclude={'api_key'})
    data['api_key_env'] = data['api_key_env'] or None
    temperature = data.pop('temperature')
    if row is not None and row.api_key_ciphertext and not new_key and _host(row.base_url) != _host(body.base_url):
        raise Invalid('更换接口域名时请重新填写 API Key（已保存的 Key 只发往原来的域名），或先清除已保存的 Key')
    if row is not None and (not body.enabled or body.search_mode == 'none'):
        for s in model_scenes.scenes_using(db, principal.workspace.id, row.id):
            if not body.enabled:
                raise Invalid(f"场景“{s['label']}”正在使用这个模型，先在 按场景配置模型 里换掉再停用")
            if s['requires_search']:
                raise Invalid(f"场景“{s['label']}”需要联网，正在使用这个模型；先换掉场景的模型再取消联网方式")
    if new_key and not secret_box.available():
        raise Invalid(secret_box.problem() or secret_box.MISSING)
    if body.is_default:
        db.execute(update(LlmProvider).where(LlmProvider.workspace_id == principal.workspace.id).values(is_default=False))
    if row is None:
        if db.scalar(select(LlmProvider.id).where(LlmProvider.workspace_id == principal.workspace.id, LlmProvider.provider_key == body.provider_key)):
            raise Conflict('模型标识已存在')
        row = LlmProvider(workspace_id=principal.workspace.id, **data, options_json='{}')
        db.add(row)
        db.flush()  # the row id is bound into the ciphertext
    else:
        for k, v in data.items():
            setattr(row, k, v)
    if new_key:
        row.api_key_ciphertext = secret_box.encrypt(new_key, f'llm_provider:{row.id}')
        row.api_key_hint = new_key[-4:]
    row.options_json = canonical({'temperature': temperature})
    db.flush()
    # The key itself never goes into the audit record; only whether it was replaced.
    record(db, principal.workspace.id, principal.user.id, 'admin.llm_provider.saved', 'llm_provider', row.id,
           {**data, 'temperature': temperature, 'api_key_replaced': bool(new_key)})
    return _provider(row)


@router.post('/llm-providers')
def create_provider(body: ProviderIn, principal: Principal = Depends(require('model.configure')), db=Depends(get_db)):
    with unit_of_work(db):
        return _save_provider(db, principal, body, None)


@router.put('/llm-providers/{provider_id}')
def update_provider(provider_id: str, body: ProviderIn, principal: Principal = Depends(require('model.configure')), db=Depends(get_db)):
    with unit_of_work(db):
        return _save_provider(db, principal, body, _provider_in_ws(db, principal, provider_id))


def _provider_in_ws(db, principal, provider_id) -> LlmProvider:
    row = db.get(LlmProvider, provider_id)
    if row is None or row.workspace_id != principal.workspace.id:
        raise NotFound('没有该模型配置')
    return row


@router.delete('/llm-providers/{provider_id}/api-key')
def clear_provider_key(provider_id: str, principal: Principal = Depends(require('model.configure')), db=Depends(get_db)):
    """清除页面保存的 API Key（之后如设置了环境变量则改用环境变量）。"""
    with unit_of_work(db):
        row = _provider_in_ws(db, principal, provider_id)
        had = bool(row.api_key_ciphertext)
        row.api_key_ciphertext, row.api_key_hint = None, None
        db.flush()
        record(db, principal.workspace.id, principal.user.id, 'admin.llm_provider.key_cleared', 'llm_provider', row.id,
               {'provider_key': row.provider_key, 'had_saved_key': had})
        return _provider(row)


# ------------------------------------------------------------------ 按场景配置模型

class SceneBindingIn(BaseModel):
    scene: str = Field(min_length=1, max_length=60)
    provider_id: str | None = Field(None, max_length=36, description='不填 = 使用默认模型')


class SceneBindingsIn(BaseModel):
    bindings: list[SceneBindingIn] = Field(max_length=50)


class SceneModelOut(BaseModel):
    id: str | None
    name: str
    model: str
    search_mode: str
    key_configured: bool
    key_source: str


class SceneOut(BaseModel):
    key: str
    label: str
    description: str
    requires_search: bool
    provider_id: str | None
    source: str = Field(description='scene=场景绑定 | workspace_default=工作区默认模型 | builtin=内置默认')
    effective: SceneModelOut
    problem: str | None


class ScenesOut(BaseModel):
    version: int
    items: list[SceneOut]


@router.get('/model-scenes', response_model=ScenesOut)
def model_scene_list(principal: Principal = Depends(require('model.configure')), db=Depends(get_db)):
    """每个调用大模型的场景用哪个模型，以及当前实际生效的模型（不含任何密钥）。"""
    return model_scenes.view(db, principal.workspace.id)


@router.put('/model-scenes', response_model=ScenesOut)
def model_scene_save(body: SceneBindingsIn, principal: Principal = Depends(require('model.configure')), db=Depends(get_db)):
    """整体替换本工作区的场景绑定；没列出的场景改为使用默认模型。"""
    keys = [b.scene for b in body.bindings]
    if len(set(keys)) != len(keys):
        raise Invalid('同一个场景只能出现一次')
    with unit_of_work(db):
        return model_scenes.save(db, principal.workspace.id, principal.user.id,
                                 {b.scene: b.provider_id for b in body.bindings})


# ------------------------------------------------------------------ 告警发送

@router.get('/notify')
def notify_settings(principal: Principal = Depends(require('system.configure')), db=Depends(get_db)):
    from sqlalchemy import func
    from app.config import get_settings
    from app.models.monitoring import Notification
    from app.domains.monitoring.policy import policy as alert_policy, sender_address
    from app.domains.monitoring.service import recipients
    s = get_settings()
    counts = dict(db.execute(select(Notification.status, func.count()).where(
        Notification.workspace_id == principal.workspace.id, Notification.channel == 'email').group_by(Notification.status)).all())
    return {'sender': sender_address(), 'sender_name': alert_policy()['sender']['display_name'],
            'smtp_configured': bool(s.smtp_host), 'smtp_host': s.smtp_host or None, 'smtp_port': s.smtp_port,
            'smtp_starttls': s.smtp_starttls, 'recipient_roles': alert_policy()['recipient_roles'],
            'recipients': [{'login': u.login, 'name': u.display_name, 'email': st.email if st else None,
                            'email_enabled': st.email_enabled if st else True} for u, st in recipients(db, principal.workspace.id)],
            'email_counts': counts, 'policy': alert_policy()}
