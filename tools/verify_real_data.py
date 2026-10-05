"""Read-only local API acceptance; save metadata, never acquired source text."""
import json
from pathlib import Path
from urllib.request import Request, urlopen
BASE='http://127.0.0.1:8766'

def request(path,login='research@demo',body=None):
    payload=json.dumps(body).encode() if body is not None else None
    req=Request(BASE+path,data=payload,headers={'X-Vip-Login':login,'X-Vip-Workspace':WS,'Content-Type':'application/json'})
    with urlopen(req,timeout=15) as response: return json.load(response)

WS=''
identities=request('/api/identities')
assert identities['data_mode']=='real_public'
WS=next(w['id'] for w in identities['workspaces'] if w['has_real_data'])
companies=request('/api/companies');assert {c['name'] for c in companies}=={'比亚迪股份有限公司','珠海格力电器股份有限公司'}
items=request('/api/intake/items');assert len(items)>=2
reads=[]
for item in items:
    detail=request('/api/intake/items/'+item['id'])
    assert detail['original_text'] and len(detail['original_text'])>100
    policy=detail['source']['policy']
    assert policy['license'] in ('CC-BY-SA-4.0','provider-published-free-local-financial-analysis')
    assert detail['revision']['hash']
    if policy['license']=='CC-BY-SA-4.0':
        assert detail['body_access']['url'].startswith('https://en.wikipedia.org/w/index.php?oldid=')
    else:
        assert detail['body_access']['url'] is None
        if detail['reading_metadata']['material_type']=='market_daily':assert detail['original_text'].startswith('date,code')
        else:assert detail['reading_metadata']['material_type']=='financial_metrics' and 'netProfit' in detail['original_text']
    reads.append({'id':item['id'],'revision':detail['revision'],'date':detail['publication']['date'],'observed_at':detail['observed_at'],'url':detail['body_access']['url'],'original_readable':True})
for company in companies:
    score=request('/api/companies/'+company['id']+'/score')
    assert score['data_mode']=='real_public' and score['quality_score'] is None
    assert all(s['pe_ttm'] is None and s['valuation_score'] is None for s in score['securities'])
    assert request('/api/companies/'+company['id']+'/timeline')['items']
assert request('/api/judgments')==[]
assert request('/api/strategy/transitions')==[]
preview=request('/api/strategy/simulate','strat@demo',{'quality_threshold':'70'})
assert len(preview['results'])==3 and all(r['quality'] is None and r['valuation'] is None for r in preview['results'])
assert all(r['passes'] is None for r in preview['results'])
result={'base':BASE,'companies':[c['name'] for c in companies],'real_readings':reads,'quality_and_valuation':'UNKNOWN','strategy_securities':3,'synthetic_objects_visible':0,'source_body_saved_in_report':False}
path=Path(__file__).resolve().parents[1]/'versions/v0.0.1/real-data-readback.json'
path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'companies':len(companies),'readable_items':len(items),'unknown_securities':3,'synthetic_objects_visible':0},ensure_ascii=False))
