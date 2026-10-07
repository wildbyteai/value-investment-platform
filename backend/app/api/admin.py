"""后台设置 API: 数据源 (and, from R5/R6, models, feeds and notification settings)."""
from fastapi import APIRouter, Depends

from app.api.deps import Principal, require_any
from app.sources import registry

router = APIRouter(prefix='/api/admin', tags=['admin'])

ADMIN = ('source.manage', 'system.configure')


@router.get('/sources')
def sources(principal: Principal = Depends(require_any(*ADMIN))) -> list[dict]:
    return [s.as_dict() for s in registry.all_sources()]
