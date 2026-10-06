"""Isolation tests use original fixtures in the test DB, not live source claims."""
import json
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from app.config import get_settings
from app.models.company import Company, ItemCompanyLink, Security
from app.models.intake import InformationItem, SourceRegistry
from app.models.runtime import ResearchInput
from app.models.judgment import JudgmentSlot
from app.services.item_history import observe
from app.services.scoring_service import score_company, score_security
from app.services.transactions import canonical, digest
from test_remediation import prepared, headers, Session

@pytest.fixture()
def real_mode(prepared, monkeypatch):
    client,ws,isolated=prepared
    monkeypatch.setattr(get_settings(),'demo_mode',False)
    with Session() as db:
        source=SourceRegistry(source_key='original-test-source',name='原创测试来源，不是实际采集',policy_json=canonical({'license':'original-test-only','fetch':'local','store':'local','analyze':'local'}))
        db.add(source);db.flush()
        company=Company(name='原创真实模式测试公司');db.add(company);db.flush()
        item=InformationItem(workspace_id=ws,source_id=source.id,entry_key='original',title='原创边界测试文',content_kind='article',summary_text='原创测试文本',reading_metadata_json=canonical({'data_mode':'real_public'}),publication_json=canonical({'date':'2026-10-01'}),body_state='available')
        db.add(item);db.flush();observe(db,item,{'readable_text':'原创测试文本，不是实际财报'})
        db.add(ItemCompanyLink(item_id=item.id,company_id=company.id,status='accepted',label_text=company.name))
        db.add(Security(company_id=company.id,market='CN_A',ticker='TEST.REAL',currency='CNY'));db.commit()
        ids={'company':company.id,'item':item.id,'source':source.id,'revision':item.current_revision_id}
    yield client,ws,isolated,ids


def test_default_and_fixture_target_guard(monkeypatch):
    from app.config import Settings
    from app.services.data_mode import fixture_mode
    assert Settings.model_fields['demo_mode'].default is False
    monkeypatch.setattr(get_settings(),'demo_mode',True)
    monkeypatch.setattr(get_settings(),'db_url','postgresql://example@127.0.0.1/vip_v0001_local')
    assert fixture_mode() is False


def test_real_routes_exclude_fixture_and_block_direct_ids(real_mode):
    c,ws,isolated,ids=real_mode;h=headers(ws)
    assert [r['id'] for r in c.get('/api/companies',headers=h).json()]==[ids['company']]
    items=c.get('/api/intake/items',headers=h).json();assert [r['id'] for r in items]==[ids['item']]
    assert c.get('/api/companies',headers=headers(isolated)).json()==[]
    with Session() as db:
        old=db.scalar(select(InformationItem.id).where(InformationItem.id!=ids['item']))
        slot=db.scalar(select(JudgmentSlot.slot_key))
    fake='00000000-0000-4000-8000-000000000001'
    for route in [f'/api/companies/{fake}/score',f'/api/companies/{fake}/timeline',f'/api/templates/{fake}',f'/api/intake/items/{old}']:
        assert c.get(route,headers=h).status_code==404
    assert c.get('/api/judgments',headers=h).json()==[]
    assert c.get('/api/strategy/transitions',headers=h).json()==[]
    for path,role in [('/api/intake/synthetic','data@demo'),('/api/judgments/auto-run','research@demo'),('/api/strategy/run-golden','strat@demo'),('/api/demo/runs','data@demo')]:
        assert c.post(path,headers=headers(ws,role),json={'source_key':'local-fixture'}).status_code==403
    assert c.post(f'/api/judgments/{slot}/override',headers={**h,'If-Match-Generation':'1'},json={'value':{},'release':True}).status_code==404
    preview=c.post('/api/strategy/simulate',headers=headers(ws,'strat@demo'),json={'quality_threshold':'70'}).json()
    assert len(preview['results'])==1 and preview['results'][0]['quality'] is None
    assert preview['results'][0]['passes'] is None
    detail=c.get(f"/api/intake/items/{ids['item']}",headers=h).json()
    assert detail['original_text']=='原创测试文本，不是实际财报'


def test_flag_alone_cannot_turn_fixture_into_real_financials(real_mode):
    _,ws,_,ids=real_mode
    from app.models.runtime import ItemRevision
    from app.services.data_mode import real_evidence
    with Session() as db:
        financial=db.scalar(select(ResearchInput).where(ResearchInput.kind=='financials'))
        copied={**json.loads(financial.payload_json),"test_lineage":"flag-alone"}
        at=datetime.now(timezone.utc)
        row=ResearchInput(workspace_id=ws,company_id=ids['company'],input_key='financials',kind='financials',payload_json=canonical(copied),content_hash=digest(copied),effective_at=at,published_at=at,known_at=at,synthetic=False)
        db.add(row);db.flush()
        company=db.get(Company,ids['company']);sec=db.scalar(select(Security).where(Security.company_id==company.id))
        assert score_company(db,company,ws)['quality_score'] is None
        assert score_company(db,company,ws)['input_refs']==[]
        assert score_security(db,sec,ws)['pe_ttm'] is None
        revision=db.get(ItemRevision,ids['revision'])
        refs=[{'synthetic':False,'source_revision_id':revision.id,'hash':revision.content_hash,'locator':'original'}]
        assert real_evidence(db,refs,ws,company.id)
        assert not real_evidence(db,[{**refs[0],'hash':'wrong'}],ws,company.id)
        assert not real_evidence(db,refs,'other-workspace',company.id)
        db.get(SourceRegistry,ids['source']).policy_json=canonical({'license':'original-test-only','fetch':'local','store':'local','analyze':'local','revoked':True});db.flush()
        assert not real_evidence(db,refs,ws,company.id)
        db.rollback()


def test_missing_strategy_input_has_priority_over_failed_coverage():
    from app.services.strategy_service import gates
    from app.services.scoring_service import config
    rules=config('strategy-standard-v1.json')
    result=gates(rules,{'quality_exact':None,'coverage_exact':'0','metrics':{}},{})
    assert result['passes'] is None
    assert any(c['result'] is False for c in result['conditions'])
    assert any(c['result'] is None for c in result['conditions'])


def test_third_real_company_does_not_block_research_or_mix_workspace(real_mode):
    from app.models.runtime import ResearchRun
    from app.models.audit import AuditLog
    from sqlalchemy import func
    client, ws, isolated, ids = real_mode
    with Session() as db:
        added = []
        for n in (2, 3):
            company = Company(name=f'原创研究范围测试公司{n}', industry_key='biopharma')
            db.add(company); db.flush()
            item = InformationItem(workspace_id=ws, source_id=ids['source'],
                entry_key=f'original-profile-{n}', title=company.name,
                content_kind='article', body_state='available',
                reading_metadata_json=canonical({'data_mode':'real_public'}))
            db.add(item); db.flush()
            observe(db, item, {'readable_text': f'原创身份测试记录{n}；没有财务或价格'})
            db.add(ItemCompanyLink(item_id=item.id, company_id=company.id,
                status='accepted', label_text=company.name))
            db.add(Security(company_id=company.id, market='HK',
                ticker=f'TEST.PROFILE{n}', currency='HKD'))
            added.append(company.id)
        db.commit()
    h = {**headers(ws), 'Idempotency-Key':'original-three-companies'}
    response = client.post('/api/research/runs', headers=h)
    assert response.status_code == 200, response.text
    run = response.json()
    assert {c['company_id'] for c in run['result']['companies']} == {ids['company'], *added}
    assert run['status'] == 'partial' and len(run['manifest']['read_items']) == 3
    for c in run['result']['companies']:
        assert c['quality']['quality_score'] is None
        assert all(s['latest_quote'] is None and s['valuation']['pe_ttm'] is None
                   and s['strategy']['result'] == 'UNKNOWN' for s in c['securities'])
        if c['company_id'] in added:
            assert c['quality']['template']['levels_applied'] == ['base']
    replay = client.post('/api/research/runs', headers=h)
    assert replay.status_code == 200 and replay.json()['manifest_hash'] == run['manifest_hash']
    assert replay.json()['id'] == run['id']
    assert client.get('/api/companies', headers=headers(isolated)).json() == []
    assert client.get('/api/research/runs/'+run['id'], headers=headers(isolated)).status_code == 404
    with Session() as db:
        assert db.scalar(select(func.count(ResearchRun.id))) == 1
        assert db.scalar(select(func.count(AuditLog.id)).where(
            AuditLog.action == 'research.preview_completed')) == 1
