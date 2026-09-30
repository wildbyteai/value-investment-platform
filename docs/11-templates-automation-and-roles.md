# 11 分层评分模板、自动审核与角色权限

设计版本 v0.2，2026-09-30。本文件是模板解析、判断生效和首版角色的权威合同；02、04、05、06 引用它，不另定义继承算法。

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

patch 按稳定 dimension ID 修改，不按数组位置修改。每项可覆盖 weight、完整 baseline 或 disabled；未覆盖的属性继承。baseline替换整个维度规则，不递归拼接半份指标数组。维度禁用同时移除其权重；新增 x_ 开头自定义维度必须同时提供权重和baseline。重复patch、未知指标、未知rubric、总权重不等于1、必需维度被禁用均拒绝发布，不偷偷归一化维度权重。有效子指标的缺失归一化仍按评分配置处理，两者不是同一个规则。

模板可配置指标、权重、rubric、证据和新鲜度要求；数值算法、计量单位、字段注册与规范版本通过受控版本发布变更，不能靠任意Python/JS片段扩展。首个标准行业模板服务一般非金融企业；金融、地产和资源周期的专用模板可接入同一框架，尚未提供适用模板时显示unsupported。这是规则适用范围，不阻止公司研究、讯息关联和事件时间线。

企业定制以(company,template_version)作用于公司经营评分；A/H对应证券共用该公司配置与经营事实，各自估值。可以存在多个研究方案，但当前标准绑定在同一研究组织中只选一个；新增研究方案需要显式profile ID，不能把两个定制分数当同一分数。策略发布固定 scoring_binding_manifest，其中记录每家公司父链和resolved hash。后续模板更新经模拟→差异预览→新绑定/策略release→CONFIG_CHANGE基线，不向旧策略release热替换。

## 3. 模板与分数的人类可读解释

模板编辑页提供三列：继承值、企业覆盖值、最终值。每个覆盖项有理由；可撤销覆盖恢复继承。显示受影响公司、哪些策略会改变、是否减少覆盖度。发布上层新版本时提供显式升级清单和冲突，不能把更新提示变成自动升级。

评分解释返回 dimension→metric/rubric→baseline→event_contribution，并给每个字段 origin_template_ref。两个分数若resolved hash、metric-definition或numeric-policy不同，比较页提示口径不同；可比较共同指标原始值，不能用相同百分制声称等价，也不自动生成未计算的“统一分”。

## 4. 自动审核与人工覆盖

模型只输出proposal。独立DecisionService校验Schema、证据归属/定位、候选身份、数值/单位、适用模板、有效时间和来源状态，之后按auto-review-policy产生append-only review_decision。高影响、基准rubric与硬风险也可自动生效，前提是满足对应政策；不再统一要求先人工审核。

决策状态 accepted/rejected/pending；accepted的生效来源为AUTO或HUMAN。AUTO记录service_principal、policy/version、模型/输入manifest和理由；HUMAN记录actor、理由和证据。旧字段approved统一表示accepted，不代表必须由人批准。硬风险需要明确risk_code和支持事实，自动判定也不能把预测、媒体猜测或无正文标题当已确认事实。

标准政策示例：一般关联r≥0.5、校准c≥0.9；影响判断校准a≥0.9且对应关联已accepted；rubric每项有有效证据与档位锚点、校准置信度≥0.9；硬风险校准c≥0.98且有有效监管/发行人原始披露，事实措辞满足对应risk_code。模型自报数字必须经过校准映射；没有可用校准版本时pending，而非伪造可信程度。这些阈值是可维护初始规则，性能尚未测得，正式启用通过07的评估要求。

人工覆盖按subject_slot(company+economic_fact/criterion+dimension)建立新决策，使用If-Match校验当前有效决策。可改关联、拒绝影响、设置无法确认、撤销硬风险或修订rubric。覆盖可以带valid_until；有效期间后续自动重跑仍可保存建议，但不能覆盖人工决定。期满后触发一次有固定cutoff的重新评估；不能简单恢复一条已过时旧AUTO结论。人工撤销覆盖也生成新记录，并重新应用当前合法输入与政策。

DecisionService、有效判断指针、audit、outbox同事务提交。人工拒绝解除关联时，受其支撑的影响、基准和硬风险失效，触发有界评分与策略重算；不能只改前端标签。一次覆盖可能影响多个证券，预览展示A/H影响。普通小修改一个明确动作完成；只有批量或会改变已发布策略状态的操作需要影响预览，不把所有编辑做成审批流程。

## 5. 首版角色与权限

| 角色ID | 默认权限 | 未默认授予 |
|---|---|---|
| viewer | 查看组织共享公司/证据/评分/策略/变化，维护本人自选与私人笔记 | 修改判断、源或发布规则 |
| researcher | viewer + analysis.override、template.edit、共享研究笔记 | 模板/策略发布、凭证、用户授权 |
| strategy_manager | viewer + template.edit/publish、strategy.edit/simulate/publish/rollback、scoring.binding.publish | 数据源凭证、用户授权 |
| data_admin | viewer + source.manage、job.retry、identity.manage、quality.correct | 模板/策略发布、用户授权 |
| system_admin | user.manage、role.assign、system.configure、model.configure、audit.read、运行状态查看 | 业务覆盖/发布不隐式授予，可明确兼任其他角色 |

RBAC以稳定capability检查，角色只是预置组合；同一用户可兼任。每项写入需同时满足role capability、workspace和对象visibility。组织研究对象默认workspace共享，私人笔记/策略由owner明确共享；无需逐家公司授权。公共市场主数据只读共享，私有判断不跨组织。服务端查询与写入统一检查，前端显示入口/按钮与PermissionNotice，不以按钮隐藏代替授权。

初始管理员通过部署初始化流程授予，不能由公开注册者自选角色。role.assign不能扩大到授权人不具备的可授予范围；最后一名系统管理员不能被无替代地移除。角色撤销后下一请求与后台业务提交重新校验，不依赖长缓存。实现可复用成熟身份服务，无须首版复杂组织树、逐字段ABAC或强制双人审批。

## 6. API与合同映射

GET /scoring-templates；POST /scoring-templates/{id}/drafts；PATCH /template-drafts/{id}；POST /template-drafts/{id}/resolve、simulations、publish；GET /companies/{id}/scoring-config；POST /scoring-bindings/publish。resolve返回完整配置、origin map、hash与错误；publish校验If-Match及预览输入hash。

GET /decisions?company_id&status&actor_kind；POST /decisions/{slot}/overrides；POST /decisions/{slot}/release-override；GET /companies/{id}/notes；POST/PATCH /notes/{id}；GET/PUT /saved-views/{id}。草稿、笔记和视图保存在服务端，具有owner/visibility、revision/ETag；浏览器临时缓存不是唯一保存位置。

GET /admin/roles；PUT /admin/users/{id}/roles。响应包含可授予权限和版本，写入采用If-Match、明确差异、审计；403无权、409并发冲突、422不合法角色组合或模板配置。模板Schema校验形状；父链、权重、scope、引用和人工覆盖优先级由语义校验补充。
