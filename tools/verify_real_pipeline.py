"""Explicit local research preview plus readback; report contains no source body."""
import argparse
import json
from decimal import Decimal
from pathlib import Path
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8766'
WS=''

def request(path,body=None,key=None):
    headers={'X-Vip-Login':'research@demo','X-Vip-Workspace':WS,'Content-Type':'application/json'}
    if key:headers['Idempotency-Key']=key
    data=json.dumps(body).encode() if body is not None else None
    with urlopen(Request(BASE+path,data=data,headers=headers),timeout=20) as response:return json.load(response)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-key',required=True,help='Explicit idempotent command for the authorized local preview')
    parser.add_argument('--require-financial',action='store_true')
    args=parser.parse_args()
    ids=request('/api/identities');assert ids['data_mode']=='real_public'
    WS=next(w['id'] for w in ids['workspaces'] if w['has_real_data'])
    items=request('/api/intake/items');assert len(items)==(6 if args.require_financial else 4)
    sources={}
    for item in items:
        detail=request('/api/intake/items/'+item['id']);assert detail['original_text'] and detail['revision']['hash']
        assert detail['data_mode']=='real_public'
        sources[item['id']]=detail
    run=request('/api/research/runs',{},args.run_key)
    assert request('/api/research/runs',{},args.run_key)['id']==run['id']
    assert request('/api/research/runs/'+run['id'])==run
    assert run['status']=='partial' and len(run['result']['companies'])==2
    assert not run['manifest']['membership_applied'] and not run['manifest']['external_model']
    markets=0;financials=0;securities=0;companies=[]
    for company in run['result']['companies']:
        assert company['quality']['quality_score'] is None
        for analysis in company['analysis']:
            if analysis['kind']=='financial_summary':
                source=sources[analysis['source_item_id']]
                assert source['revision']['id']==analysis['source_revision_id']
                assert analysis['report_rows']==20 and analysis['standard_metrics_eligible'] is False
                lines=source['original_text'].splitlines();parsed={}
                for index,line in enumerate(lines):
                    if not line.startswith('code,pubDate,statDate,'):continue
                    values=dict(zip(line.split(','),lines[index+1].split(',')))
                    parsed.setdefault(values['statDate'],{}).update(values)
                assert len(parsed)==len(analysis['periods'])==5
                for period in analysis['periods']:
                    assert parsed[period['stat_date']]['netProfit']==period['values']['netProfit']
                    assert parsed[period['stat_date']]['totalShare']==period['values']['totalShare']
                annual=[p for p in analysis['periods'] if p['stat_date'].endswith('12-31')]
                expected=(Decimal(annual[-1]['values']['netProfit'])/Decimal(annual[0]['values']['netProfit'])-1)*100
                assert abs(expected-Decimal(analysis['annual_net_profit_field_change_pct']))<Decimal('0.000000000001')
                assert company['quality']['financial_observations_available'] and company['quality']['metrics']=={}
                financials+=1
            if analysis['kind']!='market_summary':continue
            source=sources[analysis['source_item_id']]
            assert source['revision']['id']==analysis['source_revision_id']
            lines=source['original_text'].splitlines()
            assert len(lines)-1==analysis['observations']==19
            fields=lines[0].split(',');first=dict(zip(fields,lines[1].split(',')));last=dict(zip(fields,lines[-1].split(',')))
            assert analysis['first_close']==first['close'] and analysis['last_close']==last['close']
            expected=(Decimal(last['close'])/Decimal(first['close'])-1)*100
            assert abs(expected-Decimal(analysis['change_pct']))<Decimal('0.000000000001')
            markets+=1
        for security in company['securities']:
            assert security['strategy']['result']=='UNKNOWN' and not security['strategy']['applied']
            assert security['valuation']['pe_ttm'] is None
            quote=security['latest_quote']
            if security['market']=='CN_A':
                assert quote['currency']=='CNY' and quote['session']=='2026-09-30' and not quote['is_final']
            else:assert security['market']=='HK' and quote is None
            securities+=1
        live=request('/api/companies/'+company['company_id']+'/score')
        assert all(s['pe_ttm'] is None for s in live['securities'])
        assert any(s['latest_quote'] for s in live['securities'])
        companies.append(company['company_name'])
    assert markets==2 and securities==3
    if args.require_financial:assert financials==2
    assert request('/api/strategy/transitions')==[] and request('/api/judgments')==[]
    result={'base':BASE,'run_id':run['id'],'manifest_hash':run['manifest_hash'],'created_at':run['created_at'],
        'status':run['status'],'companies':companies,'readable_items':len(items),'market_rows':38,
        'financial_rows':financials*20,'standard_financial_metrics':'UNKNOWN',
        'source_revisions':run['manifest']['read_items'],'stages':run['result']['stages'],
        'statistics_verified_against_source_rows':True,'idempotent_retry_verified':True,
        'unknown_securities':securities,'synthetic_objects_visible':0,'membership_applied':False,
        'source_body_or_prices_saved_in_report':False}
    filename='real-financial-readback.json' if args.require_financial else 'real-pipeline-readback.json'
    (ROOT/'versions/v0.0.1'/filename).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['run_id','status','readable_items','market_rows','unknown_securities','statistics_verified_against_source_rows','idempotent_retry_verified']},ensure_ascii=False))
