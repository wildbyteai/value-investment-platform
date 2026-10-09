"""预置采集定时器包：一个共用 Skill + 若干采集定时器，内容全部在 ``config/collector-presets-v1.json``。

导入是幂等的：Skill 按 ``skill_key``、定时器按名称在本工作区里查，已存在的跳过，不覆盖管理员改过的内容。
新建走 ``collector.save_skill`` / ``collector.save_task``，所以校验（周期、必须能联网的模型）和审计与手工新建一致。

Never commits.
"""
from __future__ import annotations

import json
from functools import lru_cache

from sqlalchemy import select

from app.core.errors import Invalid
from app.core.paths import CONFIG_DIR
from app.domains.news import collector
from app.models.news import AgentSkill, CollectorTask
from app.domains.platform.transactions import record

CONFIG = CONFIG_DIR / 'collector-presets-v1.json'


@lru_cache
def presets() -> dict:
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def _installed(db, workspace_id) -> tuple[AgentSkill | None, dict[str, str]]:
    cfg = presets()
    skill = db.scalar(select(AgentSkill).where(AgentSkill.workspace_id == workspace_id,
                                               AgentSkill.skill_key == cfg['skill']['skill_key']))
    names = [t['name'] for t in cfg['tasks']]
    rows = db.execute(select(CollectorTask.name, CollectorTask.id).where(
        CollectorTask.workspace_id == workspace_id, CollectorTask.name.in_(names))).all()
    return skill, {name: tid for name, tid in rows}


def list_presets(db, workspace_id) -> dict:
    """The pack with what is already in this workspace (matched by skill_key / collector name)."""
    cfg = presets()
    skill, tasks = _installed(db, workspace_id)
    items = []
    for t in cfg['tasks']:
        schedule = collector.validate_schedule(t['schedule'])
        items.append({'key': t['key'], 'name': t['name'], 'prompt': t['prompt'], 'merged_from': t.get('merged_from', []),
                      'schedule': schedule, 'schedule_text': collector.describe_schedule(schedule),
                      'installed': t['name'] in tasks, 'task_id': tasks.get(t['name'])})
    s = cfg['skill']
    return {'version': cfg['version'], 'name': cfg['name'], 'description': cfg.get('description', ''),
            'skill': {'skill_key': s['skill_key'], 'name': s['name'], 'description': s.get('description', ''),
                      'installed': skill is not None, 'skill_id': skill.id if skill else None},
            'items': items}


def install(db, workspace_id, actor_id, provider_id, keys: list[str] | None = None) -> dict:
    """Create the shared skill and the selected collectors that are missing; skip the rest."""
    cfg = presets()
    known = [t['key'] for t in cfg['tasks']]
    wanted = known if not keys else list(dict.fromkeys(keys))
    unknown = [k for k in wanted if k not in known]
    if unknown:
        raise Invalid(f"没有这些预置任务：{'、'.join(unknown)}")
    # Check the model up front, so a non-search model is rejected even when everything is already installed.
    provider = collector._provider_row(db, workspace_id, provider_id)
    if (provider.search_mode or 'none') == 'none':
        raise Invalid('采集需要能联网的模型：请在 模型配置 里给该模型选择联网方式（通义 / 智谱 / Kimi / OpenAI）')

    skill, existing = _installed(db, workspace_id)
    skill_created = False
    if skill is None:
        s = cfg['skill']
        saved = collector.save_skill(db, workspace_id, actor_id, {
            'skill_key': s['skill_key'], 'name': s['name'], 'description': s.get('description', ''),
            'body': s['body'], 'enabled': True})
        skill_id, skill_created = saved['id'], True
    else:
        skill_id = skill.id

    created, skipped = [], []
    for t in cfg['tasks']:
        if t['key'] not in wanted:
            continue
        if t['name'] in existing:
            skipped.append({'key': t['key'], 'name': t['name'], 'task_id': existing[t['name']]})
            continue
        row = collector.save_task(db, workspace_id, actor_id, {
            'name': t['name'], 'prompt': t['prompt'], 'provider_id': provider.id, 'skill_id': skill_id,
            'schedule': t['schedule'], 'enabled': True})
        created.append({'key': t['key'], 'name': t['name'], 'task_id': row['id']})
    record(db, workspace_id, actor_id, 'admin.collector.presets_installed', 'collector_preset', cfg['policy_key'],
           {'version': cfg['version'], 'provider_id': provider.id, 'skill_created': skill_created,
            'created': [c['key'] for c in created], 'skipped': [s['key'] for s in skipped]})
    return {'version': cfg['version'], 'skill_id': skill_id, 'skill_created': skill_created,
            'created': created, 'skipped': skipped}
