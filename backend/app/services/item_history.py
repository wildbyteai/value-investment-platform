"""Content deduplication does not erase A→B→A observations."""
from sqlalchemy import select, func
from app.models.runtime import ItemRevision, ItemObservation
from app.services.transactions import digest, canonical


def observe(db, item, payload):
    import json
    payload = {**payload, 'item_snapshot': {
        'title': item.title, 'content_kind': item.content_kind,
        'summary_text': item.summary_text, 'publication': json.loads(item.publication_json),
        'reading_metadata': {k:v for k,v in json.loads(item.reading_metadata_json).items() if k not in ('source_observed_at','raw_hash')},
        'body_access': {'state': item.body_state, 'url': item.body_url},
    }}
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
