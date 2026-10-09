# 11 分层评分模板、自动审核与角色权限

设计版本 v0.3，2026-09-30。本文件是模板解析、判断生效和首版角色的权威合同；02、04、05、06 引用它，不另定义继承算法。

## 1. 用户已确认的边界

| 决定 | 已确认内容 | 对原 v0.1 的影响 |
|---|---|---|
| D-02A 使用范围 | 从首版支持多人、角色权限，由用户先使用验证；一个私有研究组织可起步 | 不降级为个人工具，不要求先建设公共 SaaS 或部门体系 |
| D-02B 成本 | 开发阶段不设固定预算上限，优先成熟度、效率与维护性 | 成本记录保留；预算门禁不是开发前置条件，实际采购仍是后续接入动作 |
| D-03A 通知 | 通知功能后置；当前实现规划先完成进出区间与风险变化的正确记录和查看 | 首版无需提醒中心、收件人订阅、已读/稍后提醒或任何渠道投递 |
| D-04A 模板 | 通用基础→行业→企业定制，模板由人维护发布 | 企业只覆盖差异，上层升级不悄悄改变已发布配置 |
| D-05A 模型 | 允许外部模型作为正常分析能力，权限先松后紧 | 简单 RBAC 与来源可分析标记；不为首版叠加复杂审批、逐字段 ABAC、强制 MFA 流程 |
| D-07A 判断 | 系统自动给出审核结论，符合配置规则即生效，人工可以覆盖 | 移除“重大影响必须先人工批准”和固定每日人工投入假设；无法确认仍是未知 |
| 范围与体验 | A/H；全市场基本资料可查，首批50–100家公司完整监控；桌面完整操作，手机查看和轻量处理 | 50–100是试运行范围，不是数据模型或产品能力上限 |

用户最后确认“按这版定”。本轮授权是修订并提交设计材料，未授权构建产品、采购、真实采集、调用模型或部署。技术功能以成熟方式可实现为设计前提；分阶段只是依赖和验证顺序，不能以“技术复杂”为由删掉已确认业务能力。

## 2. 模板继承与发布

对象为 ScoringTemplateVersion：template_key、version、level(base/industry/company)、parent_ref、scope、patches。base 固定引用评分配置版本；industry 固定引用 base；company 固定引用 industry。公司必须只有一个生效的行业归属绑定；跨行业公司通过显式企业定制表达，不隐式混合多个父模板。分类变化必须预览、发布新绑定。

父引用包含 key、version 和内容 SHA-256，不使用 latest。发布后的模板不可变；草稿可编辑，ETag防并发覆盖。不允许循环、跳级、跨 workspace 父引用、公司套用不适用行业，或者没有证据口径的新指标。正式运行解析器加载固定父链，校验哈希，按base→industry→company应用patch，生成完整 EffectiveScoringConfig、字段来源和 resolution_hash。

patch 按稳定 dimension ID 修改，不按数组位置修改。每项可覆盖 weight、完整 baseline、完整 quality_policy、完整 event_policy 或 disabled；未覆盖的属性继承。baseline替换整个维度规则，不递归拼接半份指标数组。维度禁用同时移除其权重；新增 x_ 开头自定义维度必须已在冻结registry注册，同时提供权重和baseline，并加载注册默认policy；disabled=true不可混用其他覆盖字段，禁用同时移除权重、baseline和policy。重复patch、未知指标、未知rubric、总权重不等于1、必需维度被禁用均拒绝发布，不偷偷归一化维度权重。有效子指标的缺失归一化仍按评分配置处理，两者不是同一个规则。

模板可配置指标、权重、rubric、证据和新鲜度要求；数值算法、计量单位、字段注册与规范版本通过受控版本发布变更，不能靠任意Python/JS片段扩展。首个标准行业模板服务一般非金融企业；金融、地产和资源周期的专用模板可接入同一框架，尚未提供适用模板时显示unsupported。这是规则适用范围，不阻止公司研究、讯息关联和事件时间线。

企业定制以(company,template_version)作用于公司经营评分；A/H对应证券共用该公司配置与经营事实，各自估值。可以存在多个研究方案，但当前标准绑定在同一研究组织中只选一个；新增研究方案需要显式profile ID，不能把两个定制分数当同一分数。策略发布固定 scoring_binding_manifest，其中记录每家公司父链和resolved hash。后续模板更新经模拟→差异预览→新绑定/策略release→CONFIG_CHANGE基线，不向旧策略release热替换。

## 3. 模板与分数的人类可读解释

模板编辑页提供三列：继承值、企业覆盖值、最终值。每个覆盖项有理由；可撤销覆盖恢复继承。显示受影响公司、哪些策略会改变、是否减少覆盖度。发布上层新版本时提供显式升级清单和冲突，不能把更新提示变成自动升级。

评分解释返回 dimension→metric/rubric→baseline→event_contribution，并给每个字段 origin_template_ref。两个分数若resolved hash、metric-definition或numeric-policy不同，比较页提示口径不同；可比较共同指标原始值，不能用相同百分制声称等价，也不自动生成未计算的“统一分”。

## 4. 自动审核与人工覆盖

模型只输出proposal。独立DecisionService校验Schema、证据归属/定位、候选身份、数值/单位、适用模板、有效时间和来源状态，之后按auto-review-policy产生append-only review_decision。高影响、基准rubric与硬风险也可自动生效，前提是满足对应政策；不再统一要求先人工审核。

决策状态 accepted/rejected/pending；accepted的生效来源为AUTO或HUMAN。AUTO记录service_principal、policy/version、模型/输入manifest和理由；HUMAN记录actor、理由和证据。旧字段approved统一表示accepted，不代表必须由人批准。硬风险需要明确risk_code和支持事实，自动判定也不能把预测、媒体猜测或无正文标题当已确认事实。

标准政策示例：一般关联r≥0.5、校准c≥0.9；影响判断校准a≥0.9且对应关联已accepted；rubric每项有有效证据与档位锚点、校准置信度≥0.9；硬风险校准c≥0.98且有有效监管/发行人原始披露，事实措辞满足对应risk_code。模型自报数字必须经过校准映射；没有可用校准版本时pending，而非伪造可信程度。这些阈值是可维护初始规则，性能尚未测得，正式启用通过07的评估要求。

人工覆盖按服务端分配的opaque UUID slot_id建立新决策（自然键见§7），用一个If-Match slot generation校验并发。服务端从slot读取当前decision，不要求调用方再提交重复的decision ID和generation字段。可改关联、拒绝影响、设置无法确认、撤销硬风险或修订rubric。覆盖命令可以带override_valid_until（决策记录为valid_until）；有效期间后续自动重跑仍可保存建议，但不能覆盖人工决定。期满后触发一次有固定cutoff的重新评估；不能简单恢复一条已过时旧AUTO结论。人工撤销覆盖也生成新记录，并重新应用当前合法输入与政策。

DecisionService、有效判断指针、audit、outbox同事务提交。人工拒绝解除关联时，受其支撑的影响、基准和硬风险失效，触发有界评分与策略重算；不能只改前端标签。一次覆盖可能影响多个证券，提交后直接展示A/H影响和重算状态。普通小修改一个明确动作完成；只有批量修改、模板/策略发布或主数据合并等本来需要比较影响的操作才要求预览，不把单项人工编辑做成审批流程。

## 5. 首版角色与权限

| 角色ID | 默认权限 | 未默认授予 |
|---|---|---|
| viewer | 查看组织共享公司/证据/评分/策略/变化，维护本人自选与私人笔记 | 修改判断、源或发布规则 |
| researcher | viewer + analysis.override、template.edit、共享研究笔记 | 模板/策略发布、凭证、用户授权 |
| strategy_manager | viewer + template.edit/publish、strategy.edit/simulate/publish/rollback、scoring.binding.publish | 数据源凭证、用户授权 |
| data_admin | viewer + source.manage、job.retry、identity.manage、quality.correct | 模板/策略发布、用户授权 |
| system_admin | 全权限：全部权限（user.manage、role.assign、system.configure、model.configure、audit.read、运行状态查看，以及上面所有业务权限） | 无（用户 2026-10-09 决定“管理员是全权限”，取代原“业务覆盖/发布不隐式授予”，见 ADR 0014） |

RBAC以稳定capability检查，角色只是预置组合；同一用户可兼任。每项写入需同时满足role capability、workspace和对象visibility。组织研究对象默认workspace共享，私人笔记/策略由owner明确共享；无需逐家公司授权。公共市场主数据只读共享，私有判断不跨组织。服务端查询与写入统一检查，前端显示入口/按钮与PermissionNotice，不以按钮隐藏代替授权。

初始管理员通过部署初始化流程授予，不能由公开注册者自选角色。role.assign不能扩大到授权人不具备的可授予范围；最后一名系统管理员不能被无替代地移除。角色撤销后下一请求与后台业务提交重新校验，不依赖长缓存。实现可复用成熟身份服务，无须首版复杂组织树、逐字段ABAC或强制双人审批。

## 6. API与合同映射

GET /scoring-templates；POST /scoring-templates/{id}/drafts；PATCH /template-drafts/{id}；POST /template-drafts/{id}/resolve、simulations、publish；GET /companies/{id}/scoring-config；POST /scoring-bindings/publish。resolve返回完整配置、origin map、hash与错误；publish校验If-Match及预览输入hash。

GET /decisions?company_id&status&actor_kind；POST /decisions/{slot}/overrides；POST /decisions/{slot}/release-override；GET /companies/{id}/notes；POST/PATCH /notes/{id}；GET/PUT /saved-views/{id}。草稿、笔记和视图保存在服务端，具有owner/visibility、revision/ETag；浏览器临时缓存不是唯一保存位置。

GET /admin/roles；PUT /admin/users/{id}/roles。响应包含可授予权限和版本，写入采用If-Match、明确差异、审计；403无权、409并发冲突、422不合法角色组合或模板配置。模板Schema校验形状；父链、权重、scope、引用和人工覆盖优先级由语义校验补充。


## 7. 类型化人工修改与不可变修订（F01）

合同为[OverrideCommand](../contracts/override-command.schema.json)、[HumanJudgmentRevision](../contracts/human-judgment.schema.json)和review-decision。命令不携带actor、known_at或新decision ID：这些由认证上下文与服务端clock生成。action=accept/reject/pending引用确切subject_revision_id；replace携带完整replacement，不同时引用subject_revision_id；release引用当前人工subject_revision_id。字段不是reason文本中的隐式JSON。

slot自然键：link=(workspace,item/event身份,company,relation_type)；impact=(workspace,company,economic_fact,dimension)；rubric=(workspace,company,rubric,criterion,period)；risk=(workspace,target_kind,target_id,risk_code,economic_fact)。subject_revision归属和旧值必须匹配slot。replace不能改身份键、扩大发生事实、风险目标或rubric期间；这些属于另建判断的有权流程，不冒充值修改。impact完整记录signed_impact、confidence、半衰期、economic_fact、event_time、业务有效期、证据与理由；rubric记录grade、period及对应锚点。link/risk同样有完整类型分支。

If-Match必须带当前slot generation；缺头428，过期409。服务端从当前slot解析decision，避免客户端重复提交并发字段。Idempotency-Key按05 §1绑定。analysis.override与workspace/visibility/证据访问权在提交时再检查，viewer为403；不可见对象为404。有效期半开；known_at不早于所有输入observed_at和本次提交时间，不能用effective_from回填系统历史。override_valid_until不晚于replacement的valid_until；到期即停用，缺新合法判断则pending/UNKNOWN。人工修改也不能绕过证据定位、数值、registry、来源权利和身份语义校验。

同一事务锁slot并用If-Match CAS：校验→replace创建不可变human_judgment_revision(previous_revision_id)→创建HUMAN accepted决策→更新有效slot指针/generation→audit/outbox。accept/reject/pending不虚构新值；reject/pending仍成为人工有效覆盖，抑制后续AUTO。release生成append-only解除记录、清人工锁、移除旧有效指针并排入固定cutoff重评；过渡期无可用判断，不恢复过期AUTO。事务失败全部回滚；同幂等重试返回原201/结果而非新修订。

业务读视图按当前slot generation校验；依赖重算未完成时显示pending_review/UNKNOWN，不沿用被拒或替换的贡献。封存历史不覆写；当前A/H经营评分均重新计算，各证券估值独立；影响封存历史且属于原错误时走12 §4纠错，普通新人工判断仅从known_at生效。AUTO保存新建议但有效HUMAN覆盖仍优先。

[两项完整例子](../examples/v03-human-replacements.json)列出+0.8→−0.2、grade3→1的请求头/新修订/决策/预期表写入链；它们是设计结果，不是数据库回读。同一slot改变值而非旧行UPDATE，409必须保留输入。拒绝risk表示解除该确切风险判断；release表示解除人工覆盖，可能重新接受合法风险，二者按钮不可混称“撤销风险”。

## 8. 硬风险目标与传播（F02）

risk proposal必须包含company_id、target_kind(company/security/listing)、target_id、risk_code、effective_from、valid_until和证据。分析输入manifest提供受限company→security→listing候选及有效身份版本；DecisionService检查target位于本输入候选、上下级一致、证据真正支持该作用范围。[risk-target-policy](../config/risk-target-policy-v1.json)规定每个risk_code允许的目标类型，政策版本固定到决策及风险resolution manifest；delisting_decision只接受listing目标，不能根据来源市场猜目标。

公司级风险传播到release中该公司的全部适用证券；security级只作用那只证券；listing级只匹配该release冻结primary_listing_id的证券。首版非primary listing风险仍记录，但不传播到其他挂牌。传播不沿母子关系自动扩散；需要本实体独立证据和判断。resolution固定目标身份版本、policy/hash、风险修订和适用release/security列表，投影不是传播权威。

strategy消费有效风险集合；任意一个适用accepted风险仍在半开有效期即硬风险OUT。撤销使用确切slot+revision和generation，不按risk_code全公司清除。新风险generation提升同事务落审计/outbox；membership提交校验当前风险generation，旧普通评估或解除任务不得把风险OUT覆盖为IN。撤销最后风险后保留last_confirmed=OUT，清pending，普通规则重新两session确认，不即时ENTER；若仍有公司级违约则继续OUT。实时风险独立于收盘封存，按实际known_at生效。

[H挂牌退市与公司违约例子](../examples/v03-risk-targets.json)：仅H退市→H OUT/RISK，A不因该风险变化；公司违约→A/H各自产生适用RISK；撤销H风险不解除公司违约。此处是预期，实际事务/传播尚未运行。

## 9. 质量与自定义维度解析（F03/F04）

[dimension registry](../config/dimensions-standard-v1.json)由人发布版本，定义稳定ID、适用行业、允许baseline方法及默认quality/event policy。base配置以path+SHA固定registry；父链中不能热换registry，注册扩展通过新base版本及绑定升级。registry注册不等于启用该维度，启用需模板weight+baseline且总权重仍为1。现有必需维度不能被禁用；未知、不适用、缺baseline或rubric引用的维度拒绝发布。

quality_policy完整替换继承值，含evidence_requirement与freshness。accessible_original要求可定位获许可原文；issuer_or_regulator_original进一步要求发行人/监管正文。age_days用于rubric，按as_of−判断effective_from计龄，修订created_at不能刷新年龄；上限与valid_until同时检查，到期边界t≥期限为stale。report_obligation用于财务指标，仍按12 §1所需期间检查，不给三年历史套180天。rubric锚点定义“证据支持哪一档”，quality policy定义“证据类别/时效可否用”，二者均须满足；AUTO policy负责校准接受门，不代替质量门。

先registry默认→base→industry→company，记录每个policy字段的origin；整个policy替换但未覆盖则继承。策略quality_gates再加限制，不让模板绕过必需维度、覆盖度或策略180日rubric上限。age_days有效最大龄期=min(模板龄期,策略baseline_max_age_days)；财务始终按义务。对同一治理输入age=120日，模板180有效，模板90 stale；若该维度为策略必需，后者评估UNKNOWN。严格正文要求不满足即missing/pending_review，不能仅藏证据链接仍给分。

event_policy为enabled=false（baseline-only，无半衰期）或enabled=true+half_life_days。标准五维半衰期由scoring配置的兼容映射与dimension_policies保持一致；解析后event_policy为计算真源，同步生成映射，不容许两个可编辑值冲突。baseline-only拒绝该维度影响，不造零值影响。分析proposal维度从固定枚举扩为受限ID，服务端用解析manifest白名单验证enabled/适用性/半衰期；模型不能任意注册字段或改H。既有同事实去重、cap和Decimal顺序不变，前端不计算策略。

[自定义模板例子](../examples/v03-template-custom.json)启用x_customer_retention、90日/发行人正文与事件H=90；配套[合成rubric](../config/rubrics-synthetic-v03.json)不是生产规则。只在该公司解析方案加载该catalog，catalog内容hash纳入resolved manifest；旧release不变。规则发布固定父链、registry、rubric/metric/numeric/policy内容hash、完整解析值及origin，不能仅冻结path或可变key。模板UI显示“接受事件/仅基准”、证据要求/龄期和最终来源；policy变更同样模拟→预览→新绑定/release。
