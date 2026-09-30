# 04 数据模型、时间与约束

## 1. 数据分层

对象存储保留获许可原文和快照，PostgreSQL 保存身份、结构化事实、已批准判断和状态；OpenSearch／向量库保存带 ACL 的可重建索引。每条派生结果能追到 source、item_revision、chunk/证据定位、分析版本、AUTO/HUMAN判断、模板解析配置、评分快照和策略评估。

关系图：workspace→source→ingestion_run→item→item_revision→evidence；item_revision↔event_revision；item_revision/event_revision↔company；company→security→price_bar；company→financial_fact/baseline→score_snapshot；security+score_snapshot+strategy_release→evaluation→membership_transition；后续notification→delivery。

## 2. 表设计（逻辑结构；物理迁移在 M0 完成）

所有 ID 为 UUID；金额、比例和精确指标 numeric，禁止 float 进入财务计算。审计时间 UTC timestamptz；原始时区与日期粒度保留。事实修订不能 UPDATE 内容；可变指针、任务租约、membership 与草稿是明确例外。

| 表 | 核心字段／关系 | 唯一约束与写责任 |
|---|---|---|
| workspace / membership_user | workspace_id, user_id, capabilities, scope | workspace+user；governance |
| source | workspace, name, adapter, policy_id, credential_ref, version, enabled | workspace+source_key；ingestion；secret 不入表 |
| source_policy | allow_fetch/store/analyze/export, ACL, expiry, retention, approval_ref | source+version；批准后的权利版本不可变 |
| source_schedule | source, partition, cron, timezone, generation, next_due | source+partition+generation；调度变更留审计 |
| ingestion_run / checkpoint | source, partition, due_at, mode, manifest, cursor, holes | run(source,partition,due,generation)；checkpoint 乐观版本 |
| raw_object | workspace, object_key, sha256, size, mime, policy, status | workspace+source+content_hash；保留 rights provenance |
| information_item | source, external_id, canonical_url_hash, latest_revision_id | source+external_id；无 external_id 才用 source+URL hash |
| item_observation | item, observation_seq, revision_ref, observed_at, previous_observation | item+sequence；A→B→A保留三次观测；information |
| item_revision | item, content_hash, object, normalized_hash, published_at, observed_at, parse_version, supersedes, status | item+content_hash+parse_version；一份内容可有不同解析修订 |
| evidence | revision, locator_kind, start/end or cell, quote_hash, text, source_quality | revision+locator+quote_hash；不可把摘要当原文 |
| company / company_alias | legal identity, market identifiers, alias language/context, valid range | 内部 company_id 稳定；同名不唯一 |
| security | company, ISIN, share_class, primary_listing_id, valid range | 公司股权工具身份；A/H独立；identity |
| listing | security, exchange, symbol, currency, calendar_ref, close_policy, valid range | exchange+symbol+有效期不重叠；首版一只security固定主要listing |
| company_relation | from/to, type, ownership, valid range, known_at, evidence | 带有效期、版本和来源；合并／拆分留映射历史 |
| analysis_run | revision, model/prompt/schema versions, input_hash, usage, decision | input+versions+mode；原始模型响应受控保留与脱敏 |
| item_company_link | item_revision, company, type, relevance, confidence, evidence, status | revision+company+type+analysis_revision；approved 指针唯一 |
| event / event_revision | event_id, action/object, event_time/range, claims, status, known_at, supersedes | 语义相似不能作为唯一键；人工可拆／合并 |
| event_evidence | event_revision, item_revision, evidence, stance | event_revision+evidence；stance=support/refute/context |
| event_company_impact | event_revision, company, dimension, signed_impact, relevance, confidence, half_life, valid_until, review | event_revision+company+dimension+decision_revision |
| review_decision / decision_slot | subject_slot/revision, status, actor_kind, actor, policy/version, input_manifest, known_at, valid_until, supersedes, current_pointer | 决策append-only；指针CAS；有效人工覆盖优先，服务身份也需权限 |
| financial_fact | company, metric, fiscal_period, report_type, consolidated, currency, unit, value, announced_at, observed_at, revision | company+metric+period+口径+source+revision |
| price_bar / fx_rate / corporate_action | security/FX pair, market_session/effective_at, raw_close, currency, source, observed_at, revision | 同 source 同 session+revision；保留纠错和原始价格 |
| report_obligation | company, market/board, report_type, required_period, due_at, grace, exception, policy/source | company+obligation+version；fundamentals；未配置不能猜新鲜度 |
| baseline_dimension | company, dimension, score, rubric, evidence, valid range, known_at, absorbed_events | company+dimension+revision；明确已吸收 contribution IDs |
| metric_snapshot | security, as_of, input_manifest, metric_version, values, quality | input_hash+version；decimal JSON 用字符串 |
| score_snapshot / score_dimension / score_contribution | company, as_of, manifest, model_version, coverage, quality, baseline, contributions | company+input_hash+model_version；完整发布指针 CAS |
| scoring_template / template_version / scoring_binding | workspace, level/scope, pinned_parent, patches, content_hash; company→resolved_manifest/hash | 发布不可变，draft ETag；scoring拥有，strategy release固定绑定 |
| research_note / saved_view | owner, visibility, company/filter, content, revision | workspace+owner+id；服务端持久化，ETag冲突不覆写 |
| strategy / strategy_version / strategy_release | workspace, owner, config, hash, parent, approval, active_from | strategy+version；发布版本不可变且禁止修改 active 内容 |
| strategy_evaluation | release, security, market_session, context_hash, rule_results, mode, known_at | release+security+session+context_hash+mode；不可覆写 |
| strategy_membership | release, security, confirmed_state, display_state, pending_sessions, last_applied_session, finalization_token, generation, evaluation | release+security；锁／CAS 是唯一状态写入口 |
| membership_transition | membership, from/to, reason, evidence_snapshot, evaluation, transition_seq | membership+seq；事件唯一且 append-only |
| correction_run / correction_record | original_evaluation, affected_window, anchor, replacement_manifest, reconciliation, generation | append-only；保留原转移，不让旧更正覆盖当前 |
| subscription / notification / delivery（后续） | user, strategy/security, channels; transition/risk+recipient; attempt/status/provider_ref | delivery(notification,recipient,channel)；去重键永久保留到策略审计期限 |
| job / outbox / inbox_dedupe | stage, entity_revision, logical_time_context, input_hash, mode, generation, lease, attempts; event_id | job 唯一业务键；inbox(consumer,event_id)；原子写 |
| audit_event | actor, workspace, action, object_revision, request_id, before/after hash, reason | append-only；受控脱敏，不能保存 secret 值 |

默认 workspace 私有，所有查询包含 workspace/ACL。市场公共主数据可复用全局只读层；只有获许可公共事实允许进入共享层，私有笔记、判断和策略不进入。关联表要求复合外键保证同 workspace，不能只依赖前端过滤。

## 3. 时间语义与历史查询

- event_time：现实发生时间；可能只有日期／时间范围，精度字段不可省略。
- published_at/announced_at：来源公开发布时间；不能直接替代发生时间。
- observed_at：系统第一次获得某修订的时间，不回填为旧发布日期。
- valid_from/to：某经营关系或人工判断适用的业务区间，半开 [from,to)。
- known_at：某结构化判断可供系统使用的最早时间，至少不早于全部输入 observed_at 和有效AUTO/HUMAN决策时间。
- evaluation_as_of：研究所针对的市场时点；knowledge_cutoff：允许使用知识的截止时间；generated_at：实际运算完成时间。

实时：evaluation_as_of≤knowledge_cutoff≤生成时点。无未来数据历史回放：知识可用时间≤当时 knowledge_cutoff，财报采用 announced_at 与 observed_at 同时满足的版本；晚到材料只能影响其系统实际知悉之后的状态。另提供 research_reconstruction 模式按当时公开时间重建，但明确“不代表系统当时已知”，默认不发送通知，禁止与 live 历史混合统计。

后来修订的财报、别名、关系、复核不可穿越回去覆盖旧判断。历史快照固定算法、prompt、来源修订及 ACL 政策版本；重算生成新的 run。仅重放已有结构化产物能严格确定性；重新调用模型称为 reanalysis，不承诺相同输出。

时间线默认事件发生时间；未知时显示“发布时间代用”，不假造顺序；可以切换“我何时得知”。同时间使用 stable event_id tie-breaker；筛选和游标查询固定 snapshot，新增数据提示刷新而不打乱阅读位置。

## 4. 质量与新鲜度合同

quality 状态 valid/missing/stale/conflicting/unsupported/pending_review/suspended，各有 reason_code 与 required_action。null 与“不适用”和“值为 0”不同。财务源优先次序由获许可来源合同确定，冲突不平均解决；货币不同不直接拼比率；累计季报需转单季时记录相减来源，TTM 用四季或年度+本年累计-去年同期，严防重复求和。

行情新鲜度参照 exchange_calendar 与最后应有的 market_session，而不是距现在 24 小时；节假日和停牌独立处理。财务按report_obligation与指标所需期间判断；移除统一180日公告龄限制，三年旧年度不得一刀切过期，旧更正不能满足新报告义务（12 §1）。过期保留旧值用于解释，但 evaluation quality gate 不可使用。

## 5. 关键索引和容量

PG 索引：(workspace,company,event_time desc,event_id)、(workspace,security,market_session desc)、(company,metric,fiscal_period,known_at desc)、(release,security,as_of desc)、job(status,next_attempt)、outbox(published_at null)、audit(workspace,time)。策略列表从已完成 snapshot 的读模型分页，禁止前端逐行 N+1 获取评分。

OpenSearch mapping：keyword company_id/security_id/source/ACL，date 时间，中文 analyzer 正文，title 较高权重；股票代码 keyword 优先精确命中，不分词；源权利／撤销 tombstone 同步所有投影。向量记录 chunk_id、embedding_model/version/dim、内容 hash、workspace、ACL、日期；不同 model namespace 禁止混算距离。

数据保留期限由 source_policy 驱动：原文撤回或到期后关闭证据访问，删除受控投影并记录 tombstone；审计保留哈希／引用及“依据已不可访问”，不为重现违规保留全文。备份到期清理与恢复后再施加 tombstone 是合同的一部分。默认保留期限是待决定的运行配置，不强行永久存全部原文。

economic_fact与contribution_slot防止跨event重复；baseline吸收同事务更新slot。score/metric/evaluation记录template_resolution_hash、numeric_policy_ref、required_source_ids与权限指纹。撤权后派生总分、计数和缓存同样重新校验。原文observation、主挂牌、FINAL价格标记及独立撤权journal完整定义见12。
