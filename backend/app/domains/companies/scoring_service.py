"""Deterministic Decimal calculations; published/effective/knowledge bounds are separate."""
from app.core.paths import REPO_ROOT
import json
from datetime import datetime, timezone
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from pathlib import Path
from zoneinfo import ZoneInfo
from functools import wraps
from sqlalchemy import select, and_, or_
from app.models.runtime import ResearchInput, TemplateRelease
from app.models.judgment import JudgmentSlot, JudgmentRevision
from app.domains.platform import data_mode
from app.domains.platform.transactions import workspace, canonical, digest

ROOT = REPO_ROOT
UNIT = Decimal('0.000000000001')


def calculation(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with localcontext() as context:
            context.prec=50
            context.rounding=ROUND_HALF_EVEN
            return fn(*args, **kwargs)
    return wrapped


def config(name): return json.loads((ROOT / 'config' / name).read_text())
def dec(v): return Decimal(str(v))
def numeric(v): return format(q(v), 'f')

def q(v):
    with localcontext() as c:
        c.prec = 50
        return dec(v).quantize(UNIT, rounding=ROUND_HALF_EVEN)


@calculation
def linear(value, zero, full):
    return q(max(Decimal(0), min(Decimal(100), (dec(value)-dec(zero))/(dec(full)-dec(zero))*100)))


def resolve_template(company, db=None, workspace_id=None, at=None):
    if db is not None:
        conditions = [TemplateRelease.company_id == company.id,
                      TemplateRelease.workspace_id == workspace(db, workspace_id)]
        if at: conditions.append(TemplateRelease.created_at <= at)
        release = db.scalar(select(TemplateRelease).where(*conditions).order_by(TemplateRelease.version.desc()).limit(1))
        if release:
            result = json.loads(release.config_json)
            return {**result, 'release_id': release.id, 'config_hash': release.config_hash}
    base = config('scoring-standard-v1.json')
    result = {**base, 'weights': {k: float(v) for k,v in base['dimension_weights'].items()},
              'levels_applied': ['base'], 'origins': {k: 'base-standard@2' for k in base['dimension_weights']},
              'field_origins': {k: {f: 'base-standard@2' for f in ('weight','baseline','quality_policy','event_policy')} for k in base['dimension_weights']},
              'industry_key': company.industry_key}
    registry = config('dimensions-standard-v1.json')
    result['registry_hash'] = digest(registry)
    result['rubric_hash'] = digest(config('rubrics-standard-v1.json'))
    defaults = {entry['dimension']: entry for entry in registry['entries']}
    for d in result['weights']:
        policies = result.setdefault('dimension_policies', {}).setdefault(d, {})
        for field in ('quality_policy', 'event_policy'):
            policies.setdefault(field, defaults[d][field])
    for template in config('templates-standard-v1.json')['templates'][1:]:
        matches = ((template['level'] == 'industry' and template['scope']['industry_key'] == company.industry_key)
                   or (template['level'] == 'company' and company.id == template['scope']['company_id']))
        if not matches: continue
        result['levels_applied'].append('company' if template['level']=='company' else 'industry:'+company.industry_key)
        result = apply_patches(result, template['patches'], template['template_key']+'@'+str(template['version']))
    result['config_hash'] = digest(result)
    return result


def apply_patches(result, patches, origin):
    result = json.loads(canonical(result))
    registry = {e['dimension']: e for e in config('dimensions-standard-v1.json')['entries']}
    seen = set()
    for patch in patches:
        if set(patch) - {'dimension','weight','reason','baseline','quality_policy','event_policy','disabled'}:
            raise ValueError('存在不支持的模板字段')
        d = patch['dimension']
        if not isinstance(d, str): raise ValueError('维度标识必须为字符串')
        if d in seen: raise ValueError('同一维度不能重复patch')
        seen.add(d)
        if d not in registry: raise ValueError('维度尚未注册')
        if result.get('industry_key') and result['industry_key'] not in registry[d]['applicable_industries']:
            raise ValueError('维度不适用当前行业')
        if 'disabled' in patch:
            if patch['disabled'] is not True or set(patch) - {'dimension','disabled','reason'}:
                raise ValueError('禁用不能混用其他覆盖字段')
            if d in config('strategy-standard-v1.json')['quality_gates']['required_dimensions']:
                raise ValueError('必需维度不可禁用')
            for key in ('weights','baselines','dimension_policies'):
                result.get(key, {}).pop(d, None)
            result.setdefault('disabled_dimensions', {})[d] = origin
            continue
        if d not in result['weights']:
            if not d.startswith('x_') or not {'weight','baseline'} <= set(patch):
                raise ValueError('新增注册维度需要权重和完整baseline')
            result.setdefault('dimension_policies', {})[d] = {f: registry[d][f] for f in ('quality_policy','event_policy')}
        for field in ('baseline','quality_policy','event_policy'):
            if field in patch and not isinstance(patch[field],dict): raise ValueError('模板政策必须是对象')
        if d not in result['weights'] and not d.startswith('x_'):
            raise ValueError('未知维度')
        if 'weight' in patch: result['weights'][d] = float(dec(patch['weight']))
        if 'baseline' in patch: result['baselines'][d] = patch['baseline']
        if 'quality_policy' in patch:
            policies=result.setdefault('dimension_policies',{}).setdefault(d,{})
            policies['quality_policy']=patch['quality_policy']
        if 'event_policy' in patch:
            policies=result.setdefault('dimension_policies',{}).setdefault(d,{})
            policies['event_policy']=patch['event_policy']
        result['origins'][d] = origin
        origins = result.setdefault('field_origins', {}).setdefault(d, {f:'dimensions-standard-v1@1' for f in ('quality_policy','event_policy')})
        for field in ('weight','baseline','quality_policy','event_policy'):
            if field in patch:
                for stale_key in list(origins):
                    if stale_key.startswith(field+'.'): del origins[stale_key]
                origins[field] = origin
                if isinstance(patch[field], dict):
                    for key, value in patch[field].items():
                        origins[field+'.'+key] = origin
                        if isinstance(value, dict):
                            for subkey in value: origins[field+'.'+key+'.'+subkey] = origin
        result.get('disabled_dimensions', {}).pop(d, None)
    if sum(dec(v) for v in result['weights'].values()) != 1:
        raise ValueError('维度权重之和必须为1')
    if any(not dec(v).is_finite() or dec(v)<0 for v in result['weights'].values()):
        raise ValueError('权重必须为非负有限数值')
    catalog=config('rubrics-standard-v1.json')['rubrics']
    if data_mode.fixture_mode(): catalog={**catalog,**config('rubrics-synthetic-v03.json')['rubrics']}
    for d in result['weights']:
        if d not in result['baselines']:
            raise ValueError('新增维度需要完整baseline')
        baseline=result['baselines'][d]
        if baseline.get('method') not in registry[d]['allowed_baseline_methods']:
            raise ValueError('注册维度不允许该计算方法')
        if baseline.get('method')=='accepted_evidence_rubric':
            if baseline.get('rubric_ref') not in catalog: raise ValueError('rubric引用未发布')
        elif baseline.get('method')=='weighted_metric_rubric':
            metrics=baseline.get('metrics')
            if not isinstance(metrics,list) or not metrics: raise ValueError('需要完整指标定义')
            metric_registry=config('metric-definitions-v2.json')['metrics']
            for metric in metrics:
                if not isinstance(metric,dict) or not {'key','weight','zero_at','full_at'} <= set(metric): raise ValueError('指标形状错误')
                if metric['key'] not in metric_registry: raise ValueError('指标尚未定义')
                numbers=[dec(metric[k]) for k in ('weight','zero_at','full_at')]
                if not all(v.is_finite() for v in numbers) or numbers[0]<=0 or numbers[1]==numbers[2]: raise ValueError('指标数值不合法')
            if sum(dec(m['weight']) for m in metrics)!=1: raise ValueError('指标权重之和必须为1')
        else: raise ValueError('不支持的baseline方法')
        policies=result.get('dimension_policies',{}).get(d,{})
        event=policies.get('event_policy',{})
        if type(event.get('enabled')) is not bool or (event['enabled'] and set(event) != {'enabled','half_life_days'}) or (not event['enabled'] and set(event) != {'enabled'}):
            raise ValueError('事件政策不合法')
        if 'half_life_days' in event and (type(event['half_life_days']) is not int or not 1<=event['half_life_days']<=730):
            raise ValueError('半衰期必须为正整数')
        quality=policies.get('quality_policy',{})
        if set(quality)!={'evidence_requirement','freshness'} or quality.get('evidence_requirement') not in ('accessible_original','issuer_or_regulator_original'):
            raise ValueError('证据要求不合法')
        freshness=quality.get('freshness',{})
        if not isinstance(freshness,dict) or freshness.get('kind') not in ('age_days','report_obligation'): raise ValueError('新鲜度政策不合法')
        if freshness.get('kind')=='age_days' and (type(freshness.get('max_age_days')) is not int or not 1<=freshness['max_age_days']<=3650):
            raise ValueError('证据龄期必须为正整数')
        expected_kind='age_days' if baseline['method']=='accepted_evidence_rubric' else 'report_obligation'
        if freshness['kind']!=expected_kind or set(freshness)!=({'kind','max_age_days'} if expected_kind=='age_days' else {'kind'}):
            raise ValueError('新鲜度政策不符合维度计算方法')
    for d, policies in result.get('dimension_policies',{}).items():
        origins=result.setdefault('field_origins',{}).setdefault(d,{})
        for field, values in policies.items():
            for key,value in values.items():
                origins.setdefault(field+'.'+key,origins.get(field,'base-standard@2'))
                if isinstance(value,dict):
                    for subkey in value: origins.setdefault(field+'.'+key+'.'+subkey,origins.get(field,'base-standard@2'))
    result.pop('config_hash', None)
    result['config_hash'] = digest(result)
    return result


def input_time_bounds(as_of, cutoff):
    """Daily quotes may be published during the fixed post-close grace period.

    Business disclosures retain the close-time publication bound. Actual DB
    knowledge and, for seals, the commit ledger still enforce the cutoff.
    """
    quote = and_(ResearchInput.kind == 'price', ResearchInput.input_key.like('price:%'))
    return (ResearchInput.effective_at <= as_of, ResearchInput.known_at <= cutoff,
            or_(and_(quote, ResearchInput.published_at <= cutoff),
                and_(~quote, ResearchInput.published_at <= as_of)))


def inputs(db, company_id, workspace_id, as_of, cutoff):
    rows = db.scalars(select(ResearchInput).where(ResearchInput.company_id == company_id,
        ResearchInput.workspace_id == workspace_id, *input_time_bounds(as_of, cutoff))
        .order_by(ResearchInput.known_at, ResearchInput.id)).all()
    latest = {}
    for row in rows:
        if not data_mode.fixture_mode():
            payload=json.loads(row.payload_json)
            if row.synthetic or row.content_hash!=digest(payload) or not data_mode.real_evidence(db,payload.get('evidence'),workspace_id,company_id,cutoff): continue
        latest[row.input_key] = row
    return list(latest.values())


@calculation
def metrics_from_financials(f):
    def ratio(n,d): return q(dec(n)/dec(d)) if dec(d)>0 else None
    if not f or f.get('scope') != 'matching_ordinary_equity': return {}
    m = {'roe_ttm': ratio(f['ordinary_profit_ttm'],f['average_ordinary_equity']),
         'net_debt_ebitda': ratio(dec(f['debt'])-dec(f['cash']),f['ebitda_ttm']),
         'interest_coverage': ratio(f['ebit_ttm'],f['interest_expense_ttm'])}
    periods=f.get('annual_periods',[]);cfo=f.get('consolidated_cfo_3y',[]);profit=f.get('consolidated_profit_3y',[])
    if len(periods)==len(set(periods))==len(cfo)==len(profit)==3:
        m['cfo_profit_3y']=ratio(sum(map(dec,cfo)),sum(map(dec,profit)))
        m['positive_cfo_year_share_3y']=q(sum(v>0 for v in map(dec,cfo))/Decimal(3))
    return m


def decision_evidence_published_by(db, refs, as_of):
    """A judgment's approval time is not its underlying disclosure time.

    Use immutable source publication dates conservatively at local end of day;
    without such a date, only a source already acquired by close is provable.
    """
    if data_mode.fixture_mode():return True
    from app.models.runtime import ItemRevision
    from datetime import time
    for ref in refs:
        revision=db.get(ItemRevision,ref.get('source_revision_id',''))
        if not revision:return False
        raw=json.loads(revision.payload_json).get('raw_capture',{})
        dates=([d.get('disclosure_date') for d in raw.get('documents',[])] or [raw.get('disclosure_date')])
        if all(dates):
            try:
                bounds=[datetime.combine(__import__('datetime').date.fromisoformat(d),time.max,ZoneInfo('Asia/Shanghai')) for d in dates]
            except (ValueError,TypeError):return False
            if max(bounds)>as_of:return False
        elif revision.created_at>as_of:return False
    return bool(refs)


def current_decisions(db, company_id, workspace_id, as_of, cutoff, revision_ids=None):
    slots = db.scalars(select(JudgmentSlot).where(JudgmentSlot.company_id == company_id,
                        JudgmentSlot.workspace_id == workspace_id)).all()
    out=[]
    for slot in slots:
        revisions = db.scalars(select(JudgmentRevision).where(JudgmentRevision.slot_id==slot.id,
            JudgmentRevision.created_at <= cutoff).order_by(JudgmentRevision.created_at,JudgmentRevision.id)).all()
        # Published/effective bounds guard historical selection. Explicit release
        # clears prior AUTO/HUMAN; a subsequent legal reassessment is required.
        effective=None; auto=None
        for rev in revisions:
            if revision_ids is not None and rev.id not in revision_ids: continue
            if rev.effective_at and rev.effective_at>as_of: continue
            if rev.decision=='accepted' and not decision_evidence_published_by(db,json.loads(rev.evidence_json),as_of):continue
            if rev.author_type=='auto' and rev.decision=='accepted':
                auto=rev
                if effective is None or effective.author_type=='auto': effective=rev
            elif rev.author_type=='human':
                if rev.decision=='released': effective=None; auto=None
                elif rev.decision=='accepted': effective=rev
        if effective and not (effective.valid_until and as_of>=effective.valid_until) and (data_mode.fixture_mode() or data_mode.real_evidence(db,json.loads(effective.evidence_json),workspace_id,company_id,cutoff)):
            out.append((slot,effective,json.loads(effective.value_json)))
    out.sort(key=lambda entry:(entry[1].effective_at or entry[1].created_at,entry[1].created_at,entry[1].id),reverse=True)
    return out


@calculation
def score_company(db, company, workspace_id=None, as_of=None, cutoff=None, template=None, input_rows=None, decision_rows=None):
    workspace_id=workspace(db,workspace_id);as_of=as_of or datetime.now(timezone.utc);cutoff=cutoff or as_of
    if cutoff<as_of: raise ValueError('知识截止不能早于评估时点')
    template=template or resolve_template(company,db,workspace_id,cutoff)
    rows=inputs(db,company.id,workspace_id,as_of,cutoff) if input_rows is None else input_rows
    financial=next((json.loads(r.payload_json) for r in rows if r.kind=='financials'),None)
    observation=next((json.loads(r.payload_json) for r in rows if r.kind=='financial_observations'),None)
    if financial and as_of>=datetime.fromisoformat(financial['obligation_valid_until']): financial=None
    metrics=metrics_from_financials(financial)
    decisions=current_decisions(db,company.id,workspace_id,as_of,cutoff) if decision_rows is None else decision_rows
    rubric_catalog=config('rubrics-standard-v1.json')['rubrics']
    if data_mode.fixture_mode(): rubric_catalog={**rubric_catalog,**config('rubrics-synthetic-v03.json')['rubrics']}
    dimensions={};known={}
    for dim,weight in template['weights'].items():
        method=template['baselines'][dim];baseline=None;subcoverage=Decimal(0);refs=[];events=[];criterion_states=[];latest_age=None
        if method['method']=='weighted_metric_rubric':
            values=[]
            for metric in method['metrics']:
                v=metrics.get(metric['key'])
                if v is not None:
                    w=dec(metric['weight']);subcoverage+=w;values.append((linear(v,metric['zero_at'],metric['full_at']),w))
            if subcoverage>=dec(template['minimum_submetric_coverage']):
                baseline=q(sum(v*w for v,w in values)/subcoverage)
                refs=[r.id for r in rows if r.kind=='financials']
        else:
            rubric=rubric_catalog[method['rubric_ref']];grades=[]
            for criterion in rubric['criteria']:
                found=next(((s,r,v) for s,r,v in decisions if s.kind=='rubric' and s.dimension==dim
                            and v.get('criterion')==criterion['key'] and v.get('rubric_ref')==method['rubric_ref']
                            and v.get('period_start','9999') <= as_of.date().isoformat() <= v.get('period_end','0000')),None)
                criterion_state={'key':criterion['key'], 'anchors':criterion['anchors'], 'status':'missing', 'reason':'尚无适用期间的有效研判'}
                criterion_states.append(criterion_state)
                if found:
                    _,rev,value=found;evidence=json.loads(rev.evidence_json)
                    policy=template.get('dimension_policies',{}).get(dim,{}).get('quality_policy',{})
                    max_age=policy.get('freshness',{}).get('max_age_days',180)
                    acquired=rev.effective_at or rev.created_at
                    allowed=evidence and as_of<acquired+__import__('datetime').timedelta(days=max_age)
                    if policy.get('evidence_requirement')=='issuer_or_regulator_original':
                        allowed=allowed and all(e.get('issuer_original') for e in evidence)
                    age = max(0, (as_of-acquired).total_seconds()/86400)
                    criterion_state.update({'status':'valid' if allowed else 'stale_or_ineligible',
                        'reason':None if allowed else '证据类别或有效期限不满足当前模板',
                        'grade':value['grade'],'revision_id':rev.id,'age_days':age})
                    if allowed:
                        latest_age = max(latest_age or 0, age)
                        grades.append(dec(value['grade']));refs.append(rev.id)
            subcoverage=q(Decimal(len(grades))/len(rubric['criteria']))
            if grades and subcoverage>=dec(rubric['minimum_criterion_coverage']): baseline=q(sum(grades)/len(grades)/4*100)
        contribution=Decimal(0)
        policy=template.get('dimension_policies',{}).get(dim,{}).get('event_policy',{})
        if baseline is not None and policy.get('enabled',True):
            by_fact={}
            for slot,rev,value in decisions:
                if slot.kind=='impact' and slot.dimension==dim and json.loads(rev.evidence_json):
                    fact=value.get('economic_fact_id',slot.slot_key)
                    rank=(1 if rev.author_type=='human' else 0,rev.created_at,rev.id)
                    current=by_fact.get(fact)
                    if current is None or rank>(1 if current[1].author_type=='human' else 0,current[1].created_at,current[1].id):
                        by_fact[fact]=(slot,rev,value)
            for fact,(slot,rev,value) in sorted(by_fact.items()):
                age=dec(str(max(0,(as_of-(rev.effective_at or rev.created_at)).total_seconds())))/86400
                half=policy.get('half_life_days',template['event_contribution']['half_life_calendar_days'].get(dim,90))
                with localcontext() as ctx:
                    ctx.prec=70
                    amount=q(dec(template['event_contribution']['scale'])*dec(value['magnitude'])*dec(value.get('relevance','0.9'))
                             *dec(value.get('confidence','0.95'))*dec(value.get('source_quality','1'))*(Decimal(2)**(-age/dec(half))))
                contribution+=amount;events.append({'fact_id':fact,'revision_id':rev.id,'contribution':numeric(amount)})
            cap=dec(template['event_contribution']['cap_per_dimension']);contribution=q(max(-cap,min(cap,contribution)))
        score=q(max(Decimal(0),min(Decimal(100),baseline+contribution))) if baseline is not None else None
        if score is not None: known[dim]=score
        dimensions[dim]={'baseline':numeric(baseline) if baseline is not None else None,'event_contribution':numeric(contribution),
                         'score':numeric(score) if score is not None else None,'subcoverage':numeric(subcoverage),'evidence_ids':refs,'events':events,
                         'status':'valid' if score is not None else 'pending_evidence',
                         'reason':None if score is not None else '部分标准财务指标缺失或不适用，未达到最低有效指标覆盖' if method['method']=='weighted_metric_rubric' else '有效评价项不足',
                         'criteria':criterion_states,'baseline_age_days':latest_age}
    coverage=q(sum(dec(template['weights'][d]) for d in known))
    observed=q(sum(dec(template['weights'][d])*known[d] for d in known)/coverage) if coverage else None
    quality=observed if coverage>=dec(template['minimum_company_coverage']) else None
    missing=[]
    if quality is None:
        if not financial and any(template['baselines'][d]['method']=='weighted_metric_rubric' and d not in known for d in template['weights']):
            missing.extend(observation.get('missing_data',[]) if observation else ['可追溯的财务报告（TTM利润、权益、债务、现金流及报告义务时间）'])
        names={'business_model':'商业模式','governance':'治理与资本配置','growth_sustainability':'成长持续性'}
        for d in template['weights']:
            if financial and template['baselines'][d]['method']=='weighted_metric_rubric' and d not in known:
                missing.append(('盈利质量' if d=='profit_quality' else '财务韧性' if d=='financial_resilience' else d)+'：部分指标缺失或不适用，未达到最低有效指标覆盖')
            if template['baselines'][d]['method']=='accepted_evidence_rubric' and d not in known:
                missing.append(names.get(d,d)+'：仍有评价项未获合格依据，详见逐项状态')
    return {'company_id':company.id,'company_name':company.name,'template':template,'coverage':float(coverage),
            'coverage_exact':numeric(coverage),'known_dimensions':list(known),'dimensions':dimensions,
            'quality_score':float(quality) if quality is not None else None,'quality_exact':numeric(quality) if quality is not None else None,
            'observed_quality':numeric(observed) if observed is not None else None,
            'industry_key':company.industry_key,
            'risk_status':'clear', 'hard_risks':[v for s,r,v in decisions if s.kind=='risk' and v.get('confirmed')],
            'financial_valid':financial is not None,
            'metrics':{k:numeric(v) if v is not None else None for k,v in metrics.items()},
            'reasons':[] if quality is not None else ['INSUFFICIENT_EVIDENCE'],
            'data_mode':'synthetic_test' if data_mode.fixture_mode() else 'real_public',
            'financial_observations_available':observation is not None,
            'missing_data':missing,
            'as_of':as_of.isoformat(),'knowledge_cutoff':cutoff.isoformat(),
            'input_refs':[{'id':r.id,'hash':r.content_hash} for r in rows],
            'judgment_refs':[{'id':r.id,'slot':s.id,'generation':s.generation} for s,r,v in decisions]}


@calculation
def score_security(db, security, workspace_id=None, as_of=None, cutoff=None, session=None, input_rows=None):
    workspace_id=workspace(db,workspace_id);as_of=as_of or datetime.now(timezone.utc);cutoff=cutoff or as_of
    rows=inputs(db,security.company_id,workspace_id,as_of,cutoff) if input_rows is None else input_rows
    f=next((json.loads(r.payload_json) for r in rows if r.kind=='financials'),None)
    price=next((json.loads(r.payload_json) for r in rows if r.input_key=='price:'+security.ticker),None)
    if price and security.currency=='HKD' and not price.get('fx_per_cny'):
        from app.domains.market_data.ecb_fx import matching_fx
        _,fx=matching_fx(rows,price.get('session'))
        if fx:
            price={**price,'fx_per_cny':fx['value'],'fx_reference':fx,'evidence':price.get('evidence',[])+fx['evidence']}
    observation=next((json.loads(r.payload_json) for r in rows if r.kind=='financial_observations'),None)
    # An independent closing balance may supersede report-period capital,
    # without changing a single report-period financial fact or metric.
    capital_rows=[(r,json.loads(r.payload_json)) for r in rows if r.kind=='share_capital']
    capital_row,capital=max(capital_rows,key=lambda pair:(pair[1]['shares_as_of'],getattr(pair[0],'known_at',as_of),pair[0].id)) if capital_rows else (None,None)
    report_day=max((fact['period_end'] for fact in (f or {}).get('lineage',{}).get('facts',[]) if fact['key']=='ordinary_shares'),default='0001-01-01')
    if capital and capital['shares_as_of']<report_day:capital_row,capital=None,None
    share_basis=capital or f
    shares_current=bool(share_basis and (not share_basis.get('ordinary_shares_valid_until') or as_of<datetime.fromisoformat(share_basis['ordinary_shares_valid_until'])))
    # Preserve later known changes until a balance after that change is verified.
    if capital and f and f.get('ordinary_shares_valid_until'):
        change=datetime.fromisoformat(f['ordinary_shares_valid_until'])
        if capital['shares_as_of']<change.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat() and as_of>=change:shares_current=False
    shares_verified=bool(share_basis and (not share_basis.get('ordinary_shares_verified_through') or as_of.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()<=share_basis['ordinary_shares_verified_through']))
    shares_current=shares_current and shares_verified
    gaps=[]
    if not price:gaps.append('未取得对应证券正式收盘价')
    elif not price.get('is_final') or (session and price['session']!=session):gaps.append('已取得日线价格，但正式收盘最终性或对应交易日尚未核验')
    if not f:gaps.extend(observation.get('missing_data',[]) if observation else ['普通股TTM利润、等权股本及有效期'])
    if share_basis and not shares_current:gaps.append('股数证据仅覆盖较早日期，需核对当前流通在外同权普通股数量' if not shares_verified else '已知期后股数变动，需核对最新流通在外同权普通股数量')
    if security.currency!='CNY' and (not price or not price.get('fx_per_cny')):
        has_reference_fx=security.currency=='HKD' and any(r.kind=='fx' for r in rows)
        gaps.append('已取得参考汇率；待证券行情确定后匹配同日汇率' if has_reference_fx and not price else '跨币种估值需要对应汇率')
    result={'security_id':security.id,'market':security.market,'ticker':security.ticker,'currency':security.currency,
            'pe_ttm':None,'valuation_score':None,'reason':'UNKNOWN_PE','latest_quote':price,
            'share_capital':{**capital,'input_id':capital_row.id} if capital else None,
            'missing_data':gaps, 'data_mode':'synthetic_test' if data_mode.fixture_mode() else 'real_public','input_refs':[r.id for r in rows], 'approved_inputs':bool(rows), 'price_final':bool(price and price.get('is_final')), 'price_lag_sessions':0 if price and price.get('is_final') and (not session or price.get('session')==session) else None, 'common_equity':bool(shares_current and share_basis.get('equivalent_share_rights')), 'suspended':bool(price and price.get('tradestatus')=='0')}
    if not f or not price: return result
    if not shares_current:return {**result,'reason':'SHARE_BASIS_NOT_CURRENT' if not shares_verified else 'SHARE_BASIS_EXPIRED','common_equity':False}
    if not price.get('is_final') or (session and price['session']!=session):
        return {**result,'reason':'FINAL_PRICE_REQUIRED'}
    if any(k not in price for k in ('currency','fx_per_cny','raw_close','evidence')):
        return {**result,'reason':'INCOMPLETE_PRICE_BASIS','missing_data':gaps+['行情币种、汇率或原始价格证据不完整']}
    if (not share_basis.get('equivalent_share_rights') or price['currency']!=security.currency
        or dec(share_basis['ordinary_shares'])<=0 or dec(f['ordinary_profit_ttm'])<=0 or dec(price['fx_per_cny'])<=0
        or as_of>=datetime.fromisoformat(f['obligation_valid_until'])):
        return {**result,'reason':'INVALID_SHARE_FINANCIAL_OR_FX','missing_data':['股本/盈利/币种/汇率或报告有效期不满足估值条件']}
    eps=q(dec(f['ordinary_profit_ttm'])/dec(share_basis['ordinary_shares']));converted=q(eps*dec(price['fx_per_cny']))
    pe=q(dec(price['raw_close'])/converted);v=config('scoring-standard-v1.json')['valuation']
    return {**result,'pe_ttm':float(pe),'pe_exact':numeric(pe),'valuation_score':float(linear(pe,v['zero_score_at'],v['full_score_at'])),
            'valuation_exact':numeric(linear(pe,v['zero_score_at'],v['full_score_at'])),'reason':None,'missing_data':[],
            'basis':{'ordinary_profit_ttm':f['ordinary_profit_ttm'],'ordinary_shares':share_basis['ordinary_shares'],
                     'share_evidence':share_basis['evidence'],
                     'eps':numeric(eps),'fx':price['fx_per_cny'],'converted_eps':numeric(converted),'raw_final_close':price['raw_close'],
                     'session':price['session'],'evidence':price['evidence']}}
