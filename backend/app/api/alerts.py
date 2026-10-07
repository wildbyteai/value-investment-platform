"""监控告警 API: alerts, my in-app notifications, my notification settings."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import Principal, require, require_any
from app.core.uow import unit_of_work
from app.db import get_db
from app.domains.monitoring import service
from app.domains.monitoring.mailer import SmtpMailer

router = APIRouter(prefix='/api', tags=['monitoring'])

SCAN = ('source.manage', 'strategy.publish', 'system.configure')


@router.get('/alerts')
def alerts(limit: int = 50, principal: Principal = Depends(require('research.read')), db=Depends(get_db)):
    return service.list_alerts(db, principal.workspace.id, max(1, min(limit, 200)))


@router.post('/alerts/scan')
def scan(principal: Principal = Depends(require_any(*SCAN)), db=Depends(get_db)):
    """Run the monitor now (normally ``python -m app.jobs alerts`` on a schedule)."""
    with unit_of_work(db):
        return service.scan_all(db, principal.workspace.id, SmtpMailer())


@router.get('/notifications')
def my_notifications(limit: int = 50, principal: Principal = Depends(require('research.read')), db=Depends(get_db)):
    return service.inbox(db, principal.workspace.id, principal.user.id, max(1, min(limit, 200)))


@router.post('/notifications/{notification_id}/read')
def read_one(notification_id: str, principal: Principal = Depends(require('research.read')), db=Depends(get_db)):
    with unit_of_work(db):
        return {'marked': service.mark_read(db, principal.workspace.id, principal.user.id, notification_id)}


@router.post('/notifications/read-all')
def read_all(principal: Principal = Depends(require('research.read')), db=Depends(get_db)):
    with unit_of_work(db):
        return {'marked': service.mark_read(db, principal.workspace.id, principal.user.id)}


class SettingIn(BaseModel):
    email: str | None = Field(None, max_length=320, pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
    email_enabled: bool = True
    inapp_enabled: bool = True


def _setting(s) -> dict:
    return {'email': s.email, 'email_enabled': s.email_enabled, 'inapp_enabled': s.inapp_enabled}


@router.get('/notifications/settings')
def get_settings_(principal: Principal = Depends(require('research.read')), db=Depends(get_db)):
    with unit_of_work(db):
        return _setting(service.get_setting(db, principal.workspace.id, principal.user.id))


@router.put('/notifications/settings')
def put_settings(body: SettingIn, principal: Principal = Depends(require('research.read')), db=Depends(get_db)):
    with unit_of_work(db):
        s = service.get_setting(db, principal.workspace.id, principal.user.id)
        s.email, s.email_enabled, s.inapp_enabled = body.email, body.email_enabled, body.inapp_enabled
        db.flush()
        return _setting(s)
