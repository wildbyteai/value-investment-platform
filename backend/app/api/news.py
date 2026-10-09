"""资讯雷达 API."""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import Principal, require, require_any
from app.core.errors import Conflict, Invalid, NotFound
from app.core.uow import unit_of_work
from app.db import get_db
from app.domains.news import service
from app.models.news import NewsFeed
from app.domains.news.normalize import feed_key_from_filename, records_from_excel

router = APIRouter(prefix='/api/news', tags=['资讯雷达'])

WRITE = ('source.manage', 'analysis.override')
REVIEW = ('analysis.override', 'quality.correct')
MAX_UPLOAD = 5 * 1024 * 1024


class LinkOut(BaseModel):
    alerts: int | None = None
    id: str
    company_id: str | None
    company: str
    company_label: str
    ticker_hint: str | None
    relevance: float | None
    impact: float | None
    rationale: str
    status: str
    proposed_by: str
    reviewed_at: str | None


class ItemOut(BaseModel):
    id: str
    feed: str | None
    title: str
    summary: str
    source_text: str | None
    url: str | None
    company_hint: str | None
    note: str | None
    published_at: str | None


class EventOut(BaseModel):
    id: str
    title: str
    summary: str
    category: str | None
    first_published_at: str | None
    last_published_at: str | None
    item_count: int
    ai_status: str
    ai_model: str | None
    ai_error: str | None
    impact_score: float | None
    links: list[LinkOut]
    items: list[ItemOut] | None = None


@router.get('/events', response_model=list[EventOut])
def events(company_id: str | None = None, status: str | None = None, limit: int = 50,
           principal: Principal = Depends(require('research.read')), db=Depends(get_db)):
    return service.list_events(db, principal.workspace.id, company_id, status, max(1, min(limit, 200)))


@router.get('/events/{event_id}', response_model=EventOut)
def event(event_id: str, principal: Principal = Depends(require('research.read')), db=Depends(get_db)):
    return service.get_event(db, principal.workspace.id, event_id)


@router.post('/import')
async def import_files(files: list[UploadFile] = File(...), score: bool = Form(True),
                       principal: Principal = Depends(require_any(*WRITE)), db=Depends(get_db)):
    """Upload one or more daily Excel files; the feed is named after the file."""
    results = []
    with unit_of_work(db):
        for upload in files:
            data = await upload.read()
            if len(data) > MAX_UPLOAD:
                raise Invalid(f'{upload.filename} 超过 5MB')
            try:
                records = records_from_excel(data)
            except Exception:
                raise Invalid(f'{upload.filename} 不是可读取的 Excel 文件')
            key, name = feed_key_from_filename(upload.filename or 'upload.xlsx')
            feed = service.ensure_feed(db, principal.workspace.id, key, name)
            results.append({'file': upload.filename, 'feed': feed.name,
                            **service.ingest(db, principal.workspace.id, feed, records, principal.user.id)})
    scoring = None
    if score:
        with unit_of_work(db):
            scoring = service.score_events(db, principal.workspace.id)
    return {'files': results, 'scoring': scoring}


class ScoreIn(BaseModel):
    event_ids: list[str] | None = None
    limit: int = Field(20, ge=1, le=100)


@router.post('/score')
def score(body: ScoreIn, principal: Principal = Depends(require_any(*WRITE)), db=Depends(get_db)):
    with unit_of_work(db):
        return service.score_events(db, principal.workspace.id, body.limit, event_ids=body.event_ids)


class ReviewIn(BaseModel):
    action: str
    relevance: float | None = None
    impact: float | None = None
    company_id: str | None = None


@router.post('/links/{link_id}/review', response_model=LinkOut)
def review(link_id: str, body: ReviewIn, principal: Principal = Depends(require_any(*REVIEW)), db=Depends(get_db)):
    with unit_of_work(db):
        link = service.review_link(db, principal.workspace.id, link_id, principal.user.id, body.action,
                                   body.relevance, body.impact, body.company_id)
        out = service.link_dict(link, service.company_names(db))
    if out['status'] == 'confirmed':
        # A confirmed ball goes straight to the monitor: alert only if it lands in the strike zone.
        from app.domains.monitoring import service as monitoring
        with unit_of_work(db):
            out['alerts'] = monitoring.scan_news(db, principal.workspace.id, link_ids=[link_id])['alerts']
    return out


class BatchReviewIn(BaseModel):
    action: str
    link_ids: list[str] = Field(..., min_length=1, max_length=500)


@router.post('/links/review-batch')
def review_batch(body: BatchReviewIn, principal: Principal = Depends(require_any(*REVIEW)), db=Depends(get_db)):
    """批量确认 / 驳回 AI 预判结果（按 AI 给出的公司、关联度、影响分原样确认）。"""
    with unit_of_work(db):
        out = service.review_links_batch(db, principal.workspace.id, body.link_ids, principal.user.id, body.action)
    out['alerts'] = []
    if body.action == 'confirm' and out['done']:
        from app.domains.monitoring import service as monitoring
        with unit_of_work(db):
            out['alerts'] = monitoring.scan_news(db, principal.workspace.id, link_ids=out['done'])['alerts']
    return out


@router.post('/feeds/{feed_id}/run')
def run_feed(feed_id: str, principal: Principal = Depends(require_any(*WRITE)), db=Depends(get_db)):
    feed = db.get(NewsFeed, feed_id)
    if feed is None or feed.workspace_id != principal.workspace.id:
        raise NotFound('没有该资讯源')
    with unit_of_work(db):
        stats = service.run_feed(db, principal.workspace.id, feed, actor_id=principal.user.id)
    if stats.get('error'):
        raise Conflict(stats['error'])
    with unit_of_work(db):
        scoring = service.score_events(db, principal.workspace.id)
    return {**stats, 'scoring': scoring}


@router.get('/feeds')
def feeds(principal: Principal = Depends(require_any('research.read', 'source.manage', 'system.configure')), db=Depends(get_db)):
    rows = db.scalars(select(NewsFeed).where(NewsFeed.workspace_id == principal.workspace.id).order_by(NewsFeed.name)).all()
    return [{'id': f.id, 'feed_key': f.feed_key, 'name': f.name, 'kind': f.kind, 'url': f.url, 'schedule': f.schedule,
             'enabled': f.enabled, 'last_run_at': f.last_run_at.isoformat() if f.last_run_at else None,
             'last_status': f.last_status} for f in rows]
