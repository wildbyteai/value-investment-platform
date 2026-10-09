"""采集定时器与 Skill 维护 API (后台设置)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import Principal, require_any
from app.core.paging import PageParams, page, page_params
from app.core.uow import unit_of_work
from app.db import get_db
from app.domains.news import collector, collector_presets

router = APIRouter(prefix='/api/admin', tags=['后台设置'])

ADMIN = ('source.manage', 'system.configure')


class SkillIn(BaseModel):
    skill_key: str = Field(min_length=1, max_length=80, pattern=r'^[a-z0-9_\-]+$')
    name: str = Field(min_length=1, max_length=200)
    description: str = Field('', max_length=2000)
    body: str = Field(min_length=1, max_length=20000)
    enabled: bool = True


class ScheduleIn(BaseModel):
    type: str = Field(pattern='^(daily|interval)$')
    times: list[str] | None = None
    weekdays: list[int] | None = None
    minutes: int | None = None


class CollectorIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    prompt: str = Field(min_length=1, max_length=20000)
    provider_id: str = Field(min_length=1, max_length=36)
    skill_id: str | None = Field(None, max_length=36)
    schedule: ScheduleIn
    enabled: bool = True


class PresetInstallIn(BaseModel):
    provider_id: str = Field(min_length=1, max_length=36, description='用哪个能联网的模型执行这些定时器')
    keys: list[str] | None = Field(None, max_length=50, description='只导入这些预置任务（不填则全部）')


class PresetScheduleOut(BaseModel):
    type: str
    times: list[str] | None = None
    weekdays: list[int] | None = None
    minutes: int | None = None


class PresetTaskOut(BaseModel):
    key: str
    name: str
    prompt: str
    merged_from: list[str]
    schedule: PresetScheduleOut
    schedule_text: str
    installed: bool
    task_id: str | None


class PresetSkillOut(BaseModel):
    skill_key: str
    name: str
    description: str
    installed: bool
    skill_id: str | None


class PresetListOut(BaseModel):
    version: int
    name: str
    description: str
    skill: PresetSkillOut
    items: list[PresetTaskOut]
    total: int
    limit: int
    offset: int


class PresetRef(BaseModel):
    key: str
    name: str
    task_id: str


class PresetInstallOut(BaseModel):
    version: int
    skill_id: str
    skill_created: bool
    created: list[PresetRef]
    skipped: list[PresetRef]


# ------------------------------------------------------------------ Skill

@router.get('/skills')
def skills(principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    return collector.list_skills(db, principal.workspace.id)


@router.post('/skills')
def create_skill(body: SkillIn, principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    with unit_of_work(db):
        return collector.save_skill(db, principal.workspace.id, principal.user.id, body.model_dump())


@router.put('/skills/{skill_id}')
def update_skill(skill_id: str, body: SkillIn, principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    with unit_of_work(db):
        return collector.save_skill(db, principal.workspace.id, principal.user.id, body.model_dump(), skill_id)


@router.delete('/skills/{skill_id}')
def delete_skill(skill_id: str, principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    with unit_of_work(db):
        collector.delete_skill(db, principal.workspace.id, principal.user.id, skill_id)
    return {'deleted': skill_id}


# ------------------------------------------------------------------ 采集定时器

@router.get('/collectors')
def collectors(principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    return collector.list_tasks(db, principal.workspace.id)


@router.get('/collectors/options')
def collector_options(principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    """Models and skills a collector can pick (no key values, only whether each key is set)."""
    from sqlalchemy import select
    from app.domains.news import service
    from app.domains.news.collector_policy import policy
    from app.models.news import LlmProvider
    rows = db.scalars(select(LlmProvider).where(LlmProvider.workspace_id == principal.workspace.id,
                                                LlmProvider.enabled.is_(True)).order_by(LlmProvider.name)).all()
    labels = {k: v['label'] for k, v in policy()['search_modes'].items()}
    return {'providers': [{'id': p.id, 'name': p.name, 'model': p.model, 'search_mode': p.search_mode or 'none',
                           'search_label': labels.get(p.search_mode or 'none'),
                           'key_configured': service.provider_config(p).configured} for p in rows],
            'skills': [{'id': s['id'], 'name': s['name'], 'enabled': s['enabled']} for s in collector.list_skills(db, principal.workspace.id)],
            'min_interval_minutes': policy()['min_interval_minutes'], 'timezone': policy()['timezone']}


@router.get('/collectors/presets', response_model=PresetListOut)
def collector_presets_list(params: PageParams = Depends(page_params), principal: Principal = Depends(require_any(*ADMIN)),
                           db=Depends(get_db)):
    """预置采集定时器包（config/collector-presets-v1.json）及本工作区是否已导入。"""
    data = collector_presets.list_presets(db, principal.workspace.id)
    items = data.pop('items')
    return {**data, **page(items[params.offset:params.offset + params.limit], len(items), params)}


@router.post('/collectors/presets/install', response_model=PresetInstallOut)
def collector_presets_install(body: PresetInstallIn, principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    """导入预置采集定时器：缺的创建、已有的跳过（按 Skill 标识和定时器名称判断），可重复执行。"""
    with unit_of_work(db):
        return collector_presets.install(db, principal.workspace.id, principal.user.id, body.provider_id, body.keys)


@router.post('/collectors')
def create_collector(body: CollectorIn, principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    with unit_of_work(db):
        return collector.save_task(db, principal.workspace.id, principal.user.id, body.model_dump())


@router.put('/collectors/{task_id}')
def update_collector(task_id: str, body: CollectorIn, principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    with unit_of_work(db):
        return collector.save_task(db, principal.workspace.id, principal.user.id, body.model_dump(), task_id)


@router.post('/collectors/{task_id}/run')
def run_collector(task_id: str, principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    """Run now (synchronously; a search-enabled model may take a minute or two)."""
    with unit_of_work(db):
        task = collector._task(db, principal.workspace.id, task_id)
        return collector.run_task(db, principal.workspace.id, task, trigger='manual', actor_id=principal.user.id)


@router.get('/collectors/{task_id}/runs')
def collector_runs(task_id: str, principal: Principal = Depends(require_any(*ADMIN)), db=Depends(get_db)):
    return collector.list_runs(db, principal.workspace.id, task_id)
