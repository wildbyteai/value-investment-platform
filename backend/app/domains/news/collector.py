"""资讯采集定时器 + Skill: a collector is a prompt, a configured model that can search the web,
an optional skill (procedure the model follows) and a schedule.

A run asks the model for today's items as strict JSON, normalizes them into the same record
shape as the Excel/RSS feeds, then ingests (dedupe into events) and scores them exactly like
any other feed, so the human review flow is unchanged.

Never commits, except ``run_due`` which owns its own transactions per collector.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.errors import Conflict, Invalid, NotFound
from app.domains.news import agent, llm, model_scenes, service
from app.domains.news.collector_policy import policy
from app.models.news import AgentSkill, CollectorRun, CollectorTask, LlmProvider, NewsFeed
from app.domains.news.normalize import Record, parse_published
from app.domains.platform.transactions import canonical, record

OUTPUT_CONTRACT = """你是价值投资平台的资讯采集员。请用联网搜索完成用户交给你的采集任务。
现在是 {now}（{tz}）。

只收录真实存在、能给出原文链接的资讯，不要编造；拿不准的不要收录。
同一件事多个来源报道时只收录一条，选最权威的来源。
最多 {max_items} 条。没有符合要求的资讯就返回空列表。

最后只输出严格 JSON（不要任何解释文字），格式：
{{"items":[{{"title":"标题","summary":"核心内容摘要（2-4 句，含关键数字）","url":"原文链接","source":"来源媒体或机构","published_at":"YYYY-MM-DD HH:MM","company":"涉及的公司及代码，如 诺诚健华（688428.SH / 09969.HK），没有就留空","category":"行业或类别","note":"一句话解读，可留空"}}]}}"""

SKILL_BLOCK = """

请严格按照下面这个 Skill 的流程执行（Skill 名称：{name}）：
-----
{body}
-----"""


# ---------------------------------------------------------------- schedule

def _zone() -> ZoneInfo:
    return ZoneInfo(policy()['timezone'])


def validate_schedule(schedule: dict) -> dict:
    kind = schedule.get('type')
    if kind == 'daily':
        times = sorted({str(t).strip() for t in schedule.get('times') or []})
        if not times or not all(re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', t) for t in times):
            raise Invalid('每天执行时间格式应为 HH:MM，例如 08:30')
        weekdays = sorted({int(d) for d in schedule.get('weekdays') or range(1, 8)})
        if not weekdays or any(d < 1 or d > 7 for d in weekdays):
            raise Invalid('星期取值为 1（周一）到 7（周日）')
        return {'type': 'daily', 'times': times, 'weekdays': weekdays}
    if kind == 'interval':
        minimum = policy()['min_interval_minutes']
        try:
            minutes = int(schedule.get('minutes'))
        except (TypeError, ValueError):
            raise Invalid('间隔分钟数必须是整数')
        if minutes < minimum:
            raise Invalid(f'间隔不能少于 {minimum} 分钟')
        return {'type': 'interval', 'minutes': minutes}
    raise Invalid('执行周期只能是每天定时或固定间隔')


def next_run(schedule: dict, after: datetime) -> datetime:
    """First run strictly after ``after`` (aware), in UTC."""
    if schedule['type'] == 'interval':
        return (after + timedelta(minutes=schedule['minutes'])).astimezone(timezone.utc)
    zone = _zone()
    local = after.astimezone(zone)
    for day in range(0, 8):
        d = (local + timedelta(days=day)).date()
        if d.isoweekday() not in schedule['weekdays']:
            continue
        for t in schedule['times']:
            hh, mm = map(int, t.split(':'))
            candidate = datetime(d.year, d.month, d.day, hh, mm, tzinfo=zone)
            if candidate > local:
                return candidate.astimezone(timezone.utc)
    raise Invalid('无法计算下次执行时间')


def describe_schedule(schedule: dict) -> str:
    if schedule['type'] == 'interval':
        m = schedule['minutes']
        return f'每 {m // 60} 小时' if m % 60 == 0 else f'每 {m} 分钟'
    names = '一二三四五六日'
    days = schedule['weekdays']
    day_text = '每天' if len(days) == 7 else ('工作日' if days == [1, 2, 3, 4, 5] else '每周' + '、'.join(names[d - 1] for d in days))
    return f"{day_text} {'、'.join(schedule['times'])}"


# ---------------------------------------------------------------- skills

def skill_dict(s: AgentSkill, used_by: int = 0) -> dict:
    return {'id': s.id, 'skill_key': s.skill_key, 'name': s.name, 'description': s.description, 'body': s.body,
            'version': s.version, 'enabled': s.enabled, 'used_by': used_by,
            'updated_at': s.updated_at.isoformat() if s.updated_at else None}


def list_skills(db, workspace_id) -> list[dict]:
    rows = db.scalars(select(AgentSkill).where(AgentSkill.workspace_id == workspace_id).order_by(AgentSkill.name)).all()
    usage: dict[str, int] = {}
    for sid in db.scalars(select(CollectorTask.skill_id).where(CollectorTask.workspace_id == workspace_id,
                                                               CollectorTask.skill_id.is_not(None))).all():
        usage[sid] = usage.get(sid, 0) + 1
    return [skill_dict(s, usage.get(s.id, 0)) for s in rows]


def save_skill(db, workspace_id, actor_id, data: dict, skill_id: str | None = None) -> dict:
    if skill_id is None:
        if db.scalar(select(AgentSkill.id).where(AgentSkill.workspace_id == workspace_id, AgentSkill.skill_key == data['skill_key'])):
            raise Conflict('Skill 标识已存在')
        row = AgentSkill(workspace_id=workspace_id, version=1, **data)
        db.add(row)
    else:
        row = _skill(db, workspace_id, skill_id)
        if data['skill_key'] != row.skill_key and db.scalar(select(AgentSkill.id).where(
                AgentSkill.workspace_id == workspace_id, AgentSkill.skill_key == data['skill_key'])):
            raise Conflict('Skill 标识已存在')
        if data['body'] != row.body:
            row.version += 1  # runs record which version they followed
        for k, v in data.items():
            setattr(row, k, v)
    row.updated_by, row.updated_at = actor_id, datetime.now(timezone.utc)
    db.flush()
    record(db, workspace_id, actor_id, 'admin.skill.saved', 'agent_skill', row.id,
           {'skill_key': row.skill_key, 'version': row.version, 'enabled': row.enabled})
    return skill_dict(row)


def delete_skill(db, workspace_id, actor_id, skill_id) -> None:
    row = _skill(db, workspace_id, skill_id)
    if db.scalar(select(CollectorTask.id).where(CollectorTask.skill_id == row.id)):
        raise Conflict('还有采集定时器在用这个 Skill，先在定时器里换掉或停用 Skill')
    record(db, workspace_id, actor_id, 'admin.skill.deleted', 'agent_skill', row.id, {'skill_key': row.skill_key})
    db.delete(row)
    db.flush()


def _skill(db, workspace_id, skill_id) -> AgentSkill:
    row = db.get(AgentSkill, skill_id)
    if row is None or row.workspace_id != workspace_id:
        raise NotFound('没有该 Skill')
    return row


# ---------------------------------------------------------------- collectors

def _provider_row(db, workspace_id, provider_id) -> LlmProvider:
    row = db.get(LlmProvider, provider_id) if provider_id else None
    if row is None or row.workspace_id != workspace_id:
        raise Invalid('请选择一个已配置的模型')
    return row


def task_dict(db, t: CollectorTask) -> dict:
    schedule = json.loads(t.schedule_json)
    if t.provider_id:
        provider = db.get(LlmProvider, t.provider_id)
    else:
        provider, _ = model_scenes.resolve_row(db, t.workspace_id, model_scenes.NEWS_COLLECT)
    skill = db.get(AgentSkill, t.skill_id) if t.skill_id else None
    return {'id': t.id, 'name': t.name, 'prompt': t.prompt, 'provider_id': t.provider_id,
            'follows_scene': not t.provider_id,
            'provider': f'{provider.name} · {provider.model}' if provider else None,
            'search_mode': provider.search_mode if provider else None,
            'skill_id': t.skill_id, 'skill': skill.name if skill else None, 'feed_id': t.feed_id,
            'schedule': schedule, 'schedule_text': describe_schedule(schedule), 'enabled': t.enabled,
            'next_run_at': t.next_run_at.isoformat() if t.next_run_at else None,
            'last_run_at': t.last_run_at.isoformat() if t.last_run_at else None, 'last_status': t.last_status}


def list_tasks(db, workspace_id) -> list[dict]:
    rows = db.scalars(select(CollectorTask).where(CollectorTask.workspace_id == workspace_id).order_by(CollectorTask.created_at)).all()
    return [task_dict(db, t) for t in rows]


def save_task(db, workspace_id, actor_id, data: dict, task_id: str | None = None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    schedule = validate_schedule(data['schedule'])
    # A collector's own model is an override; without one it follows the 资讯采集 scene.
    if data.get('provider_id'):
        provider = _provider_row(db, workspace_id, data['provider_id'])
        if (provider.search_mode or 'none') == 'none':
            raise Invalid(model_scenes.NEEDS_SEARCH)
        provider_id = provider.id
    else:
        model_scenes.search_row_for_collect(db, workspace_id)
        provider_id = None
    if data.get('skill_id'):
        _skill(db, workspace_id, data['skill_id'])
    if task_id is None:
        feed = NewsFeed(workspace_id=workspace_id, feed_key=f"agent-{now.strftime('%Y%m%d%H%M%S%f')}",
                        name=data['name'], kind='agent', enabled=True, config_json='{}')
        db.add(feed)
        db.flush()
        row = CollectorTask(workspace_id=workspace_id, feed_id=feed.id, created_by=actor_id)
        db.add(row)
    else:
        row = _task(db, workspace_id, task_id)
        feed = db.get(NewsFeed, row.feed_id)
        feed.name = data['name']
    row.name, row.prompt = data['name'], data['prompt']
    row.provider_id, row.skill_id = provider_id, data.get('skill_id') or None
    row.schedule_json, row.enabled = canonical(schedule), data.get('enabled', True)
    row.next_run_at = next_run(schedule, now) if row.enabled else None
    row.updated_at = now
    feed.enabled = row.enabled
    feed.schedule = describe_schedule(schedule)[:60]
    db.flush()
    record(db, workspace_id, actor_id, 'admin.collector.saved', 'collector_task', row.id,
           {'name': row.name, 'provider_id': row.provider_id, 'skill_id': row.skill_id, 'schedule': schedule,
            'enabled': row.enabled})
    return task_dict(db, row)


def _task(db, workspace_id, task_id) -> CollectorTask:
    row = db.get(CollectorTask, task_id)
    if row is None or row.workspace_id != workspace_id:
        raise NotFound('没有该采集定时器')
    return row


def list_runs(db, workspace_id, task_id, limit=20) -> list[dict]:
    _task(db, workspace_id, task_id)
    rows = db.scalars(select(CollectorRun).where(CollectorRun.task_id == task_id)
                      .order_by(CollectorRun.started_at.desc()).limit(limit)).all()
    return [run_dict(r) for r in rows]


def run_dict(r: CollectorRun) -> dict:
    return {'id': r.id, 'trigger': r.trigger, 'status': r.status, 'model': r.model, 'search_mode': r.search_mode,
            'skill_key': r.skill_key, 'skill_version': r.skill_version, 'items_found': r.items_found,
            'stats': json.loads(r.stats_json or '{}'), 'error': r.error, 'output_excerpt': r.output_excerpt,
            'started_at': r.started_at.isoformat() if r.started_at else None,
            'finished_at': r.finished_at.isoformat() if r.finished_at else None}


# ---------------------------------------------------------------- run

def build_messages(task: CollectorTask, skill: AgentSkill | None, now: datetime) -> list[dict]:
    cfg = policy()
    system = OUTPUT_CONTRACT.format(now=now.astimezone(_zone()).strftime('%Y-%m-%d %H:%M'), tz=cfg['timezone'],
                                    max_items=cfg['max_items_per_run'])
    if skill is not None and skill.enabled:
        system += SKILL_BLOCK.format(name=skill.name, body=skill.body.strip())
    return [{'role': 'system', 'content': system}, {'role': 'user', 'content': task.prompt}]


def parse_items(content: str) -> list[Record]:
    text = (content or '').strip()
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end <= start:
        raise llm.LlmError('模型没有按要求返回 JSON')
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        raise llm.LlmError('模型返回的 JSON 无法解析')
    rows = data.get('items') if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise llm.LlmError('模型返回的 JSON 缺少 items 列表')
    out = []
    for row in rows[:policy()['max_items_per_run']]:
        if not isinstance(row, dict):
            continue
        title = str(row.get('title') or '').strip()
        if not title:
            continue
        url = str(row.get('url') or '').strip() or None
        if url and not re.match(r'^https?://', url):
            url = None
        out.append(Record(title=title[:500], summary=str(row.get('summary') or '').strip(),
                          source_text=(str(row.get('source') or '').strip() or None),
                          url=url, category=(str(row.get('category') or '').strip() or None),
                          company_hint=(str(row.get('company') or '').strip() or None),
                          note=(str(row.get('note') or '').strip() or None),
                          published_at=parse_published(row.get('published_at')), raw=row))
    return out


def run_task(db, workspace_id, task: CollectorTask, trigger='manual', actor_id=None, transport=None,
             now: datetime | None = None) -> dict:
    """Execute once. Failures are recorded on the run and the task, never raised."""
    now = now or datetime.now(timezone.utc)
    cfg = policy()
    if task.provider_id:
        provider_row = db.get(LlmProvider, task.provider_id)
        missing = '定时器选择的模型不存在或已停用'
    else:  # follow the 资讯采集 scene
        provider_row, _ = model_scenes.resolve_row(db, workspace_id, model_scenes.NEWS_COLLECT)
        missing = '定时器没有单独选模型，场景“资讯采集”也没有可用的模型：请在 模型配置 › 按场景配置模型 里设置'
    skill = db.get(AgentSkill, task.skill_id) if task.skill_id else None
    run = CollectorRun(workspace_id=workspace_id, task_id=task.id, trigger=trigger, status='running', started_at=now,
                       skill_key=skill.skill_key if skill else None, skill_version=skill.version if skill else None,
                       items_found=0, stats_json='{}', output_excerpt='')
    db.add(run)
    db.flush()
    stats: dict = {}
    try:
        if provider_row is None or not provider_row.enabled:
            raise llm.LlmError(missing)
        provider = service.provider_config(provider_row)
        run.model, run.search_mode = f'{provider.name}/{provider.model}', provider.search_mode
        if provider.search_mode == 'none':
            raise llm.LlmError(model_scenes.NEEDS_SEARCH)
        result = agent.chat(provider, build_messages(task, skill, now), transport=transport)
        run.output_excerpt = result.content[:cfg['output_excerpt_chars']]
        records = parse_items(result.content)
        run.items_found = len(records)
        feed = db.get(NewsFeed, task.feed_id)
        stats = service.ingest(db, workspace_id, feed, records, actor_id)
        stats['searches'] = result.searches
        if cfg['score_after_collect'] and stats['new_events'] + stats['merged_into_events']:
            stats['scoring'] = service.score_events(db, workspace_id, limit=cfg['max_items_per_run'], transport=transport)
        run.status = 'succeeded'
        task.last_status = f"成功：采到 {run.items_found} 条，新增 {stats['new_items']} 条，新事件 {stats['new_events']} 个"
    except llm.LlmError as exc:
        run.status, run.error = 'failed', str(exc)[:1000]
        task.last_status = f'失败：{exc}'[:300]
    run.stats_json = canonical(stats)
    run.finished_at = datetime.now(timezone.utc)
    task.last_run_at = now  # a manual run leaves the schedule alone; run_due moves next_run_at
    db.flush()
    record(db, workspace_id, actor_id, f'news.collector.{run.status}', 'collector_task', task.id,
           {'run_id': run.id, 'trigger': trigger, 'items_found': run.items_found, 'error': run.error})
    return run_dict(run)


def run_due(db_factory, now: datetime | None = None, transport=None) -> list[dict]:
    """Scheduler tick (``python -m app.jobs collect`` every few minutes). Each due collector is
    claimed with ``FOR UPDATE SKIP LOCKED`` and its next run moved forward before the model is
    called, so overlapping ticks never run the same collector twice."""
    now = now or datetime.now(timezone.utc)
    out = []
    while True:
        with db_factory() as db:
            task = db.scalar(select(CollectorTask).where(CollectorTask.enabled.is_(True), CollectorTask.next_run_at <= now)
                             .order_by(CollectorTask.next_run_at).limit(1).with_for_update(skip_locked=True))
            if task is None:
                return out
            due_at = task.next_run_at
            task.next_run_at = next_run(json.loads(task.schedule_json), max(now, due_at))
            db.commit()
            try:
                result = run_task(db, task.workspace_id, task, trigger='schedule', transport=transport, now=now)
                db.commit()
            except Exception as exc:  # keep the scheduler alive; the claim above already moved next_run_at
                db.rollback()
                result = {'status': 'failed', 'error': type(exc).__name__}
            out.append({'task': task.id, 'name': task.name, **{k: result.get(k) for k in ('status', 'items_found', 'error')}})
