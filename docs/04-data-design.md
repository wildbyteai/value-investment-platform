# 04 数据模型、时间与约束

## 1. 数据分层

对象存储保留获许可原文和快照，PostgreSQL 保存身份、结构化事实、已批准判断和状态；Elasticsearch／向量库保存带 ACL 的可重建索引。每条派生结果能追到 source、item_revision、chunk/证据定位、分析版本、AUTO/HUMAN判断、模板解析配置、评分快照和策略评估。

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
| item_source_reference | item_revision、reference_key、source_name、url、locator_kind、target_revision | 一条摘要多来源；未取得正文可无target；描述固定，目标首次绑定CAS |
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

Elasticsearch mapping：keyword company_id/security_id/source/ACL，date 时间，中文 analyzer 正文，title 较高权重；股票代码 keyword 优先精确命中，不分词；源权利／撤销 tombstone 同步所有投影。向量记录 chunk_id、embedding_model/version/dim、内容 hash、workspace、ACL、日期；不同 model namespace 禁止混算距离。

数据保留期限由 source_policy 驱动：原文撤回或到期后关闭证据访问，删除受控投影并记录 tombstone；审计保留哈希／引用及“依据已不可访问”，不为重现违规保留全文。备份到期清理与恢复后再施加 tombstone 是合同的一部分。默认保留期限是待决定的运行配置，不强行永久存全部原文。

economic_fact与contribution_slot防止跨event重复；baseline吸收同事务更新slot。score/metric/evaluation记录template_resolution_hash、numeric_policy_ref、required_source_ids与权限指纹。撤权后派生总分、计数和缓存同样重新校验。原文observation、主挂牌、FINAL价格标记及独立撤权journal完整定义见12。


## 6. v0.3补齐的逻辑记录与约束

| 对象 | 字段/约束 | 写责任 |
|---|---|---|
| human_judgment_revision | workspace,slot UUID,previous_revision,subject_kind,完整typed value,effective区间,known/created_at,input_manifest,actor；append-only | analysis；只replace创建，旧修订不变 |
| risk_revision / risk_resolution | target_kind/id,company,risk_code,economic_fact,有效区间,evidence；identity/policy版本,适用release/security manifest | analysis验证目标；strategy消费明确适用集合 |
| decision_slot | kind+自然键唯一，current_decision,override_expiry,generation；revision/decision归属同workspace | analysis；自然键与原子替换见11 §7/8 |
| dimension_registry / effective_config | 固定registry hash,逐维quality/event policies,origin与全部内容hash | scoring；继承发布见11 §9 |
| evaluation_seal / frozen_manifest | 唯一workspace+release+security+session+mode，generation,fence,完整输入/缺口,cutoff watermark,hash,sealed_at/token,application_status | strategy；12 §8独占冻结/CAS/唯一封存 |

risk解除引用确切revision，membership提交另校验risk generation；封存与普通状态原子提交见12。所有修订/manifest保留source ACL继承和同workspace复合引用；DDL与运行约束仍未实现。

## 7. 字段级物理设计候选

[15字段字典与ER](./15-database-dictionary.md)展开本逻辑模型。字段维护入口为design/database-catalog.json，按切片逐步落实；其中link/impact/rubric/risk采用共同judgment_revision根表和类型化逻辑视图，human链可指AUTO旧修订，有效指针仍只有decision_slot。数据库表/视图/约束与事务均尚未创建或验证，不把目录完整度作为M0一次性建表门槛。

## 6. 资料接入与可阅读载荷（编码准备补齐）

2026-10-01依据已确认的文件参考方案补齐；设计主干与11/12评分、自动审核、A/H时点合同不变。字段真源为design/database-catalog.json；解析DTO为[InformationEntry 1.0](../contracts/information-entry.schema.json)，批次输出为[IngestionResult 1.0](../contracts/ingestion-result.schema.json)，示例为[合成资料](../examples/information-intake.json)。以下拥有新增业务语义，Schema负责形状；API不另复制载荷定义。

### 材料、摘要和原文

content_kind为source_document、agent_report、agent_digest。报告文件是一份agent_report，解析条目是一份agent_digest，引用文章实际取得后是单独source_document。summary_text是阅读摘要；reading_metadata固定资料类型、主题、人物/头衔、summary_origin/generator_ref、上游解读、观察点和阅读星级/排名。system_generated摘要必须保留生成版本；上游解读与有效判断分别显示，不写用户research_note，不把阅读星级当公司质量分。

agent_digest通过parent_revision_id+origin_locator定位报告sheet/range，共享父raw_object。文件中的单元格只证明报告原有表述，不能把二手摘要标为发行人原文。content_hash覆盖完整解析载荷、reading_metadata和引用描述，parse_version改变可产生新修订。observed_at由本系统真实取得时点产生，不能回填为报告日期、上游检索时间或源发布时间。

每次item_observation记录ingestion_run_id；同文件导入采用source+上游稳定报告ID（有则用）或文件hash作为报告external_id，条目external_id=报告身份+sheet+条目位置（规范化序列化，parse_version不混入身份）。相同内容不同解析版本建立新revision；重试同批次不重复observation或条目提交。上游报告无稳定ID时，另一天/排版改变作为新材料，事件/事实层再关联，不能用标题或行号覆写旧材料。A→B→A观察合同保持不变，不能用“重复内容”丢掉新的真实观察。

item_source_reference一条对应一个来源描述，包含source_name、可空url、article/list/account/unknown定位类型及原位置。路径猜测不等于原文核验，未确定为unknown。描述随所属item_revision固定；target_revision_id只允许null→已实际取得、可定位正文的同workspace source_document，CAS与现有审计同事务；同一绑定重试返回原结果。错误绑定通过新解析修订更正，不修改旧快照。没有链接或正文时不制造空information_item。目标权限读取时重新校验；目标已绑定也可能无权/撤权，不把ID或来源细节泄漏给不可见用户。报告的权利不自动授予引用来源的权利。

### 资讯时间

published_at仅用于真实可定位瞬时（instant/minute），要求明确来源时区及offset，日期与该时区的民用日一致。published_date保存上游日期，published_precision表达instant/minute/day/part_of_day/unknown；只有日期或“晚间”时published_at为空，保留published_time_raw，不补午夜/整点。分钟精度不宣称秒精度。无法确定IANA时区时保留原文与日期，不能凭电脑时区猜测；访谈“日期”含义不明则precision=unknown、date/at为空，原值保留raw。

资讯列表默认分两组：已知发布日期按发布民用日倒序；同一天可定位瞬时的条目按瞬时倒序，不精确条目按stable item_id排列并标日期精度，不能声称它们先后已确定。未知发布日期放在“发布时间未明确”；可切time_basis=observed按取得瞬时倒序。跨时区精确瞬时换成读者显示时区的日分组，未知时区的仅日期标“来源日期、时区未明确”，不是严格全球先后。排序tuple、snapshot与组边界写入游标；published日期筛选按这个同源分组日，不把未知日期混入“今日”。事件时间线仍遵守§3，不能用这套资讯排序替换事件时间。

### 批次输出与监控说明

ingestion_run.input_manifest_id在运行前冻结输入/版本；解析输出另写input_manifest表kind=ingestion_result，run.result_manifest_id指向它。输出包含上游报告日期/生成时间/窗口、adapter/parse版本、文件/报告修订、成功revision引用、失败条目定位/原因及company_coverage。每次恢复产生新不可变输出清单，实际成功条目回读后决定succeeded/partial/failed；不把后产生的结果塞回输入或覆写旧输出。

company_coverage.reported_result=has_updates/no_material_update/unknown，是上游报告的说明；与运行是否成功分开。候选公司ID未确认为空。窗口声明与实际跨度不符可记warning，不阻止其他有效条目阅读；无重要动态不产生经济事件。部分失败保留checkpoint.holes，成功条目可见，未解决洞不推进完整checkpoint。监控说明先用固定输出DTO，不增加单独coverage表。

阅读解读与来源入口不要求先完成所有全文抓取/影响判断。需要参与评分的证据仍满足已有07/11政策；满足政策可AUTO接受，不追加逐篇人工审批。报价、研报目标价或原Agent解读不直接进入price_bar、财务事实或经营分。一个条目可涉及多个事实，重复材料各自保留，沿用economic_fact/contribution_slot防重复加分。
