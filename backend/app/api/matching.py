"""资讯→公司匹配 API（ADR 0016，docs/24 §6）：关注列表、公司别名、提及、建议关注、匹配任务、公司资讯流。

R10a publishes the contract (paths, schemas, permissions); a route whose PR has not landed answers
**501** with the standard error envelope, code ``not_implemented``. Permissions are checked before
that, so the contract for 401/403 already holds.

| 路由 | 权限 | 实现于 |
|---|---|---|
| GET /api/watchlist/companies | research.read | R10b |
| POST /api/watchlist/companies, PATCH/DELETE /api/watchlist/companies/{id} | watchlist.manage | R10b |
| GET /api/companies/{id}/aliases | research.read | R10b |
| POST /api/companies/{id}/aliases, DELETE …/aliases/{alias_id} | watchlist.manage | R10b |
| GET /api/companies/{id}/news | research.read | R10b |
| GET /api/news/events/{id}/mentions | research.read | R10b |
| GET /api/news/suggested-companies | research.read | R10b |
| POST /api/news/suggested-companies/add | watchlist.manage | R10b |
| POST /api/news/match-jobs/estimate, POST /api/news/match-jobs | rematch: watchlist.manage 或 news.reassess；reassess: news.reassess | R11 |
| GET /api/news/match-jobs, GET /api/news/match-jobs/{id} | research.read | R11 |
| POST /api/news/match-jobs/{id}/cancel | watchlist.manage 或 news.reassess（reassess 任务需 news.reassess） | R11 |
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator

from app.api.deps import Principal, require, require_any
from app.core.errors import Forbidden, NotImplementedYet
from app.core.paging import PageParams, page_params

watchlist_router = APIRouter(prefix='/api/watchlist', tags=['公司档案'])
companies_router = APIRouter(prefix='/api/companies', tags=['公司档案'])
news_router = APIRouter(prefix='/api/news', tags=['资讯雷达'])

READ = 'research.read'
MANAGE = 'watchlist.manage'
REASSESS = 'news.reassess'

AliasKind = Literal['name', 'short', 'en', 'former', 'ticker']
Market = Literal['SH', 'SZ', 'BJ', 'HK', 'US']
WatchStatus = Literal['active', 'archived']
JobKind = Literal['rematch', 'reassess']
NOT_IMPLEMENTED_RESPONSE = {501: {'description': '契约已发布、实现尚未合入（错误码 not_implemented）'}}


def _todo(pr: str, what: str):
    raise NotImplementedYet(f'{what}尚未上线（计划在 {pr} 实现）')


# ------------------------------------------------------------------ schemas

class SecurityRef(BaseModel):
    market: str
    ticker: str


class AliasOut(BaseModel):
    id: str
    company_id: str
    alias: str
    alias_norm: str = Field(description='归一化结果（matching/normalize.py），匹配时比较的就是它')
    kind: AliasKind
    market: Market | None
    source: Literal['seed', 'manual', 'suggested']
    created_at: str


class AliasIn(BaseModel):
    alias: str = Field(min_length=1, max_length=200)
    kind: AliasKind = 'short'
    market: Market | None = Field(None, description='kind=ticker 时可指明市场；不填按代码形状推断')


class AliasListOut(BaseModel):
    company_id: str
    items: list[AliasOut]


class WatchCompanyOut(BaseModel):
    id: str
    company_id: str
    company: str = Field(description='公司名')
    securities: list[SecurityRef]
    status: WatchStatus
    note: str
    alias_count: int
    links_30d: int = Field(description='近 30 天关联（确认 + 待确认）的事件数')
    added_by: str | None
    added_at: str


class WatchCompanyIn(BaseModel):
    company_id: str | None = Field(None, max_length=36, description='关注已有公司；与 name 二选一')
    name: str | None = Field(None, min_length=1, max_length=200, description='公司档案里没有时按名称新建')
    tickers: list[str] = Field(default_factory=list, max_length=10, description='新建公司时的证券代码，如 688428.SH、09969.HK')
    aliases: list[AliasIn] = Field(default_factory=list, max_length=50)
    note: str = Field('', max_length=2000)

    @model_validator(mode='after')
    def _one_of(self):
        if bool(self.company_id) == bool(self.name):
            raise ValueError('company_id 与 name 必须且只能填一个')
        return self


class WatchCompanyPatch(BaseModel):
    status: WatchStatus | None = None
    note: str | None = Field(None, max_length=2000)


class WatchCompanyPage(BaseModel):
    items: list[WatchCompanyOut]
    total: int
    limit: int
    offset: int


class MentionOut(BaseModel):
    id: str
    event_id: str
    name: str = Field(description='原文写法')
    name_norm: str
    ticker_raw: str | None
    ticker_norm: str | None
    market: Market | None
    relevance: float | None = Field(description='0..1')
    impact: float | None = Field(description='-1..1')
    key_point: str = Field(description='≤80 字要点')
    evidence: str = Field(description='原文证据（短引文）')
    extractor: str = Field(description='llm:<provider>/<model>@news-extract:v1 | rule:v1')
    company_id: str | None = Field(description='第二段匹配到的关注公司；null = 未关注或未匹配')
    link_id: str | None
    link_status: Literal['proposed', 'confirmed', 'rejected'] | None
    match_method: Literal['ticker', 'alias', 'contains'] | None
    created_at: str


class MentionListOut(BaseModel):
    event_id: str
    extract_status: Literal['pending', 'done', 'rule_only', 'failed']
    extract_version: str | None
    extracted_at: str | None
    items: list[MentionOut]


class SuggestedCompanyOut(BaseModel):
    name: str
    name_norm: str
    ticker_norm: str | None
    market: Market | None
    events: int = Field(description='近 days 天内提及它的事件数')
    last_seen_at: str | None
    sample_event_ids: list[str]
    company_id: str | None = Field(description='公司档案里已有（但本工作区未关注）时的公司 id')


class SuggestedCompanyPage(BaseModel):
    min_events: int
    days: int
    items: list[SuggestedCompanyOut]
    total: int
    limit: int
    offset: int


class SuggestedAddIn(BaseModel):
    name_norm: str = Field(min_length=1, max_length=200)
    name: str | None = Field(None, max_length=200, description='新建公司时用的名称；不填取最常见写法')
    ticker: str | None = Field(None, max_length=60)


class SuggestedAddOut(BaseModel):
    watch: WatchCompanyOut
    company_created: bool
    aliases_added: int


class MatchJobIn(BaseModel):
    kind: JobKind
    date_from: date | None = Field(None, description='按事件最后发布时间筛选（北京时间日期，含）')
    date_to: date | None = Field(None, description='含当天')
    event_ids: list[str] | None = Field(None, max_length=2000, description='只处理这些事件；与日期范围可同时给出（取交集）')

    @model_validator(mode='after')
    def _range(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError('date_from 不能晚于 date_to')
        return self


class MatchEstimateOut(BaseModel):
    kind: JobKind
    events: int
    estimated_calls: int = Field(description='预计调用大模型次数；rematch 为 0')


class MatchJobOut(BaseModel):
    id: str
    kind: JobKind
    params: dict
    status: Literal['queued', 'running', 'done', 'failed', 'cancelled']
    total: int
    processed: int
    links_added: int
    links_updated: int
    estimated_calls: int
    error: str | None
    created_by: str | None
    created_at: str
    started_at: str | None
    finished_at: str | None


class MatchJobPage(BaseModel):
    items: list[MatchJobOut]
    total: int
    limit: int
    offset: int


class CompanyNewsItemOut(BaseModel):
    link_id: str
    event_id: str
    title: str
    summary: str
    published_at: str | None
    status: Literal['proposed', 'confirmed']
    relevance: float | None
    impact: float | None
    key_point: str
    evidence: str
    match_method: Literal['ticker', 'alias', 'contains'] | None
    url: str | None = Field(description='代表性原文链接')


class CompanyNewsOut(BaseModel):
    company_id: str
    items: list[CompanyNewsItemOut]
    next_cursor: str | None = Field(description='下一页游标；null = 没有更多')


def _job_permission(principal: Principal, kind: str) -> None:
    if kind == 'reassess' and not principal.can(REASSESS):
        raise Forbidden('重新研判需要“批量重新研判资讯”权限（数据管理员或系统管理员）')


# ------------------------------------------------------------------ 关注列表

@watchlist_router.get('/companies', response_model=WatchCompanyPage, responses=NOT_IMPLEMENTED_RESPONSE)
def watch_list(status: WatchStatus | None = None, q: str | None = Query(None, max_length=100),
               params: PageParams = Depends(page_params), principal: Principal = Depends(require(READ))):
    """本工作区关注的公司（只有 active 的参与第二段匹配）。"""
    _todo('R10b', '关注列表')


@watchlist_router.post('/companies', response_model=WatchCompanyOut, status_code=201, responses=NOT_IMPLEMENTED_RESPONSE)
def watch_add(body: WatchCompanyIn, principal: Principal = Depends(require(MANAGE))):
    """关注一家公司（公司档案里没有就按名称新建，并写入别名）。"""
    _todo('R10b', '添加关注公司')


@watchlist_router.patch('/companies/{watch_id}', response_model=WatchCompanyOut, responses=NOT_IMPLEMENTED_RESPONSE)
def watch_update(watch_id: str, body: WatchCompanyPatch, principal: Principal = Depends(require(MANAGE))):
    """改状态（active / archived）或备注。"""
    _todo('R10b', '修改关注公司')


@watchlist_router.delete('/companies/{watch_id}', status_code=204, responses=NOT_IMPLEMENTED_RESPONSE)
def watch_delete(watch_id: str, principal: Principal = Depends(require(MANAGE))):
    """取消关注（已有关联保留）。"""
    _todo('R10b', '取消关注')


# ------------------------------------------------------------------ 公司别名 / 资讯流

@companies_router.get('/{company_id}/aliases', response_model=AliasListOut, responses=NOT_IMPLEMENTED_RESPONSE)
def alias_list(company_id: str, principal: Principal = Depends(require(READ))):
    _todo('R10b', '公司别名')


@companies_router.post('/{company_id}/aliases', response_model=AliasOut, status_code=201, responses=NOT_IMPLEMENTED_RESPONSE)
def alias_add(company_id: str, body: AliasIn, principal: Principal = Depends(require(MANAGE))):
    _todo('R10b', '添加公司别名')


@companies_router.delete('/{company_id}/aliases/{alias_id}', status_code=204, responses=NOT_IMPLEMENTED_RESPONSE)
def alias_delete(company_id: str, alias_id: str, principal: Principal = Depends(require(MANAGE))):
    _todo('R10b', '删除公司别名')


@companies_router.get('/{company_id}/news', response_model=CompanyNewsOut, responses=NOT_IMPLEMENTED_RESPONSE)
def company_news(company_id: str, cursor: str | None = Query(None, max_length=200),
                 limit: int = Query(30, ge=1, le=100), principal: Principal = Depends(require(READ))):
    """公司资讯流：已确认 + 待确认的关联，按时间倒序，游标分页。"""
    _todo('R10b', '公司资讯流')


# ------------------------------------------------------------------ 提及 / 建议关注 / 匹配任务

@news_router.get('/events/{event_id}/mentions', response_model=MentionListOut, responses=NOT_IMPLEMENTED_RESPONSE)
def event_mentions(event_id: str, principal: Principal = Depends(require(READ))):
    """第一段抽取出的全部公司提及（关注与否），及第二段匹配结果。"""
    _todo('R10b', '事件提及')


@news_router.get('/suggested-companies', response_model=SuggestedCompanyPage, responses=NOT_IMPLEMENTED_RESPONSE)
def suggested(params: PageParams = Depends(page_params), principal: Principal = Depends(require(READ))):
    """建议关注：近期被多条资讯提及、但本工作区未关注的公司。"""
    _todo('R10b', '建议关注')


@news_router.post('/suggested-companies/add', response_model=SuggestedAddOut, status_code=201, responses=NOT_IMPLEMENTED_RESPONSE)
def suggested_add(body: SuggestedAddIn, principal: Principal = Depends(require(MANAGE))):
    """一键关注（没有就新建公司并写入别名）。"""
    _todo('R10b', '一键关注')


@news_router.post('/match-jobs/estimate', response_model=MatchEstimateOut, responses=NOT_IMPLEMENTED_RESPONSE)
def match_estimate(body: MatchJobIn, principal: Principal = Depends(require_any(MANAGE, REASSESS))):
    """执行前预估：涉及事件数与预计大模型调用次数。"""
    _job_permission(principal, body.kind)
    _todo('R11', '匹配任务预估')


@news_router.post('/match-jobs', response_model=MatchJobOut, status_code=202, responses=NOT_IMPLEMENTED_RESPONSE)
def match_job_create(body: MatchJobIn, principal: Principal = Depends(require_any(MANAGE, REASSESS))):
    """排队一个 重新匹配（rematch）或 重新研判（reassess，需 news.reassess）任务，后台执行。"""
    _job_permission(principal, body.kind)
    _todo('R11', '匹配任务')


@news_router.get('/match-jobs', response_model=MatchJobPage, responses=NOT_IMPLEMENTED_RESPONSE)
def match_jobs(params: PageParams = Depends(page_params), principal: Principal = Depends(require(READ))):
    _todo('R11', '匹配任务列表')


@news_router.get('/match-jobs/{job_id}', response_model=MatchJobOut, responses=NOT_IMPLEMENTED_RESPONSE)
def match_job(job_id: str, principal: Principal = Depends(require(READ))):
    _todo('R11', '匹配任务进度')


@news_router.post('/match-jobs/{job_id}/cancel', response_model=MatchJobOut, responses=NOT_IMPLEMENTED_RESPONSE)
def match_job_cancel(job_id: str, principal: Principal = Depends(require_any(MANAGE, REASSESS))):
    """取消排队中或执行中的任务（已处理的部分保留）。"""
    _todo('R11', '取消匹配任务')
