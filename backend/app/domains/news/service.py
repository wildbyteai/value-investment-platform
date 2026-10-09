"""资讯雷达 service: ingest → dedupe into events → AI/rule company links → human review.

Never commits: callers wrap calls in ``unit_of_work``.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.errors import Conflict, Invalid, NotFound
from app.domains.news import llm
from app.domains.news.dedupe import same_event
from app.models.news import LlmProvider, NewsEvent, NewsEventCompany, NewsFeed, NewsItem
from app.domains.news.normalize import Record
from app.domains.news.policy import policy
from app.models.company import Company, Security
from app.domains.platform.transactions import canonical, record

# ---------------------------------------------------------------- feeds & ingest


def ensure_feed(db, workspace_id, feed_key, name=None, kind='excel_upload', url=None) -> NewsFeed:
    feed = db.scalar(select(NewsFeed).where(NewsFeed.workspace_id == workspace_id, NewsFeed.feed_key == feed_key))
    if feed is None:
        feed = NewsFeed(workspace_id=workspace_id, feed_key=feed_key, name=name or feed_key, kind=kind, url=url,
                        enabled=True, config_json='{}')
        db.add(feed)
        db.flush()
    return feed


def _find_event(db, workspace_id, rec: Record) -> NewsEvent | None:
    window = timedelta(days=policy()['dedupe']['window_days'])
    q = select(NewsEvent).where(NewsEvent.workspace_id == workspace_id)
    if rec.published_at:
        q = q.where((NewsEvent.last_published_at.is_(None)) | (NewsEvent.last_published_at >= rec.published_at - window))
    for event in db.scalars(q.order_by(NewsEvent.created_at.desc()).limit(500)).all():
        if same_event(rec.title, rec.published_at, event.fingerprint, event.last_published_at):
            return event
    return None


def ingest(db, workspace_id, feed: NewsFeed, records: list[Record], actor_id=None) -> dict:
    stats = {'received': len(records), 'new_items': 0, 'duplicate_items': 0, 'new_events': 0, 'merged_into_events': 0}
    for rec in records:
        h = rec.content_hash
        if db.scalar(select(NewsItem.id).where(NewsItem.workspace_id == workspace_id, NewsItem.content_hash == h)):
            stats['duplicate_items'] += 1
            continue
        event = _find_event(db, workspace_id, rec)
        if event is None:
            event = NewsEvent(workspace_id=workspace_id, title=rec.title, summary=rec.summary, category=rec.category,
                              fingerprint=rec.title, first_published_at=rec.published_at,
                              last_published_at=rec.published_at, item_count=0, ai_status='pending')
            db.add(event)
            db.flush()
            stats['new_events'] += 1
        else:
            stats['merged_into_events'] += 1
            if rec.published_at and (event.first_published_at is None or rec.published_at < event.first_published_at):
                event.first_published_at = rec.published_at
            if rec.published_at and (event.last_published_at is None or rec.published_at > event.last_published_at):
                event.last_published_at = rec.published_at
            if len(rec.summary) > len(event.summary):
                event.summary = rec.summary
            if event.ai_status != 'pending':
                event.ai_status = 'pending'  # new evidence: re-score, human decisions are kept
        event.item_count += 1
        db.add(NewsItem(workspace_id=workspace_id, feed_id=feed.id, event_id=event.id, title=rec.title,
                        summary=rec.summary, source_text=rec.source_text, url=rec.url, category=rec.category,
                        company_hint=rec.company_hint, note=rec.note, published_at=rec.published_at,
                        content_hash=h, raw_json=canonical(rec.raw)))
        db.flush()
        stats['new_items'] += 1
    feed.last_run_at = datetime.now(timezone.utc)
    feed.last_status = f"新增 {stats['new_items']} 条，重复 {stats['duplicate_items']} 条，新事件 {stats['new_events']} 个"
    record(db, workspace_id, actor_id, 'news.ingested', 'news_feed', feed.id, stats)
    return stats


# ---------------------------------------------------------------- company matching

def _ticker_key(ticker: str) -> str:
    m = re.match(r'0*(\d+)\.?([A-Za-z]*)', ticker.strip())
    return f'{m.group(1)}.{m.group(2).upper()}' if m else ticker.strip().upper()


def company_index(db) -> list[dict]:
    rows = []
    for company in db.scalars(select(Company).order_by(Company.name)).all():
        tickers = db.scalars(select(Security.ticker).where(Security.company_id == company.id)).all()
        rows.append({'id': company.id, 'name': company.name, 'tickers': list(tickers),
                     'ticker_keys': {_ticker_key(t) for t in tickers}})
    return rows


def watchlist(index: list[dict]) -> list[str]:
    return [f"{c['name']}（{' / '.join(c['tickers'])}）" if c['tickers'] else c['name'] for c in index]


def match_company(index: list[dict], label: str, ticker: str | None) -> str | None:
    keys = {_ticker_key(t) for t in re.findall(r'\d{4,6}\.[A-Za-z]{2}', f'{label} {ticker or ""}')}
    for c in index:
        if keys & c['ticker_keys']:
            return c['id']
    for c in index:
        if c['name'] and (c['name'] in label or label in c['name']):
            return c['id']
    return None


def _event_text(db, event: NewsEvent) -> str:
    items = db.scalars(select(NewsItem).where(NewsItem.event_id == event.id).order_by(NewsItem.published_at)).all()
    hints = sorted({i.company_hint for i in items if i.company_hint})
    parts = [f'标题：{event.title}', f'摘要：{event.summary[:1500]}']
    if hints:
        parts.append('来源标注的公司：' + '；'.join(hints))
    return '\n'.join(parts)


# ---------------------------------------------------------------- AI scoring

def resolve_provider(db, workspace_id) -> llm.ProviderConfig:
    """Model for 资讯研判打分 (scene ``news_analysis``): scene binding → workspace default → built-in."""
    from app.domains.news import model_scenes
    return model_scenes.resolve(db, workspace_id, model_scenes.NEWS_ANALYSIS)


def provider_config(row: LlmProvider) -> llm.ProviderConfig:
    from app.domains.news import model_scenes
    return model_scenes.provider_config(row)


def _rule_links(index, text) -> list[llm.ProposedLink]:
    fallback = Decimal(policy()['linking']['rule_fallback_relevance'])
    seen = {_ticker_key(t) for t in re.findall(r'\d{4,6}\.[A-Za-z]{2}', text)}
    out = []
    for c in index:
        if (c['name'] and c['name'] in text) or (seen & c['ticker_keys']):
            out.append(llm.ProposedLink(c['name'], (c['tickers'] or [None])[0], fallback, Decimal(0),
                                        '规则匹配：资讯中出现公司名称或代码；影响分待人工判断'))
    return out


def score_events(db, workspace_id, limit=20, transport=None, event_ids=None) -> dict:
    provider = resolve_provider(db, workspace_id)
    index = company_index(db)
    names = watchlist(index)
    q = select(NewsEvent).where(NewsEvent.workspace_id == workspace_id)
    q = q.where(NewsEvent.id.in_(event_ids)) if event_ids else q.where(NewsEvent.ai_status == 'pending')
    stats = {'events': 0, 'ai_scored': 0, 'rule_only': 0, 'links_added': 0, 'model': f'{provider.name}/{provider.model}', 'error': None}
    for event in db.scalars(q.order_by(NewsEvent.created_at).limit(limit)).all():
        stats['events'] += 1
        text = _event_text(db, event)
        try:
            links = llm.propose_links(provider, text, names, transport=transport)
            event.ai_status, event.ai_model, event.ai_error = 'scored', f'{provider.provider_key}/{provider.model}', None
            proposed_by = f'ai:{provider.provider_key}/{provider.model}'
            stats['ai_scored'] += 1
        except llm.LlmError as exc:
            links = _rule_links(index, text)
            event.ai_status, event.ai_model, event.ai_error = 'rule_only', None, str(exc)[:500]
            proposed_by = 'rule:name_or_ticker'
            stats['rule_only'] += 1
            stats['error'] = str(exc)
        existing = {l.company_label: l for l in db.scalars(select(NewsEventCompany).where(NewsEventCompany.event_id == event.id)).all()}
        for link in links:
            row = existing.get(link.company)
            if row is not None and row.status != 'proposed':
                continue  # never overwrite a human decision
            if row is None:
                row = NewsEventCompany(event_id=event.id, company_label=link.company, status='proposed')
                db.add(row)
                stats['links_added'] += 1
            row.company_id = match_company(index, link.company, link.ticker)
            row.ticker_hint, row.relevance, row.impact = link.ticker, link.relevance, link.impact
            row.rationale, row.proposed_by = link.rationale, proposed_by
        db.flush()
    return stats


# ---------------------------------------------------------------- human review

def review_link(db, workspace_id, link_id, actor_id, action, relevance=None, impact=None, company_id=None) -> NewsEventCompany:
    link = db.get(NewsEventCompany, link_id)
    event = db.get(NewsEvent, link.event_id) if link else None
    if link is None or event is None or event.workspace_id != workspace_id:
        raise NotFound('没有该资讯关联')
    if action not in ('confirm', 'reject'):
        raise Invalid('只能确认或驳回')
    if link.status != 'proposed' and not (link.status == 'confirmed' and action == 'reject') and not (link.status == 'rejected' and action == 'confirm'):
        raise Conflict('该关联已处理')
    cfg = policy()['linking']
    if relevance is not None:
        link.relevance = llm._clamp(relevance, *cfg['relevance_range'])
    if impact is not None:
        link.impact = llm._clamp(impact, *cfg['impact_range'])
    if company_id is not None:
        if db.get(Company, company_id) is None:
            raise Invalid('公司不存在')
        link.company_id = company_id
    if action == 'confirm' and link.company_id is None:
        raise Invalid('请先把关联对应到公司档案中的公司')
    if action == 'confirm' and (link.relevance is None or link.impact is None):
        raise Invalid('确认前需要关联度和影响分')
    link.status = 'confirmed' if action == 'confirm' else 'rejected'
    link.reviewed_by, link.reviewed_at = actor_id, datetime.now(timezone.utc)
    db.flush()
    record(db, workspace_id, actor_id, f'news.link.{link.status}', 'news_event_company', link.id,
           {'event_id': event.id, 'company_id': link.company_id, 'relevance': str(link.relevance),
            'impact': str(link.impact)})
    return link


def review_links_batch(db, workspace_id, link_ids: list[str], actor_id, action) -> dict:
    """Accept (or reject) the AI's proposals as they stand, many at once. A link that cannot be
    confirmed as-is (not matched to a company profile, already handled) is skipped with a reason
    instead of failing the whole batch; the researcher fixes those one by one."""
    if action not in ('confirm', 'reject'):
        raise Invalid('只能确认或驳回')
    names = company_names(db)
    done, skipped = [], []
    for link_id in dict.fromkeys(link_ids):
        link = db.get(NewsEventCompany, link_id)
        label = names.get(link.company_id, link.company_label) if link else None
        if link is not None and link.status != 'proposed':
            skipped.append({'id': link_id, 'company': label, 'reason': '已处理过'})
            continue
        try:
            with db.begin_nested():
                review_link(db, workspace_id, link_id, actor_id, action)
            done.append(link_id)
        except (NotFound, Invalid, Conflict) as exc:
            skipped.append({'id': link_id, 'company': label, 'reason': str(exc)})
    return {'action': action, 'done': done, 'skipped': skipped}


# ---------------------------------------------------------------- reads

def link_dict(link: NewsEventCompany, names: dict) -> dict:
    return {'id': link.id, 'company_id': link.company_id, 'company': names.get(link.company_id, link.company_label),
            'company_label': link.company_label, 'ticker_hint': link.ticker_hint,
            'relevance': None if link.relevance is None else float(link.relevance),
            'impact': None if link.impact is None else float(link.impact),
            'rationale': link.rationale, 'status': link.status, 'proposed_by': link.proposed_by,
            'reviewed_at': link.reviewed_at.isoformat() if link.reviewed_at else None}


def event_dict(db, event: NewsEvent, names: dict, items=False) -> dict:
    links = db.scalars(select(NewsEventCompany).where(NewsEventCompany.event_id == event.id)
                       .order_by(NewsEventCompany.relevance.desc().nullslast())).all()
    out = {'id': event.id, 'title': event.title, 'summary': event.summary, 'category': event.category,
           'first_published_at': event.first_published_at.isoformat() if event.first_published_at else None,
           'last_published_at': event.last_published_at.isoformat() if event.last_published_at else None,
           'item_count': event.item_count, 'ai_status': event.ai_status, 'ai_model': event.ai_model,
           'ai_error': event.ai_error, 'links': [link_dict(l, names) for l in links],
           'impact_score': max((float(l.impact) * float(l.relevance) for l in links
                                if l.status != 'rejected' and l.impact is not None and l.relevance is not None),
                               key=abs, default=None)}
    if items:
        rows = db.scalars(select(NewsItem).where(NewsItem.event_id == event.id).order_by(NewsItem.published_at)).all()
        feeds = {f.id: f.name for f in db.scalars(select(NewsFeed).where(NewsFeed.id.in_({r.feed_id for r in rows}))).all()} if rows else {}
        out['items'] = [{'id': r.id, 'feed': feeds.get(r.feed_id), 'title': r.title, 'summary': r.summary,
                         'source_text': r.source_text, 'url': r.url, 'company_hint': r.company_hint, 'note': r.note,
                         'published_at': r.published_at.isoformat() if r.published_at else None} for r in rows]
    return out


def company_names(db) -> dict:
    return dict(db.execute(select(Company.id, Company.name)).all())


def list_events(db, workspace_id, company_id=None, status=None, limit=50) -> list[dict]:
    q = select(NewsEvent).where(NewsEvent.workspace_id == workspace_id)
    if company_id:
        q = q.where(NewsEvent.id.in_(select(NewsEventCompany.event_id).where(
            NewsEventCompany.company_id == company_id, NewsEventCompany.status != 'rejected')))
    if status == 'needs_review':
        q = q.where(NewsEvent.id.in_(select(NewsEventCompany.event_id).where(NewsEventCompany.status == 'proposed')))
    names = company_names(db)
    rows = db.scalars(q.order_by(NewsEvent.last_published_at.desc().nullslast(), NewsEvent.created_at.desc()).limit(limit)).all()
    return [event_dict(db, e, names) for e in rows]


def get_event(db, workspace_id, event_id) -> dict:
    event = db.get(NewsEvent, event_id)
    if event is None or event.workspace_id != workspace_id:
        raise NotFound('没有该资讯事件')
    return event_dict(db, event, company_names(db), items=True)


# ---------------------------------------------------------------- scheduled feeds

def run_feed(db, workspace_id, feed: NewsFeed, transport=None, actor_id=None) -> dict:
    """Fetch an RSS/Atom feed. A fetch failure is recorded on the feed and returned as ``error``."""
    import httpx
    from app.domains.news.normalize import records_from_rss
    if feed.kind != 'rss' or not feed.url:
        raise Invalid('只有配置了地址的 RSS 源可以自动抓取；Excel 源请上传文件')
    try:
        from app.core.secret_guard import PublicOnlyTransport
        with httpx.Client(transport=transport or PublicOnlyTransport(), timeout=30, follow_redirects=True, max_redirects=5) as client:
            r = client.get(feed.url, headers={'User-Agent': 'value-investment-platform/1.0'})
            r.raise_for_status()
    except httpx.HTTPError as exc:
        feed.last_run_at, feed.last_status = datetime.now(timezone.utc), f'抓取失败：{type(exc).__name__}'
        db.flush()
        return {'error': feed.last_status}
    try:
        records = records_from_rss(r.text)
    except Exception:
        feed.last_run_at, feed.last_status = datetime.now(timezone.utc), '抓取失败：不是有效的 RSS/Atom'
        db.flush()
        return {'error': feed.last_status}
    return ingest(db, workspace_id, feed, records, actor_id)
