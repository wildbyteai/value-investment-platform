"""Original fixtures exercise issuer attribution, permission policy and replay."""
import copy,json
from datetime import datetime,timezone
import pytest
from sqlalchemy import select,func
from app.services.issuer_disclosures import validate,import_snapshot
from app.models.company import Company,Security
from app.models.runtime import ItemRevision
from app.models.intake import SourceRegistry
from app.models.audit import AuditLog
from app.services.transactions import canonical
from test_remediation import prepared,Session

def snapshot():
    return {'key':'original-fixture','ticker':'09969.HK','issuer':'诺诚健华医药有限公司',
        'title':'原创合成公告，不是发行人实际数据','url':'https://static.cninfo.com.cn/finalpage/2026-09-01/100.PDF',
        'disclosure_date':'2026-09-01','observed_at':datetime.now(timezone.utc).isoformat(),
        'pdf_sha256':'a'*64,'page_count':1,'pages':[{'number':1,'text':'诺诚健华医药有限公司\n原创测试：付款有条件，不是已实现收入。'}]}

def test_traditional_issuer_and_explicit_decoder_version():
    s=snapshot();s['text_parser']='pdfplumber_0.11.9'
    s['pages'][0]['text']='諾誠健華醫藥有限公司\n原創測試。'
    validate(s)
    s['text_parser']='unchecked_decoder'
    with pytest.raises(ValueError,match='解析版本'):validate(s)

@pytest.mark.parametrize('defect',['issuer','host','future','unreadable','hash','page'])
def test_wrong_source_or_unreadable_issuer_rejected(defect):
    s=snapshot()
    if defect=='issuer':s['issuer']='另一发行人'
    if defect=='host':s['url']='https://other.example/finalpage/2026-09-01/100.PDF'
    if defect=='future':s['observed_at']='2099-01-01T00:00:00+00:00'
    if defect=='unreadable':s['pages'][0]['text']='无法解码的文本'
    if defect=='hash':s['pdf_sha256']='wrong'
    if defect=='page':s['pages'][0]['number']=2
    with pytest.raises(ValueError):validate(s)

def test_append_replay_and_revoked_policy(prepared):
    _,ws,other=prepared;s=snapshot()
    with Session() as db:
        c=Company(name=s['issuer']);db.add(c);db.flush()
        db.add(Security(company_id=c.id,market='HK',ticker='09969.HK',currency='HKD'));db.commit()
        result=import_snapshot(db,ws,s);db.commit()
        replay=import_snapshot(db,ws,s);db.commit()
        assert replay['reused'] and replay['revision_id']==result['revision_id']
        assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='research.issuer_disclosure_imported'))==1
        assert db.get(ItemRevision,result['revision_id']).content_hash==result['hash']
        changed=copy.deepcopy(s);changed['pages'][0]['text']+='\n原创更正。'
        new=import_snapshot(db,ws,changed);db.commit()
        assert new['revision_id']!=result['revision_id']
        assert db.get(ItemRevision,result['revision_id']).content_hash==result['hash']
        src=db.scalar(select(SourceRegistry).where(SourceRegistry.source_key=='cninfo-bounded-issuer-disclosures'))
        p=json.loads(src.policy_json);p['revoked']=True;src.policy_json=canonical(p);db.commit()
        with pytest.raises(ValueError,match='撤销'):import_snapshot(db,ws,s)


def test_long_statutory_document_keeps_excerpt_bound():
    s=snapshot();s['page_count']=89;s['pages'][0]['number']=74
    validate(s)
    s['page_count']=101
    with pytest.raises(ValueError,match='页数'):validate(s)
    s['page_count']=100;s['pages']=[{'number':n,'text':'诺诚健华医药有限公司合成页'} for n in range(1,32)]
    with pytest.raises(ValueError,match='页数'):validate(s)
