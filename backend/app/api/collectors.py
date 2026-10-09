"""采集定时器与 Skill 维护 API (后台设置)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import Principal, require_any
from app.core.uow import unit_of_work
from app.db import get_db
from app.domains.news import collector

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
