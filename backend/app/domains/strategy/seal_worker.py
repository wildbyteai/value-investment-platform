"""One scheduled internal job with separate lease/freeze/finish transactions."""
from app.domains.strategy import sealing_service as service

def run_one(session_factory,context,seal_id):
    with session_factory() as db:
        token=service.claim(db,context,seal_id);db.commit()
    if not token:return {'state':'leased_elsewhere'}
    if token.get('state'):return token
    with session_factory() as db:
        db.connection(execution_options={'isolation_level':'REPEATABLE READ'})
        frozen=service.freeze(db,context,token);db.commit()
        manifest_id,manifest_hash=frozen.id,frozen.manifest_hash
    with session_factory() as db:
        evaluation=service.finish(db,context,token,manifest_id,manifest_hash);db.commit()
        return {'state':'sealed' if evaluation else 'blocked_safety','evaluation_id':evaluation.id if evaluation else None}
