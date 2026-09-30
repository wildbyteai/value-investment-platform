# 05 API、异步任务与并发合同

## 1. 同步 API 通则

REST /api/v1；完整 OpenAPI 由 M0 后端 DTO 生成，当前文档是详细合同目录，JSON Schema 是跨端关键对象合同。OIDC 会话建议 BFF/同域 HttpOnly Cookie，CSRF 检查与合理 SameSite；跨域 Token 模式须单独审核。服务端鉴权，列表、详情、导出、任务和证据下载均应用相同 ACL。

返回 {data,meta:{request_id,snapshot_id,generated_at,data_as_of,quality}}；分页 opaque cursor 包含过滤 hash 和 snapshot，limit 默认 30、最大 100；排序有稳定 ID 次键。金钱/比例 numeric 在 JSON 用 decimal 字符串，分数亦用 decimal 字符串；日期 ISO 8601，单位与币种明确；unknown 使用 null+reason。

修改草稿支持 ETag/If-Match；缺 expected version 返回 428，版本冲突 409。写请求 Idempotency-Key 与 actor+workspace+route+payload_hash 绑定，重用相同 key 不同 payload 返回 409；重试相同 payload 返回原结果。保存 7 日是默认提案，长期业务唯一约束另外保证。

错误体符合 Problem Details 思路：type/title/status/code/detail/instance/request_id/field_errors；detail 不含内部 URL、SQL、模型提示词或 secret。400 无效参数，401 未认证，403 权限不足，404 不存在或不可见对象（不可泄露），409 冲突，422 合同或业务规则错误，429 配额，503 依赖不可用。部分内容故障返回 200+quality，不伪装完整有效。

## 2. 业务端端点

| 方法与路径 | 输入与输出 | 权限／行为 |
|---|---|---|
| GET /me | capability 与首选项 | 只返回本人 |
| GET /dashboard | as_of, strategy_id；关注变化、质量概览 | 完整 snapshot；不用全局大屏排行榜 |
| GET /companies | query, filters, cursor；身份+经营分+coverage | 只读；过滤状态可分享 URL |
| GET /companies/{id} | securities、经营摘要、关键变化 | 公司名称+各证券市场明确区分 |
| GET /companies/{id}/timeline | event/published/known time, dimension,r_min,cursor | 聚合事件、已批准关联、待复核可独立筛选 |
| GET /companies/{id}/scores | snapshot/as_of；维度、基准、贡献、缺口 | 解释与总分来自同一 snapshot |
| GET /securities/{id}/valuation | snapshot/as_of；价格、FX、分母与质量 | A/H 独立、停牌/过期说明 |
| GET /information/{id}/revisions/{revision} | 来源、证据、关联、事件 | metadata_only 不返回虚构正文 |
| GET /events/{id} | 历史修订、支持／反驳来源、公司影响 | 权限过滤后仍显示“部分证据不可见” |
| POST /search | q, company_ids,date range,types,mode,cursor | 精确／全文／语义，可降级；ACL 在检索前应用 |
| GET /strategies | 本人／组织可见版本与区间数量 | 不泄露他人私有规则 |
| GET /strategies/{id}/evaluations | security,state,release,snapshot | 每规则结果 true/false/unknown 与原因 |
| POST /strategies/{id}/drafts | config,parent_release | strategy.edit；JSON Schema 校验 |
| POST /strategy-drafts/{id}/simulations | fixed_as_of,universe_manifest | strategy.simulate；202 job，不发通知 |
| POST /strategy-drafts/{id}/publish | If-Match,preview_id,preview_hash,confirmation | strategy.publish；预览过期 409，无效不能发布 |
| POST /strategy-releases/{id}/rollback-preview | target_version,as_of | 生成新发布提案与变化预览，不直接修改旧版 |
| GET/PATCH /watchlists/{id} | security_ids，If-Match | 本人，越权证券不可附加 |
| GET /changes | type,strategy,company,as_of,cursor | 首版变化记录；固定历史解释，再看当前 |
| GET /notifications（后续） | unread,type,strategy,cursor | 本人；显示原因和证据入口 |
| POST /notifications/{id}/ack（后续） | reviewed/snooze+until | 不改变 membership；读过和处理过分开 |
| PUT /subscriptions/{id}（后续） | strategy/security,channels,quiet_hours | 本人；首次外部连接验证后方可 enabled |
| POST /reviews | subject_revision,decision,reason,evidence,If-Match | analysis.override，拒绝stale subject；11定义人工优先与依赖重算 |
| GET /evidence/{id}/access | 受控代理或短期 signed URL | source_policy 再校验，访问留日志 |

## 3. 管理端端点

/admin/sources CRUD 草稿；/sources/{id}/preview、publish、pause、resume；/source-runs 和 /jobs；/jobs/{id}/retry-preview、retry；/identity/merge-preview、merge、split；/review-queue；/rubrics/versions；/models/policies；/index/rebuild-preview、rebuild；/users/capabilities；/audit；/quality；/costs。批量/发布/会改变已生效状态的动作分preview→confirm；常规草稿保存和小范围编辑直接操作，避免逐项审批。预览返回预计对象、请求量、费用、变化数与回滚说明。删除数据、改权限、源授权和历史重放不能混进“重试失败任务”。

授权不是按钮显隐：对应 capability 且目标 workspace 合法。管理员可以查看运行状态，但 business strategy.publish 和 analysis.override独立授权。preview object 与请求 hash、版本、负责人绑定；确认后 202 task_id，任务详情可追溯。

## 4. 异步事件合同

事件共同字段见 contracts/job-event.schema.json：event_id、event_type、schema_version、workspace_id、entity_id/revision、occurred_at、trace_id、mode、generation、payload引用及evaluation_context（固定as_of/cutoff/time_bucket/版本）。类型包括 ItemCaptured/ItemNormalized/AnalysisProposed/DecisionAccepted/DecisionOverridden/TemplatePublished/CorrectionRecorded/EventChanged/FundamentalChanged/ScoreCompleted/StrategyEvaluated/MembershipChanged/NotificationRequested/IndexRequested。消费者不信任消息内权限，重新从事实库校验。

mode=live/backfill/replay/shadow/research_reconstruction。只有 live 且本次 source/strategy/subscription 权利均有效才可外部通知。事件发生与实际投递时间分开；任务传播 mode 不能默认回 live。

默认 job 重试最多 5 次，指数退避 30s 起、上限 30min、随机 jitter；源 429 服从 Retry-After 且并发配额全源共享；认证/权限/Schema 错误无盲重试。LLM 合同错误最多一次受限修复，仍失败进入人工队列；按已配置任务配额判断是否可重试，开发不强制固定月度预算。DLQ 保留错误分类和指针，不放秘密或完整原文。

## 5. 事务与并发示例

### 策略评估提交

1. 以固定 input_manifest 计算规则，不锁整个系统。
2. BEGIN；取得 membership 行锁，验证 release 当前、expected generation、session 与 context。
3. 若已消费 evaluation_id 则返回同结果。若输入过时则记录 superseded、终止状态变更。
4. 更新确认计数／状态；仅相邻expected FINAL sessions推进且finalization_token唯一；较早session不改当前，封存后走CORRECTION。生成transition+解释snapshot+outbox+audit，统一 COMMIT。
5. relay 投递；首版consumer处理后续业务/索引；后续通知consumer才按delivery唯一键领发送任务。

双 Worker 并行同证券时只允许一个转移；丢 ACK 重试不生成第二条。其他公司独立并发，不全局锁。评分发布 CAS 与评估 generation 防止慢任务覆盖新财报。

### 通知外部副作用

渠道支持幂等键时发送 delivery_id 为 provider key。若 provider 不支持，发送超时结果标为 UNKNOWN_DELIVERY，查询投递状态或人工确认，不能盲重发导致重复。数据库 exactly-once 业务记录不能证明外部信道 exactly-once。业务变化记录仍可正常访问；没有渠道授权不能发送测试消息。

### 主数据合并

merge-preview 展示证券、别名、事件、评分和策略影响；confirm 写不可变 merge decision、alias redirect、新 identity generation 并触发固定范围重算。不删除旧 company_id；历史引用旧版本仍可解释，当前查询显式跳转。split 与误合并恢复同理，不直接批量 UPDATE 历史。

## 6. 客户端合同

前端只调用生成客户端；TanStack Query keys 包括 workspace、filters、snapshot，切换 workspace 清除敏感缓存。写成功按后端返回 revision 精确失效相关 query，不强制整页刷新。未知任务状态显示“等待更新”并提供 request_id。核心变化与任务更新可 SSE（只发 ID、质量／进度），断线退回有限轮询；SSE 不必保证消息持久性，刷新从事实库取得正确状态。

模板解析/模拟/发布、企业评分绑定、人工覆盖/解除、研究笔记/保存视图、用户角色端点详见11 §6。API返回有效父链与字段来源；发布固定binding manifest。POST /correction-previews与POST /corrections采用12 §4的窗口/锚点、If-Match和scope，返回固定历史解释和当前影响；禁止通过普通job retry回写封存session。
