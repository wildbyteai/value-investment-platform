"""Execute and persist local research against actual accessible input revisions.

Preview runs have no seal token and never advance market membership.
"""
import json
from decimal import Decimal, localcontext
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models.runtime import ResearchRun, ItemRevision
from app.models.company import Security, ItemCompanyLink
from app.models.intake import InformationItem
from app.models.strategy import StrategyVersion
from app.services import data_mode
from app.services.scoring_service import score_company, score_security, inputs, config, numeric
from app.services.strategy_service import gates
from app.services.transactions import canonical, digest, record


def evidence_for(db,item):
    revision=db.get(ItemRevision,item.current_revision_id) if item.current_revision_id else None
    if not revision or digest(json.loads(revision.payload_json))!=revision.content_hash:return None
    return {'synthetic':False,'source_revision_id':revision.id,'hash':revision.content_hash,'locator':'readable_text','item_id':item.id}


def source_stats(db,item,ref):
    revision=db.get(ItemRevision,ref['source_revision_id']);payload=json.loads(revision.payload_json)
    original=payload.get('readable_text')
    if not original:return None
    data=payload.get('raw_capture')
    if data and data.get('report_type')=='reviewed_original_statements':
        from app.services.issuer_reports import analysis
        return analysis(data,ref)
    if data and data.get('report_type')=='financial_metrics':
        from app.services.baostock_financial import analysis
        meta=json.loads(item.reading_metadata_json)
        return analysis({**data,'observed_at':meta['source_observed_at']},ref)
    if data and data.get('provider')=='baostock':
        # Only the validated registered provider snapshot is interpreted.
        from app.services.baostock_source import validate
        meta=json.loads(item.reading_metadata_json)
        rows=validate({**data,'observed_at':meta['source_observed_at']})
        first,last=rows[0],rows[-1]
        with localcontext() as context:
            context.prec=50
            delta=numeric((Decimal(last['close'])/Decimal(first['close'])-1)*100)
        return {'kind':'market_summary','data_mode':'real_public','source_item_id':item.id,'source_revision_id':revision.id,
                'first_session':first['date'],'last_session':last['date'],'observations':len(rows),
                'first_close':first['close'],'last_close':last['close'],'change_pct':delta,'currency':'CNY','adjustment':'unadjusted',
                'meaning':'首末供应商日线收盘价的描述统计；不是总回报、预测或投资评分','evidence':[ref]}
    # Exact excerpt with a locator; no keyword grading or invented impact/rubric.
    return {'kind':'source_excerpt','source_item_id':item.id,'source_revision_id':revision.id,
            'excerpt':original[:320],'meaning':'引用已取得资料，尚未形成经营判断','evidence':[ref]}


def start_run(db,principal,command_key):
    request_hash=digest({'actor':principal.user.id,'mode':'real_research_preview','command_version':'1'})
    db.execute(select(func.pg_advisory_xact_lock(int(digest({'workspace':principal.workspace.id,'key':command_key})[:15],16))))
    old=db.scalar(select(ResearchRun).where(ResearchRun.workspace_id==principal.workspace.id,ResearchRun.command_key==command_key))
    if old:
        legacy_hash=digest({'actor':principal.user.id,'mode':'real_research_preview','algorithm':'local-research-preview-v1'})
        if old.request_hash not in (request_hash,legacy_hash):raise HTTPException(409,'运行命令已由其他请求使用')
        readable_run(db,old,principal.workspace.id)
        return old
    cutoff=db.scalar(select(func.now()))
    items=db.scalars(select(InformationItem).where(InformationItem.workspace_id==principal.workspace.id)).all()
    items=[item for item in items if data_mode.real_item(db,item,principal.workspace.id)]
    refs=[];stats_by_company={};company_ids=set();read_items=[]
    for item in items:
        ref=evidence_for(db,item)
        if not ref or not data_mode.real_evidence(db,[ref],principal.workspace.id,cutoff=cutoff):continue
        stats=source_stats(db,item,ref)
        if not stats:continue
        refs.append(ref);read_items.append({'item_id':item.id,'revision_id':ref['source_revision_id'],'hash':ref['hash'],'source_id':item.source_id})
        links=db.scalars(select(ItemCompanyLink).where(ItemCompanyLink.item_id==item.id,ItemCompanyLink.status=='accepted')).all()
        for link in links:
            if link.company_id:
                company_ids.add(link.company_id);stats_by_company.setdefault(link.company_id,[]).append(stats)
    if not refs:raise HTTPException(409,'尚无允许本地分析且可读的真实资料')
    companies=[c for c in data_mode.companies(db,principal.workspace.id) if c.id in company_ids]
    if not companies:raise HTTPException(409,'可读资料尚未关联到研究公司')
    if len(companies)>2:raise HTTPException(409,'本次验证范围最多两家公司')
    release=db.scalar(select(StrategyVersion).where(StrategyVersion.workspace_id==principal.workspace.id,StrategyVersion.published.is_(True)).order_by(StrategyVersion.version.desc()).limit(1))
    rules=json.loads(release.rules_json) if release else config('strategy-standard-v1.json')
    results=[];calculation_refs=[]
    for company in companies:
        quality=score_company(db,company,principal.workspace.id,cutoff,cutoff)
        rows=inputs(db,company.id,principal.workspace.id,cutoff,cutoff)
        quotes={row.input_key:json.loads(row.payload_json) for row in rows if row.kind=='price'}
        securities=[]
        for security in db.scalars(select(Security).where(Security.company_id==company.id)).all():
            valuation=score_security(db,security,principal.workspace.id,cutoff,cutoff)
            preview=gates(rules,quality,valuation)
            quote=quotes.get('price:'+security.ticker)
            outcome='UNKNOWN' if preview['passes'] is None else 'MATCH' if preview['passes'] else 'NO_MATCH'
            if release is None:outcome='UNKNOWN'
            # No formal session/calendar/close policy is configured: this run is a
            # traceable research preview, never a membership decision.
            securities.append({'security_id':security.id,'ticker':security.ticker,'market':security.market,'currency':security.currency,
                'latest_quote':quote,'valuation':valuation,'strategy':{**preview,'result':outcome,'applied':False,'release_id':release.id if release else None},
                'gaps':list(valuation['missing_data'])+(['需要发布策略版本'] if release is None else [])+['正式封存机制已实现；本证券的批准市场日历与FINAL收盘依据尚待接入']})
        results.append({'company_id':company.id,'company_name':company.name,'analysis':stats_by_company.get(company.id,[]),'quality':quality,'securities':securities})
        calculation_refs.append({'company_id':company.id,'inputs':quality['input_refs'],'judgments':quality['judgment_refs'],'template_hash':quality['template']['config_hash']})
    status='partial' if any(c['quality']['quality_score'] is None or any(s['strategy']['result']=='UNKNOWN' or s['gaps'] for s in c['securities']) for c in results) else 'completed'
    manifest={'algorithm':'local-research-preview-v2','mode':'real_research_preview','as_of':cutoff.isoformat(),'knowledge_cutoff':cutoff.isoformat(),
              'source_evidence':refs,'read_items':read_items,'calculation_refs':calculation_refs,
              'strategy':{'id':release.id if release else None,'version':release.version if release else None,'rules':rules,'hash':digest(rules)},
              'external_model':False,'membership_applied':False}
    result={'mode':'real_research_preview','status':status,'companies':results,'stages':[
        {'stage':'read_sources','status':'completed','detail':f'{len(read_items)}份可读真实资料，当前修订已固定'},
        {'stage':'analyze','status':'completed','detail':'实际行情/财务字段比较和原文摘录；财务口径与经营判断缺口明确保留'},
        {'stage':'score','status':'partial' if any(c['quality']['quality_score'] is None or any(s['valuation']['valuation_score'] is None for s in c['securities']) for c in results) else 'completed','detail':'执行真实输入评分；缺失项保持UNKNOWN'},
        {'stage':'strategy_preview','status':'partial','detail':'逐证券计算草稿规则；缺数为UNKNOWN，未正式封存或应用'},
    ]}
    run=ResearchRun(workspace_id=principal.workspace.id,actor_id=principal.user.id,command_key=command_key,request_hash=request_hash,
        manifest_json=canonical(manifest),manifest_hash=digest(manifest),result_json=canonical(result),status=status)
    db.add(run);db.flush()
    record(db,principal.workspace.id,principal.user.id,'research.preview_completed','research_run',run.id,{'manifest_hash':run.manifest_hash,'status':status})
    return run


def readable_run(db,run,workspace_id):
    if not run or run.workspace_id!=workspace_id:raise HTTPException(404,'没有该工作区的研究运行')
    manifest=json.loads(run.manifest_json)
    if not data_mode.real_evidence(db,manifest.get('source_evidence'),workspace_id):raise HTTPException(403,'输入资料的读取或分析权限已不可用')
    return run


def response(run):
    return {'id':run.id,'status':run.status,'manifest_hash':run.manifest_hash,'created_at':run.created_at.isoformat(),
            'manifest':json.loads(run.manifest_json),'result':json.loads(run.result_json)}
