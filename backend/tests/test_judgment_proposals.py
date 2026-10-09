"""Pending AI advice is readable but cannot masquerade as accepted human work."""
import copy,json
from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func
from app.models.runtime import ItemRevision
from app.models.judgment import JudgmentSlot,JudgmentRevision
from app.models.audit import AuditLog
from app.models.intake import SourceRegistry
from app.domains.platform.transactions import canonical
from test_real_data import real_mode
from test_remediation import Session,headers,prepared
from test_ux18 import author_body


def proposal(ids):
    with Session() as db: body=author_body(ids,db.get(ItemRevision,ids['revision']))
    return {**body,'confidence':'0.99','author_label':'原创合成研究工具',
            'limitations':'本夹具没有校准，不能自动计入评分。'}


def test_pending_proposal_evidence_replay_score_and_explicit_confirmation(real_mode):
    client,ws,other,ids=real_mode;body=proposal(ids)
    h={**headers(ws),'Idempotency-Key':'proposal-one'}
    response=client.post('/api/judgments/proposals',headers=h,json=body)
    assert response.status_code==201,response.text
    saved=response.json();assert saved['applicability']=='pending_review'
    assert client.post('/api/judgments/proposals',headers=h,json=body).json()['id']==saved['id']
    row=client.get('/api/judgments',headers=headers(ws)).json()[0]
    assert row['effective'] is None and row['author_type']=='auto'
    assert row['proposal']['confidence_calibrated'] is False and row['proposal']['reason']==body['reason']
    score=client.get('/api/companies/'+ids['company']+'/score',headers=headers(ws)).json()
    assert score['dimensions']['business_model']['criteria'][0]['status']=='missing'
    assert saved['id'] not in [r['id'] for r in score['judgment_refs']]
    assert client.get('/api/judgments',headers=headers(other)).json()==[]
    run=client.post('/api/research/runs',headers={**headers(ws),'Idempotency-Key':'pending-snapshot'}).json()
    frozen=run['result']['companies'][0]['judgment_proposals']
    assert len(frozen)==1 and frozen[0]['revision_id']==saved['id']
    confirm={**headers(ws),'If-Match-Generation':'1','Idempotency-Key':'confirm-one'}
    r=client.post('/api/judgments/'+saved['slot_key']+'/override',headers=confirm,
                  json={'value':{'grade':2,'reason':'原创测试明确人工确认'}})
    assert r.status_code==200,r.text
    assert client.post('/api/judgments/'+saved['slot_key']+'/override',headers=confirm,
                       json={'value':{'grade':2,'reason':'原创测试明确人工确认'}}).json()['id']==r.json()['id']
    row=client.get('/api/judgments',headers=headers(ws)).json()[0]
    assert row['author_type']=='human' and row['proposal'] is None and row['effective']['grade']==2
    assert row['evidence'][0]['source_revision_id']==body['evidence'][0]['source_revision_id']
    history=client.get('/api/research/runs/'+run['id'],headers=headers(ws)).json()
    assert history['manifest_hash']==run['manifest_hash'] and history['result']['companies'][0]['judgment_proposals']==frozen
    assert client.post('/api/judgments/'+saved['slot_key']+'/override',headers={**headers(ws),'If-Match-Generation':'1'},json={'value':{'grade':3}}).status_code==409
    with Session() as db:
        slot=db.scalar(select(JudgmentSlot).where(JudgmentSlot.slot_key==saved['slot_key']))
        assert db.scalar(select(func.count(JudgmentRevision.id)).where(JudgmentRevision.slot_id==slot.id))==2
        assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='judgment.proposed'))==1


def test_proposal_rejects_wrong_evidence_permissions_and_expired_confirmation(real_mode):
    c,ws,other,ids=real_mode;body=proposal(ids);h={**headers(ws),'Idempotency-Key':'proposal-boundary'}
    bad=copy.deepcopy(body);bad['evidence'][0]['quote']='不存在原文'
    assert c.post('/api/judgments/proposals',headers=h,json=bad).status_code==422
    assert c.post('/api/judgments/proposals',headers={**headers(ws,'viewer@demo'),'Idempotency-Key':'denied'},json=body).status_code==403
    assert c.post('/api/judgments/proposals',headers={**headers(other),'Idempotency-Key':'other'},json=body).status_code==404
    response=c.post('/api/judgments/proposals',headers=h,json=body);assert response.status_code==201
    key=response.json()['slot_key']
    with Session() as db:
        rev=db.get(JudgmentRevision,response.json()['id']);rev.valid_until=datetime.now(timezone.utc)-timedelta(seconds=1);db.commit()
    assert c.post('/api/judgments/'+key+'/override',headers={**headers(ws),'If-Match-Generation':'1'},json={'value':{'grade':2}}).status_code==422
    with Session() as db:
        source=db.get(SourceRegistry,ids['source']);p=json.loads(source.policy_json);p['revoked']=True;source.policy_json=canonical(p);db.commit()
    assert c.get('/api/judgments',headers=headers(ws)).json()==[]
    assert c.post('/api/judgments/'+key+'/override',headers={**headers(ws),'If-Match-Generation':'1'},json={'value':{'grade':2}}).status_code==404
