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
| GET /information | company_id、topic、material_type、content_kind、published_from/to、time_basis、cursor | 新闻/摘要列表；发布时间未知单列，阅读不等待评分；详见§7 |
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
| POST /decisions/{slot_id}/overrides | OverrideCommand action=accept/reject/pending/replace，If-Match、Idempotency-Key | analysis.override；返回immutable revision/decision与generation，11 §7 |
| POST /decisions/{slot_id}/release-override | 同合同action=release，引用当前人工revision | analysis.override；清有效人工指针并固定cutoff重评，非恢复旧AUTO |
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


v0.3覆盖命令/201合成响应及预期持久化见11 §7与examples/v03-human-replacements.json。path slot是操作身份，body保留slot_id用于审计一致性；并发只用一个If-Match generation，服务端读取当前decision，不要求重复的expected decision/generation字段。普通覆盖端点不接受release动作，release端点只接受release。输入evidence_ids需包含新判断value中的全部证据。单项人工覆盖提交后直接返回影响和重算状态；preview仅用于批量、模板/策略发布和主数据合并等需要先比较影响的操作，绑定输入hash、slot generation、受影响证券及操作者。无权或过期预览不授权提交。内部seal命令非公开API，12 §8定义worker身份、冻结事务和提交原子性。

## 7. 资讯阅读接口与文件适配器

GET /information的过滤为company_id、topic、material_type、content_kind、published_from/to、time_basis=published|observed、cursor/limit；limit/ACL/snapshot沿用§1。公司筛选只使用有效已接受关联，歧义条目仍可在总体列表按候选/待关联说明阅读，不误挂公司。排序、未知发布时间和仅日期语义以04 §6为准。旧company timeline仍是聚合事件接口，新闻列表不能用它代替。

列表记录返回item_id、revision_id、title、summary_text、content_kind、reading_metadata、publication、observed_at、可见公司关联、body_access、reference_access[]和quality/reasons；详情沿用GET /information/{id}/revisions/{revision}返回这些字段及可用证据、事件/判断、父文件定位。publication和reading_metadata直接来自InformationEntry同源类型；写入端不接受actor/observed_at/accepted。服务端生成原文访问状态，不要求前端推断：

| 访问状态 | 页面表达/动作 | 语义 |
|---|---|---|
| available | 阅读原文（指确切target revision） | 实际已取得且当前可访问的source_document正文 |
| not_acquired | 来源入口；原文尚未取得 | 只返回获许可可见的url，不返回虚构body |
| no_locator | 暂无原文入口 | 只有来源名称，没有可用文章定位 |
| restricted | 依据暂不可访问 | 当前不可见正文/目标不返回ID、URL或摘录；保留有权摘要可读范围 |

body_access描述本材料自身正文：agent_digest默认无“新闻原文”，但可回查父报告；references各自描述被引用文章状态。同一摘要可能一条来源available、另一条not_acquired。资料详情始终分别展示摘要、上游Agent解读、系统有效判断、观察点；只有一个来源取得也不声称其他来源均核实。metadata_only与正文不可见保留§2现有语义。点击外部URL仅是阅读导航，后台不因页面打开自动下载。

目标SourceAdapter接口：capture(scope, logical_context)返回批次/原文件；normalize(raw_object, parse_version)返回InformationEntry[]、逐条错误和上游报告元信息；publish_result产生IngestionResult并关联实际run。解析按配置处理表头偏移、同义列、公司分段、文本URL与超链接，用同一DTO；同义列如“链接/来源链接/原文链接”，但不凭列名认定网址为具体正文。结构明确时使用规则解析，不强制逐行LLM。

批次输入固定本次文件范围、source/adapter/parse版本与模式；正文/摘要不放异步消息。继续复用ItemCaptured/ItemNormalized/IndexRequested，ItemNormalized可独立触发读取投影与analysis，不等待ScoreCompleted；公司关联可与影响分析独立决定。成功条目提交修订/观察/来源引用与outbox后即读可见；失败定位进入holes并产生partial输出；单条重试复用逻辑键，无全量重评或额外审核。

生成客户端入口在M0实施：后端DTO从固定Schema生成/导出，OpenAPI含资讯列表、详情和参考访问状态，再生成TS客户端。当前只是接口合同，未声称已有HTTP端点或生成客户端。

列表/详情共用字段已固定为[InformationRead 1.0](../contracts/information-read.schema.json)，阅读类型与解析DTO由材料检查核对同源。body_access/reference_access的state、可见url、target_revision_id均由后端返回；restricted/no_locator不返回目标ID或URL，available必须有确切目标修订。列表返回标准{data:InformationRead[],meta}，详情{data:InformationRead加可用body_text/evidence/events/decisions及parent locator,meta}；body_text只在本source_document正文available时返回，摘要页不虚构body。全文/父定位和判断属于既有详情合同，客户端按各自固定类型生成。合成expected_read_response是预期，不是HTTP回读。
