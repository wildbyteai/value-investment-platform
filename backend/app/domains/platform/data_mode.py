"""Real research defaults; fixtures are usable only in the disposable test DB.

Classification follows source-backed items, never names or ticker resemblance.
"""
import json
from app.core.errors import Forbidden, NotFound
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.config import get_settings
from app.models.company import Company, ItemCompanyLink
from app.models.intake import InformationItem, SourceRegistry
from app.models.runtime import ItemRevision


def fixture_mode():
    settings = get_settings()
    target = make_url(settings.db_url)
    return settings.demo_mode and target.host in ('127.0.0.1','localhost') and target.database == 'vip_v0001_test'


def require_fixture():
    if not fixture_mode():
        raise Forbidden('合成操作仅允许在隔离测试库中执行')


def real_item(db, item, workspace_id):
    if not item or item.workspace_id != workspace_id:
        return False
    meta = json.loads(item.reading_metadata_json)
    source = db.get(SourceRegistry, item.source_id)
    policy = json.loads(source.policy_json) if source else {}
    return (meta.get('data_mode') == 'real_public' and bool(policy.get('license'))
            and bool(policy.get('fetch')) and bool(policy.get('store')) and not policy.get('revoked'))


def readable_item(db, item, workspace_id):
    if not item or item.workspace_id != workspace_id:
        return False
    source = db.get(SourceRegistry, item.source_id)
    if not source or json.loads(source.policy_json).get('revoked'):
        return False
    return fixture_mode() or real_item(db, item, workspace_id)


def companies(db, workspace_id):
    rows = db.scalars(select(Company).order_by(Company.name)).all()
    if fixture_mode():
        return rows
    items = db.scalars(select(InformationItem).where(InformationItem.workspace_id == workspace_id)).all()
    ids = [it.id for it in items if real_item(db, it, workspace_id)]
    company_ids = set(db.scalars(select(ItemCompanyLink.company_id).where(
        ItemCompanyLink.item_id.in_(ids), ItemCompanyLink.status == 'accepted')).all())
    return [c for c in rows if c.id in company_ids]


def require_company(db, company_id, workspace_id):
    row = next((c for c in companies(db, workspace_id) if c.id == company_id), None)
    if row is None:
        raise NotFound('当前研究模式和工作区没有该公司')
    return row


def real_evidence(db, refs, workspace_id, company_id=None, cutoff=None):
    if not isinstance(refs, list) or not refs:
        return False
    for ref in refs:
        if not isinstance(ref, dict) or ref.get('synthetic') is not False or not ref.get('locator'):
            return False
        revision = db.get(ItemRevision, ref.get('source_revision_id', ''))
        item = db.get(InformationItem, revision.item_id) if revision else None
        if not real_item(db, item, workspace_id) or item.body_state != 'available':
            return False
        if cutoff and revision.created_at > cutoff:
            return False
        from app.domains.platform.transactions import digest
        if digest(json.loads(revision.payload_json)) != revision.content_hash or ref.get('hash') != revision.content_hash:
            return False
        if company_id and not db.scalar(select(ItemCompanyLink.id).where(
            ItemCompanyLink.item_id == item.id, ItemCompanyLink.company_id == company_id,
            ItemCompanyLink.status == 'accepted')):
            return False
        policy = json.loads(db.get(SourceRegistry, item.source_id).policy_json)
        if not policy.get('analyze') or policy.get('analyze') == 'disabled':
            return False
    return True
