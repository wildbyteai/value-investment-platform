"""后台设置 API: 数据源、资讯源、模型配置、告警发送."""
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from app.api.deps import Principal, require, require_any
from app.core.errors import Conflict, Invalid, NotFound
from app.core.uow import unit_of_work
from app.db import get_db
from app.domains.news import llm
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
    api_key_env: str = Field(min_length=1, max_length=120, pattern=r'^[A-Z][A-Z0-9_]*$')
    is_default: bool = False
    enabled: bool = True
    temperature: float = Field(0, ge=0, le=2)
    search_mode: str = Field('none', pattern='^(none|qwen_enable_search|zhipu_web_search|kimi_search|openai_web_search)$')


def _provider(p: LlmProvider) -> dict:
    cfg = llm.ProviderConfig(p.provider_key, p.name, p.base_url, p.model, p.api_key_env)
    return {'id': p.id, 'provider_key': p.provider_key, 'name': p.name, 'base_url': p.base_url, 'model': p.model,
            'api_key_env': p.api_key_env, 'key_configured': cfg.configured, 'blocked': cfg.blocked, 'is_default': p.is_default,
            'enabled': p.enabled, 'options': json.loads(p.options_json or '{}'), 'search_mode': p.search_mode or 'none'}


@router.get('/llm-providers')
def list_providers(principal: Principal = Depends(require('model.configure')), db=Depends(get_db)):
    rows = db.scalars(select(LlmProvider).where(LlmProvider.workspace_id == principal.workspace.id).order_by(LlmProvider.provider_key)).all()
    default = llm.default_provider()
    return {'providers': [_provider(p) for p in rows],
            'builtin_default': {'provider_key': default.provider_key, 'name': default.name, 'base_url': default.base_url,
                                'model': default.model, 'api_key_env': default.api_key_env, 'key_configured': default.configured},
            'search_modes': {k: v['label'] for k, v in collector_policy()['search_modes'].items()},
            'presets': collector_policy()['provider_presets'],
            'active': None if not rows else next((p.provider_key for p in sorted(rows, key=lambda r: (not r.is_default, r.created_at)) if p.enabled), None)}


def _save_provider(db, principal, body: ProviderIn, row: LlmProvider | None):
    from app.core.secret_guard import provider_problem
    problem = provider_problem(body.base_url, body.api_key_env)
    if problem:
        raise Invalid(problem)
    data = body.model_dump()
    temperature = data.pop('temperature')
    if body.is_default:
        db.execute(update(LlmProvider).where(LlmProvider.workspace_id == principal.workspace.id).values(is_default=False))
    if row is None:
        if db.scalar(select(LlmProvider.id).where(LlmProvider.workspace_id == principal.workspace.id, LlmProvider.provider_key == body.provider_key)):
            raise Conflict('模型标识已存在')
        row = LlmProvider(workspace_id=principal.workspace.id, **data, options_json='{}')
        db.add(row)
    else:
        for k, v in data.items():
            setattr(row, k, v)
    row.options_json = canonical({'temperature': temperature})
    db.flush()
    record(db, principal.workspace.id, principal.user.id, 'admin.llm_provider.saved', 'llm_provider', row.id,
           {**data, 'temperature': temperature})
    return _provider(row)


@router.post('/llm-providers')
def create_provider(body: ProviderIn, principal: Principal = Depends(require('model.configure')), db=Depends(get_db)):
    with unit_of_work(db):
        return _save_provider(db, principal, body, None)


@router.put('/llm-providers/{provider_id}')
def update_provider(provider_id: str, body: ProviderIn, principal: Principal = Depends(require('model.configure')), db=Depends(get_db)):
    with unit_of_work(db):
        row = db.get(LlmProvider, provider_id)
        if row is None or row.workspace_id != principal.workspace.id:
            raise NotFound('没有该模型配置')
        return _save_provider(db, principal, body, row)


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
