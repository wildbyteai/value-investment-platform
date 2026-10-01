#!/usr/bin/env python3
"""Offline v0.3 material checks. This does NOT execute the proposed application."""
import copy
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from pathlib import Path
from urllib.parse import unquote
from material_schema import validate, MaterialError

ROOT=Path(__file__).resolve().parents[1]
checks=[]
def check(ok,name):
    if not ok:raise AssertionError(name)
    checks.append(name)
def read(path):return json.loads((ROOT/path).read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical_hash(value):return hashlib.sha256((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest()
def current_revision():
    try:
        return subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    except (OSError,subprocess.CalledProcessError):
        return None
def reject(fn,name):
    try:fn()
    except (MaterialError,ValueError,AssertionError,KeyError):checks.append('Negative: '+name)
    else:raise AssertionError('Expected rejection: '+name)

for pattern in ['config/*.json','contracts/*.json','examples/*.json','design/*.json']:
    for p in sorted(ROOT.glob(pattern)):
        json.loads(p.read_text());check(True,f'JSON syntax: {p.relative_to(ROOT)}')
for p in sorted(ROOT.rglob('*.md')):
    if p.name=='REVIEW-PACK.md' or '.git' in p.parts or 'local-evidence' in p.parts:continue
    for dest in re.findall(r'(?<!!)\[[^\]]+\]\(([^\s)]+)\)',p.read_text()):
        if '://' in dest or dest.startswith('#'):continue
        target=unquote(dest.split('#')[0]);check((p.parent/target).exists(),f'Local link: {p.relative_to(ROOT)} -> {target}')
for p in sorted(ROOT.glob('contracts/*.schema.json')):
    s=json.loads(p.read_text());check(s.get('$schema')=='https://json-schema.org/draft/2020-12/schema',f'Schema dialect: {p.name}')
    def inspect(v):
        if isinstance(v,dict):
            if '$ref' in v:
                ref=v['$ref'];check(ref.startswith('#/'),f'Local-only schema ref: {p.name}')
                t=s
                for seg in ref[2:].split('/'):t=t[seg.replace('~1','/').replace('~0','~')]
                check(isinstance(t,dict),f'Resolvable schema ref: {p.name}:{ref}')
            for child in v.values():inspect(child)
        elif isinstance(v,list):
            for child in v:inspect(child)
    inspect(s)

pairs=[('config/strategy-standard-v1.json','strategy.schema.json'),('config/scoring-standard-v1.json','scoring.schema.json'),('examples/analysis-proposal.json','analysis-result.schema.json'),('examples/job-event.json','job-event.schema.json'),('examples/auto-decision.json','review-decision.schema.json'),('examples/human-override.json','review-decision.schema.json')]
for filename,schemafile in pairs:
    value,s=read(filename),read('contracts/'+schemafile);validate(value,s);check(True,f'Limited Schema fixture validation: {filename}')
    bad=copy.deepcopy(value);bad['unexpected_material_field']=True
    reject(lambda:validate(bad,s),filename+' extra field')
    bad=copy.deepcopy(value);del bad[s['required'][0]]
    reject(lambda:validate(bad,s),filename+' missing required field')

strategy=read('config/strategy-standard-v1.json');scoring=read('config/scoring-standard-v1.json');metrics=read('config/metric-definitions-v2.json')['metrics'];rubrics=read('config/rubrics-standard-v1.json')['rubrics']
all_rubrics={**rubrics,**read('config/rubrics-synthetic-v03.json')['rubrics']}
registry=read('config/dimensions-standard-v1.json');registry_entries={x['dimension']:x for x in registry['entries']}
check(len(registry_entries)==len(registry['entries']),'Unique registered dimension IDs')
check(scoring['dimension_registry_ref']['sha256']==sha(ROOT/scoring['dimension_registry_ref']['path']),'Pinned dimension registry content hash')
check(strategy['universe']['markets']==['CN_A','HK'],'Confirmed A/H scope')
check(strategy['scoring_model_ref']==scoring['model_key'],'Strategy scoring reference')
check(scoring['metric_definition_ref']=='metric-definitions-v2','Corrected metric-definition version')
check(scoring['numeric_policy_ref']==read('config/numeric-policy-v1.json')['policy_key'],'Numeric policy reference')
check(sum(Decimal(v) for v in scoring['dimension_weights'].values())==1,'Base dimension weights sum to 1')
check(strategy['quality_gates']['minimum_coverage']==scoring['minimum_company_coverage']=='0.80','Coverage consistency')
check('financial_max_announced_age_days' not in strategy['quality_gates'],'Removed uniform announcement age')
check(strategy['quality_gates']['price_max_lag_sessions']==0,'No stale close advances FINAL confirmation')
for dim,b in scoring['baselines'].items():
    if 'metrics' in b:
        check(sum(Decimal(x['weight']) for x in b['metrics'])==1,f'Submetric weights: {dim}')
        check(all(x['key'] in metrics and Decimal(x['zero_at'])!=Decimal(x['full_at']) for x in b['metrics']),f'Metric registry / ranges: {dim}')
    else:check(b['rubric_ref'] in rubrics and b['method']=='accepted_evidence_rubric',f'AUTO/HUMAN rubric ref: {dim}')
check(sum(len(v['criteria']) for v in rubrics.values())==11,'Eleven rubric criteria supplied')
for name,r in rubrics.items():
    check(all(len(c['anchors'])==5 and all(c['anchors']) for c in r['criteria']),f'Five evidence anchors: {name}')
    check(r['minimum_criterion_coverage']=='0.80',f'Rubric coverage: {name}')

fields=set(read('contracts/strategy.schema.json')['$defs']['expression']['oneOf'][1]['properties']['field']['enum'])
for mode in ['enter','retain']:
    clauses=strategy[mode]['all'];check(0<len(clauses)<=30 and len({x['field'] for x in clauses})==len(clauses),f'Bounded unique default clauses: {mode}')
    for clause in clauses:
        check(clause['field'] in fields and clause['op'] in {'gte','lte'},f'Whitelisted rule: {mode}:{clause["field"]}');Decimal(clause['value'])
a={x['field']:x for x in strategy['enter']['all']};b={x['field']:x for x in strategy['retain']['all']};check(set(a)==set(b),'Enter/retain field parity')
for f,e in a.items():
    v,w=Decimal(e['value']),Decimal(b[f]['value']);check(e['op']==b[f]['op'] and (v>=w if e['op']=='gte' else v<=w),f'Retain no stricter than enter: {f}')
p=strategy['state_policy'];check(p['enter_distinct_sessions']==p['exit_distinct_sessions']==2 and p['require_adjacent_expected_sessions'] and p['final_price_required'],'Two adjacent expected FINAL sessions')
check(p['notification_phase']=='deferred' and not p['initial_baseline_notify'] and not p['historical_notify'],'Notifications deferred, baseline/history quiet')

# Material resolver: demonstrates the specified inheritance semantics; it is not application implementation.
bundle=read('config/templates-standard-v1.json');tplschema=read('contracts/scoring-template.schema.json')
for t in bundle['templates']:validate(t,tplschema);check(True,'Limited template shape: '+t['template_key'])
def resolve(key,templates=None,stack=()):
    templates=templates or bundle['templates'];bykey={t['template_key']:t for t in templates}
    if len(bykey)!=len(templates):raise ValueError('duplicate template key')
    t=bykey[key]
    validate(t,tplschema)
    if t['scope']['kind'] != {'base':'all','industry':'industry','company':'company'}[t['level']]:raise ValueError('scope/level mismatch')
    if key in stack:raise ValueError('cycle')
    if t['level']=='base':
        if t['base_config_ref']['sha256']!=sha(ROOT/t['base_config_ref']['path']):raise ValueError('base hash')
        c=copy.deepcopy(read(t['base_config_ref']['path']))
        if c['dimension_registry_ref']['sha256']!=sha(ROOT/c['dimension_registry_ref']['path']):raise ValueError('registry hash')
    else:
        parent=bykey[t['parent_ref']['key']]
        if t['parent_ref']['version']!=parent['version'] or t['parent_ref']['sha256']!=canonical_hash(parent):raise ValueError('parent version/hash')
        if (parent['level'],t['level']) not in {('base','industry'),('industry','company')}:raise ValueError('level')
        c=resolve(parent['template_key'],templates,stack+(key,))
    seen=set()
    for patch in t['patches']:
        d=patch['dimension']
        if d in seen:raise ValueError('duplicate patch')
        seen.add(d)
        if d not in registry_entries:raise ValueError('unregistered dimension')
        if t['level']=='industry' and t['scope']['industry_key'] not in registry_entries[d]['applicable_industries']:raise ValueError('inapplicable dimension')
        if t['level']=='company':
            industry=bykey[t['parent_ref']['key']]['scope']['industry_key']
            if industry not in registry_entries[d]['applicable_industries']:raise ValueError('inapplicable dimension')
        if patch.get('disabled'):
            if set(patch)-{'dimension','reason','disabled'}:raise ValueError('mixed disable')
            c['dimension_weights'].pop(d,None);c['baselines'].pop(d,None);c['dimension_policies'].pop(d,None)
        else:
            if d not in c['dimension_weights'] and not(d.startswith('x_') and 'weight' in patch and 'baseline' in patch):raise ValueError('unregistered new dimension')
            if d not in c['dimension_policies']:c['dimension_policies'][d]={k:copy.deepcopy(registry_entries[d][k]) for k in ['quality_policy','event_policy']}
            if 'weight' in patch:c['dimension_weights'][d]=patch['weight']
            if 'baseline' in patch:c['baselines'][d]=copy.deepcopy(patch['baseline'])
            for key in ['quality_policy','event_policy']:
                if key in patch:c['dimension_policies'][d][key]=copy.deepcopy(patch[key])
    if sum(Decimal(x) for x in c['dimension_weights'].values())!=1:raise ValueError('weight sum')
    if set(c['baselines'])!=set(c['dimension_weights']):raise ValueError('dimensions/weights')
    if not set(strategy['quality_gates']['required_dimensions'])<=set(c['baselines']):raise ValueError('required disabled')
    if set(c['dimension_policies'])!=set(c['baselines']):raise ValueError('policies/dimensions')
    c['event_contribution']['half_life_calendar_days']={d:v['event_policy']['half_life_days'] for d,v in c['dimension_policies'].items() if v['event_policy']['enabled']}
    validate(c,read('contracts/scoring.schema.json'))
    for d,base in c['baselines'].items():
        if base['method'] not in registry_entries[d]['allowed_baseline_methods']:raise ValueError('baseline method')
        freshness=c['dimension_policies'][d]['quality_policy']['freshness']['kind']
        if (base['method']=='weighted_metric_rubric')!=(freshness=='report_obligation'):raise ValueError('freshness method')
        validate(base,read('contracts/scoring.schema.json')['properties']['baselines']['additionalProperties'])
        if 'metrics' in base and (sum(Decimal(x['weight']) for x in base['metrics'])!=1 or any(Decimal(x['zero_at'])==Decimal(x['full_at']) for x in base['metrics'])):raise ValueError('submetric weights/range')
        if 'metrics' in base and not all(x['key'] in metrics for x in base['metrics']):raise ValueError('unknown metric')
        if 'rubric_ref' in base and base['rubric_ref'] not in all_rubrics:raise ValueError('unknown rubric')
    return c
industry=resolve('industry-manufacturing');company=resolve('company-synthetic-manufacturer')
check(industry['dimension_weights']['profit_quality']=='0.30','Industry override golden value')
check(company['dimension_weights']=={'profit_quality':'0.35','financial_resilience':'0.20','business_model':'0.25','governance':'0.15','growth_sustainability':'0.05'},'Company override full golden weights')
check(company['baselines']==scoring['baselines'],'Unchanged baselines inherited')
for label,mutator in [
('bad parent hash',lambda ts:ts[-1]['parent_ref'].update(sha256='0'*64)),
('weight sum invalid',lambda ts:ts[-1]['patches'][0].update(weight='0.99')),
('duplicate patch',lambda ts:ts[-1]['patches'].append(copy.deepcopy(ts[-1]['patches'][0]))),
('disable required dimension',lambda ts:ts[-1]['patches'].append({'dimension':'business_model','disabled':True,'reason':'negative'})),
('unknown metric',lambda ts:ts[-1]['patches'][0].update(baseline={'method':'weighted_metric_rubric','metrics':[{'key':'unknown','weight':'1','zero_at':'0','full_at':'1'}]})),
('wrong scope',lambda ts:ts[-1].update(scope={'kind':'all'})),
('jump level',lambda ts:ts[-1]['parent_ref'].update(key=ts[0]['template_key'],version=1,sha256=canonical_hash(ts[0]))),
]:
    bad=copy.deepcopy(bundle['templates']);mutator(bad);reject(lambda:resolve('company-synthetic-manufacturer',bad),label)

policy=read('config/auto-review-policy-v1.json');roles=read('config/roles-standard-v1.json')['roles']
check(policy['risk_target_policy_ref']['sha256']==sha(ROOT/policy['risk_target_policy_ref']['path']),'Pinned risk target policy hash')
check(policy['hard_risk']['allow_auto_accept'] and not policy['template_and_strategy_auto_publish'],'AUTO risk allowed, templates/strategy human-published')
check(policy['human_override_precedence']=='until_released_or_expired' and policy['on_override_expiry']=='reevaluate_current_legal_inputs','Human override precedence/expiry')
check(set(roles)=={'viewer','researcher','strategy_manager','data_admin','system_admin'},'Five confirmed roles')
check('analysis.override' in roles['researcher'] and 'strategy.publish' not in roles['researcher'],'Researcher override but no publish')
check('template.publish' in roles['strategy_manager'] and 'source.manage' not in roles['strategy_manager'],'Strategy manager boundaries')
check('role.assign' not in roles['data_admin'] and 'analysis.override' not in roles['viewer'],'Data admin / viewer boundaries')
check('strategy.publish' not in roles['system_admin'] and 'analysis.override' not in roles['system_admin'],'System admin no implicit business authority')
proposal=read('examples/analysis-proposal.json')
for link in proposal['links']:check(bool(link['evidence_ids']) and 'approved' not in link,'Model proposal cannot self-approve')
for impact in proposal['impact_proposals']:check(impact['company_id'] in {x['company_id'] for x in proposal['links']} and impact['dimension'] in scoring['dimension_weights'],'Impact link/dimension exists')
auto=read('examples/auto-decision.json');human=read('examples/human-override.json')
check(auto['actor_kind']=='AUTO' and auto['status']=='accepted','Independent AUTO decision example')
check(all(x['company_id'] in {l['company_id'] for l in proposal['links']} and x['rubric_ref'] in rubrics and x['criterion_key'] in {c['key'] for c in rubrics[x['rubric_ref']]['criteria']} for x in proposal['rubric_proposals']), 'Rubric proposal link/catalog/criterion references')
check(human['subject_slot']==auto['subject_slot'] and human['supersedes_decision_id']==auto['decision_id'] and human['status']=='rejected','Same-slot human override example')
job=read('examples/job-event.json');check(job['mode']=='shadow' and set(job['payload'])=={'input_manifest_id','job_id'},'Synthetic job reference-only and shadow')
cases=read('examples/state-machine-cases.json');check(cases['synthetic'] and [c['change_event'] for c in cases['cases'] if c['change_event']]==['ENTER','EXIT','ENTER','RISK'],'State expected changes, NOT engine execution')
check(not any(c['delivery_expected'] for c in cases['cases']),'First phase zero delivery expectations')
check(cases['cases'][4]['display']=='UNKNOWN' and cases['cases'][4]['confirmed']=='IN','Unknown preserves baseline expectation')
boundary={c['id']:c for c in read('examples/v02-boundary-cases.json')['cases']}
check(boundary['T-30']['expected_count']==1 and boundary['T-32']['expected_current_state']=='IN','Gap/correction counterexamples recorded, NOT engine execution')
with localcontext() as ctx:
    ctx.prec=70;ctx.rounding=ROUND_HALF_EVEN;q=Decimal('0.000000000001')
    v=Decimal(10)*Decimal('.8')*Decimal('.5')*Decimal('.95')*Decimal('.8')
    check(str(v.quantize(q))==boundary['T-35']['expected_before_decay'] and str((v/2).quantize(q))==boundary['T-35']['expected_after_decay'],'Golden contribution / exact half-life arithmetic')
    check((v/Decimal(2).sqrt()).quantize(q)==Decimal('2.149604614807'),'Non-integer half-life golden arithmetic (sqrt cross-check)')
    check(Decimal(75)/Decimal(100)==Decimal('.75') and Decimal('.75')<Decimal('.8'),'Matched consolidated CFO/profit counterexample')
    check(Decimal('69.999999999999')<Decimal(70) and round(Decimal('69.999999999999'),1)==Decimal('70.0'),'Displayed 70.0 does not pass exact 70 threshold')

prd=(ROOT/'docs/01-product-requirements.md').read_text();accept=(ROOT/'docs/10-acceptance.md').read_text();plan=(ROOT/'docs/09-delivery-plan.md').read_text()
for n in range(1,18):check(f'R-{n:02}' in prd and f'R-{n:02}' in accept,f'Requirement trace: R-{n:02}')
for n in range(1,39):check(f'T-{n:02}' in accept,f'Acceptance scenario: T-{n:02}')
for n in range(1,9):check(f'W-{n:02}' in plan and f'W-{n:02}' in accept,f'Work trace: W-{n:02}')
for doc in ['docs/02-business-design.md','docs/07-ai-and-retrieval.md','AGENTS.md']:
    text=(ROOT/doc).read_text();check('必须人工复核' not in text and '高影响先人工批准' not in text,f'No superseded mandatory-human gate: {doc}')

from v03_material_checks import run as run_v03_checks
run_v03_checks(read,check,reject,resolve,bundle,scoring,canonical_hash)
for n in range(39,44):check(f'T-{n:02}' in accept,f'v03 acceptance scenario: T-{n:02}')
for d,v in scoring['dimension_policies'].items():
    check(v['event_policy']['half_life_days']==scoring['event_contribution']['half_life_calendar_days'][d],f'Standard event half-life policy agreement: {d}')

# Hash primary inputs only. Derived packs/paste files and report do not participate in self-referential hashes.
sources=[]
for pattern in ['README.md','PROJECT.md','CONTEXT.md','AGENTS.md','docs/*.md','docs/adr/*.md','research/*.md','config/*.json','contracts/*.md','contracts/*.json','examples/*.json','tools/*.py','tools/*.cjs','design/*.json','design/*.md','prototype/*.html','prototype/*.css','prototype/*.js','prototype/*.md','review/DESIGN-DETAIL-REVIEW.md','review/GPT-PRO-PROMPT.md','review/V02-CHANGELOG.md','review/V03-CHANGELOG.md','review/V03-COUNTEREXAMPLES.md','review/ROUND-2-*']:sources+=sorted(ROOT.glob(pattern))
sources=sorted(set(sources))
for p in sources:check(not re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}',p.read_text()),f'Targeted credential-pattern scan: {p.relative_to(ROOT)}')
revision=current_revision()
binding=(f'source_sha256 binds the exact inputs used by this run; Git HEAD at run was {revision}; no remote delivery claimed'
         if revision else
         'source_sha256 binds the exact working-tree inputs; Git revision unavailable; no remote delivery claimed')
report={'design_version':'0.3','design_date':'2026-10-01','executed_at':datetime.now(timezone.utc).isoformat(),'base_commit':'00ac20433c33a0a6296797c94d81136e0499e13f','revision_at_run':revision,'revision_binding':binding,'status':'passed','scope':'Offline material syntax, conservative subset Schema fixture checks, references, config semantics and synthetic arithmetic/counterexample expectations; NOT product runtime acceptance','check_count':len(checks),'checks':checks,'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sources},'not_run':['Full draft-2020-12 validation with a standards implementation','Runtime scoring/template/decision/state-machine implementation','Database/API/source integration and concurrency','Model/retrieval gold-set evaluation','Real UI/accessibility/device/UAT','Load/security/recovery exercises','External notification (deferred)']}
(ROOT/'review/validation-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(f'PASS: {len(checks)} material checks; {len(sources)} primary input hashes. Full JSON Schema library validation and product runtime acceptance NOT RUN.')
