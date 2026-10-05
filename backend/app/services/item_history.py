"""Content deduplication does not erase A→B→A observations."""
from sqlalchemy import select, func
from app.models.runtime import ItemRevision, ItemObservation
from app.services.transactions import digest, canonical


def observe(db, item, payload):
    content_hash=digest(payload)
    revision=db.scalar(select(ItemRevision).where(ItemRevision.item_id==item.id,ItemRevision.content_hash==content_hash))
    if revision is None:
        revision=ItemRevision(item_id=item.id,content_hash=content_hash,payload_json=canonical(payload))
        db.add(revision);db.flush()
    if item.current_revision_id != revision.id:
        sequence=(db.scalar(select(func.max(ItemObservation.sequence)).where(ItemObservation.item_id==item.id)) or 0)+1
        db.add(ItemObservation(item_id=item.id,revision_id=revision.id,sequence=sequence))
        item.current_revision_id=revision.id
    return revision
