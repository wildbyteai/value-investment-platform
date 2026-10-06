"""Synthetic independent EUR bases; ingestion rights/replay and FX direction."""
import csv,io,json,hashlib
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
from types import SimpleNamespace
import pytest
from sqlalchemy import select,func
from app.services.ecb_fx import validate,import_snapshot,URL
from app.services.scoring_service import score_security
from app.services.transactions import canonical
from app.models.audit import AuditLog
from app.models.company import Company
from test_remediation import prepared,Session
from test_original_inputs import bundle
from app.services.original_financials import normalize

FIELDS=['KEY','FREQ','CURRENCY','CURRENCY_DENOM','EXR_TYPE','EXR_SUFFIX','TIME_PERIOD','OBS_VALUE','OBS_STATUS','UNIT','UNIT_MULT']
def snapshot(change=None):
 rows=[{'KEY':'EXR.D.'+c+'.EUR.SP00.A','FREQ':'D','CURRENCY':c,'CURRENCY_DENOM':'EUR','EXR_TYPE':'SP00','EXR_SUFFIX':'A','TIME_PERIOD':'2026-06-30','OBS_VALUE':v,'OBS_STATUS':'A','UNIT':c,'UNIT_MULT':'0'} for c,v in [('HKD','12'),('CNY','8')]]
 if change:change(rows)
 out=io.StringIO();writer=csv.DictWriter(out,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows);raw=out.getvalue()
 return {'provider':'ecb','url':URL,'start':'2026-06-01','end':'2026-06-30','observed_at':datetime.now(timezone.utc).isoformat(),'raw':raw,'raw_sha256':hashlib.sha256(raw.encode()).hexdigest()}

@pytest.mark.parametrize('change',[
 lambda r:r.pop(),lambda r:r.append(deepcopy(r[0])),lambda r:r[0].update(OBS_VALUE='NaN'),
 lambda r:r[0].update(OBS_VALUE='0'),lambda r:r[0].update(OBS_STATUS='M'),
 lambda r:r[0].update(CURRENCY_DENOM='USD'),lambda r:r[0].update(UNIT_MULT='3'),
 lambda r:r[0].update(KEY='EXR.D.CNY.EUR.SP00.A'),lambda r:r[0].update(TIME_PERIOD='2026-07-01')])
def test_incomplete_conflicting_or_wrong_basis_rejected(change):
 with pytest.raises(ValueError):validate(snapshot(change))

def test_original_values_cross_rate_and_knowledge_clock():
 s=snapshot();r=validate(s)[0]
 assert r['value']=='1.5' and r['components']['HKD']['original_value']=='12'
 s['raw_sha256']='bad'
 with pytest.raises(ValueError):validate(s)
 s=snapshot();s['observed_at']='2099-01-01T00:00:00+00:00'
 with pytest.raises(ValueError):validate(s)

def test_fx_join_does_not_promote_reference_close_or_reuse_wrong_date():
 f=normalize(bundle());ref=[{'synthetic':False,'source_revision_id':'r','hash':'a'*64,'locator':'synthetic'}]
 p={'ticker':'TEST','currency':'HKD','session':'2026-06-30','raw_close':'30','is_final':False,'evidence':ref}
 fx={'provider':'ecb','pair':'HKD_PER_CNY','rows':validate(snapshot()),'evidence':ref}
 rows=[SimpleNamespace(id='f',kind='financials',input_key='financials',payload_json=canonical(f)),
 SimpleNamespace(id='p',kind='price',input_key='price:TEST',payload_json=canonical(p)),
 SimpleNamespace(id='fx',kind='fx',input_key='fx:HKD_PER_CNY',payload_json=canonical(fx))]
 security=SimpleNamespace(id='test',company_id='c',ticker='TEST',currency='HKD',market='HK')
 now=datetime.fromisoformat('2026-06-30T23:00:00+08:00')
 q=score_security(None,security,'ws',now,input_rows=rows)
 assert q['reason']=='FINAL_PRICE_REQUIRED' and q['latest_quote']['fx_per_cny']=='1.5' and q['pe_ttm'] is None
 p['is_final']=True;rows[1].payload_json=canonical(p)
 q=score_security(None,security,'ws',now,input_rows=rows)
 assert q['pe_exact']=='0.153846153846' and len(q['basis']['evidence'])==2
 p['session']='2026-06-29';rows[1].payload_json=canonical(p)
 assert score_security(None,security,'ws',now,input_rows=rows)['reason']=='INCOMPLETE_PRICE_BASIS'
 assert 'fx_per_cny' not in p

def test_import_replay_source_permissions_and_company_boundary(prepared,monkeypatch):
 from app.models.intake import SourceRegistry
 from app.models.runtime import ResearchInput
 from fastapi import HTTPException
 _,ws,other=prepared
 with Session() as db:
  c=Company(name='原创合成FX测试公司');c2=Company(name='原创合成FX第二公司');db.add_all([c,c2]);db.flush();id=c.id;ids=[id,c2.id];db.commit()
  first=import_snapshot(db,ws,ids,snapshot());db.commit()
  second=import_snapshot(db,ws,ids,snapshot());db.commit()
  assert second['inputs'][0]['reused'] and first['revision_id']==second['revision_id']
  assert all(x['reused'] for x in second['inputs']) and len({x['input_id'] for x in first['inputs']})==2
  assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='research.ecb_fx_imported'))==2
  r=db.get(ResearchInput,first['inputs'][0]['input_id']);assert r.published_at.date()>datetime.fromisoformat('2026-06-30').date()
  import uuid
  with pytest.raises(HTTPException):import_snapshot(db,ws,[str(uuid.uuid4())],snapshot())
  db.rollback()
  src=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key=='ecb-reference-fx'));policy=json.loads(src.policy_json);policy['revoked']=True;src.policy_json=canonical(policy);db.commit()
  with pytest.raises(ValueError,match='revoked'):import_snapshot(db,ws,[id],snapshot())
