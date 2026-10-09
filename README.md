# 价值投资策略管理系统

> 设计基线 v0.3 · 本地产品 v0.0.1 部分实现与验证 · A 股与港股 · 完整必选验收未通过

从定时采集到公司研究、可解释评分、策略筛选及状态提醒的一套系统。优先建立可信、可恢复、可维护的流程和工程基础；价投规则提供可替换的标准版本，不承诺预测或收益。本仓库已有本地可运行的v0.0.1研究版本；完整首slice必选验收尚未通过。设计基线仍为v0.3。

## 当前整体评估入口

2026-10-05整理：其他Agent整体评估请先读[当前交接](./review/CURRENT-HANDOFF.md)及[可直接转发的评估提示词](./review/CURRENT-REVIEW-PROMPT.md)，覆盖方案、设计、源码、核心逻辑、实际UI和文案；当前源码包用`python3 tools/build_current_review_bundle.py`从干净提交本地生成，manifest固定revision与逐文件hash，不含真实原始资料、凭证或备份。旧REVIEW-PACK/PASTE材料属于编码前历史快照。

GPT Pro仅能读取GitHub时，使用[UX18设计与评审专用提示词](./review/GPT-PRO-UX18-PROMPT.md)，从`main`最新代码解析并固定SHA；设计与本轮实现为[18重设计修订2](./docs/18-ux-and-copywriting-redesign.md)，逐项处置、检查及限制见[UX18实施记录](./review/UX18-IMPLEMENTATION.md)。不需要附件或本地zip，main已包含当前产品与设计；既有修订见[处置索引](./review/PRE-MAIN-DISPOSITION.md)，不把历史原型当当前产品。

## 当前本地运行与验收

```sh
./tools/vip migrate
./tools/vip build-ui
./tools/vip dev
```

API/React UI/本地worker启动在127.0.0.1，默认8765，占用时使用8766；本轮入口为[本地工作台](http://127.0.0.1:8766)。仅启动API可用`./tools/vip dev-api`；停止用`./tools/vip dev-down`，测试用`./tools/vip test`（只重建合成测试库）。依赖：Python3.12的backend/.venv、npm锁定依赖、本机项目专用PG库；凭证配置在忽略的backend/.env。前端依赖重建用`npm ci --prefix frontend --ignore-scripts`。本机make受Xcode许可限制时用tools/vip，无需修改系统许可。

UX18阶段已运行（2026-10-06）：81项后端测试、TS构建与OpenAPI生成通过；七页研究界面、首次有证据研判、自选取消、历史元数据一致性、策略模拟发布绑定及质量门已实施。真实库只读浏览器核对原文返回、历史比较、失败保留、390px布局、键盘/焦点与独立运维身份通过；未替用户录入真实经营判断。10-02的真实接入/迁移及日线、财务回读保留为历史证据。先前9组页面场景保留为历史验证。实际研究入口仅展示有真实来源的资料和公司；合成操作只允许在隔离test库，旧记录保留。真实评分必须具有可追溯的原文修订，缺失财报和正式行情时显示具体缺口。完整封存/风险/纠错/Excel及目标用户签收仍未完成；详见[验证与缺口](./versions/v0.0.1/VERIFICATION.md)，不能把本地演示当作完整版本或生产就绪。真实文本导入显式运行`./tools/vip public-import`；免费A股日线显式运行`./tools/vip baostock-import --capture`，固定响应重放使用`--snapshot /absolute/path`。免费财务指标显式运行`./tools/vip financial-import --capture`；先只取本地响应使用`--capture --capture-only`，已保存响应重放使用`--snapshot /absolute/path`。正常启动不采集。在工作台“研究运行”可保存当前真实资料的本地研究预览，查看价格、区间统计与缺口。三年财务指标已接入，可看报告期、提供商披露日与原始字段比较；完整财报原始科目/口径、港股行情及正式封存仍未完成，研究运行状态为partial；详见[来源与流程证据](./versions/v0.0.1/REAL-DATA.md)。

最新进展（2026-10-06真实启用）：已授权并完成真实库0010迁移、8份法定报告、两家85项原始科目、格力23标准财务事实及5财务指标的真实入库/复算。后端144 passed，UI构建及实际API固定快照/重试/原文回读通过；详见[真实启用记录](./review/REAL-SOURCE-ACTIVATION.md)。格力两个财务维度可计算，已知股数变动后的旧股数拒绝PE。比亚迪完整口径、当前股数、港股token/同日FX与批准日历/FINAL真实封存仍有缺口，研究partial，真实seal为0。`./tools/vip issuer-import --snapshot /absolute/path --workspace ID`直接核对本机原PDF/hash/页文，默认仅校验，`--write`显式写库；真实原件和原值不入Git。

下面的设计说明保留编码前基线时的上下文；当前产品状态以PROJECT和版本验证为准。

## 独立项目入口

项目已独立于BYTEWATCHER，项目根目录直接管理Git、设计和后续开发。[PROJECT.md](./PROJECT.md)负责阶段与管理入口，[AGENTS.md](./AGENTS.md)负责执行规则；原BW-0051仅保留历史迁移指向。

## 用户路径

当前结论与下一步 → 今天发生了什么 → 哪家公司受到什么影响 → 依据在哪里 → 公司质量与证券估值发生什么变化 → 是否进入策略区间 → 为什么发生变化 → 人工覆盖与维护规则。

管理端处理数据源、身份映射、人工审查、规则版本、运行故障与审计；业务端专注候选池、公司档案、时间线、评分解释、策略与变化记录；通知后置。两端复用设计系统，不把后台技术字段直接塞给研究人员。

## 文档导航

| 文档 | 用途 |
|---|---|
| [00 产品主线（先读）](./docs/00-product-mainline.md) | 四层主线、四个菜单、击球区与告警口径；2026-10-07 用户确认，见 ADR-0005 |
| [领域词汇](./CONTEXT.md) | 公司／证券、讯息／事件、关联／影响、策略状态的统一定义 |
| [01 产品需求](./docs/01-product-requirements.md) | 目标、范围、角色、需求 ID、容量和质量目标 |
| [02 业务设计](./docs/02-business-design.md) | 主流程、评分数学口径、标准策略与状态机 |
| [03 工程架构](./docs/03-architecture.md) | 模块、技术栈、异步管道、部署与扩展取舍 |
| [04 数据设计](./docs/04-data-design.md) | 实体、时间语义、版本、约束与索引 |
| [05 API 与任务合同](./docs/05-api-and-jobs.md) | 接口、错误、并发、事务及重放 |
| [06 UX 与设计系统](./docs/06-ux-and-design-system.md) | 信息架构、关键页面、交互状态、一致性与可用性验收 |
| [07 AI 与检索](./docs/07-ai-and-retrieval.md) | 候选召回、关联、证据、模型评估与混合检索 |
| [08 安全与运维](./docs/08-security-and-operations.md) | 权限、来源边界、运维、可观测性与恢复 |
| [09 交付计划](./docs/09-delivery-plan.md) | 纵向切片、依赖、里程碑、风险、人员与预算假设 |
| [10 验收矩阵](./docs/10-acceptance.md) | 需求—设计—任务—验证追踪与真实通过标准 |
| [11 模板、自动审核与权限](./docs/11-templates-automation-and-roles.md) | 已确认边界、三层继承、判断生效/人工覆盖和RBAC |
| [12 时点、数值与纠错](./docs/12-time-numerics-and-corrections.md) | 财务口径、FINAL、相邻session、恢复与更正 |
| [13 首个开发切片](./docs/13-first-slice.md) | 合成全流程基线任务书；实现进展以版本验证为准 |
| [14 领域与业务流程](./docs/14-domain-and-business-flows.md) | 领域边界、核心流程图与对象/页面连接 |
| [15 字段字典与ER](./docs/15-database-dictionary.md) | 目标字段/ER与事务边界；实际表另核对models及迁移 |
| [16 页面原型与追踪](./docs/16-prototype-and-design-trace.md) | 可点击合成原型、页面与全部需求连接及检查边界 |
| [17 编码前准备与交接](./docs/17-coding-readiness.md) | 编码前固定技术/任务/输入/验收与后置事项；保留设计依据 |
| [19 生产资源与配置清单](./docs/19-production-resources-and-configuration.md) | 现有组件、域名/HTTPS、资源估算、上线缺口及 Java 差异；尚未部署 |
| [22 部署与安全](./docs/22-deployment-and-security.md) | Docker 部署步骤、账号开通、密钥防泄露措施、备份；代码与 CI 已验证，尚未真实部署 |
| [23 工程规范](./docs/23-engineering-conventions.md) | 账号与角色管理、按权限下发菜单、统一错误格式/分页/请求编号、前后端目录约定；已实现并测试，尚未真实部署 |
| [20 需求方图文报告](./docs/20-stakeholder-report-design.md) | [可直接阅读的报告源稿](./reports/stakeholder/business-narrative.md)与[源码维护入口](./reports/stakeholder/README.md)；业务沙盘、角色工作流、合成图示、框架与费用依据；含实拍的本机PDF/Word不入Git |
| [范围变更决策](./docs/adr/0002-v02-confirmed-scope.md) | 用户确认与技术修订，保留旧决策历史 |
| [标准策略](./config/strategy-standard-v1.json) | 人可维护的初始版本；与策略 JSON Schema 对照 |
| [合同目录](./contracts/README.md) | 策略、分析结果、异步事件的机器可检查合同 |
| [迁移后二轮评审](./review/ROUND-2-REVIEW.md) / [二轮请求](./review/ROUND-2-REQUEST.md) | 固定迁移基线复审，提案与已确认合同分开 |
| [GPT Pro 终审提示词](./review/GPT-PRO-PROMPT.md) | 以业务闭环和UI可理解性为主，按实际影响选择必要工程核对 |
| [整包评审材料](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/REVIEW-PACK.md) | 已归档（R2）：编码前快照，仅在归档标签中保留 |
| [开源初步候选](./research/open-source-shortlist.md) / [第二轮核查](./research/second-review.md) | 固定源码核查、候选取舍与边界，尚未集成 |
| [v0.2变更账本](./review/V02-CHANGELOG.md) / [v0.3处置](./review/V03-CHANGELOG.md) | 历史需求映射与二轮五项设计合同完善 |
| [不附文件的使用方式](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/PASTE-INSTRUCTIONS.md) | 已归档（R2）：分段粘贴材料，仅在归档标签中保留 |

## 编码前授权与状态（历史）

本节及后续材料检查说明保留编码前上下文，不表示当前产品尚未实现或真实接入未授权；后续研发、真实源及三年范围授权见PROJECT的日期记录，当前实际结果以版本验证为准。

已确认：A/H、完整流程及技术框架优先、多人角色权限、三层评分模板、自动审核按规则生效/人工覆盖、允许外部模型、开发不设固定预算、通知后置；管理端与业务端、桌面完整操作/手机轻量处理、提交当前个人账号私有GitHub。完整决定见11。用户未要求本阶段部署、真实采集、外部模型调用、真实通知或交易。

技术、评分阈值、容量、SLO 与工期为建议基线，尚未得到实施验收。首批供应商/权利、运行环境、真实接入责任人仍待上线前选择，不阻止设计和合成开发；固定预算与“是否支持多人”不再列为未决。文档中的测试是验收设计；只有 `review/validation-result.json` 记录的本地材料检查是本阶段已运行检查。数据库、API、UI、性能与灾备功能均未实现和未验证。

## 材料验证

```sh
python3 tools/build_review_pack.py
python3 tools/validate_design.py
python3 tools/build_review_pack.py
```

工具只读设计文件、生成评审包与材料检查结果，不连接数据库或外部平台。校验不能替代系统验收。设计修改后重新生成整包；仓库不保存真实平台内容、持仓、密钥或账号资料。不声明开源许可，公开和实施另行决策。

历史v0.2由当前会话按用户已确认范围独立修订，使用Pro共享页可见评审正文与第二轮研究；未获取其完整60文件包。旧v0.1可在Git历史`8b9d9de36d197b1932c4102cc98888d224984085`查看。config文件名中的v1表示第一套标准配置，不表示设计仍为v0.1；当前scoring/analysis配置合同已升级3.0，template/review-decision为2.0，strategy/job保持2.0，指标定义另有v2引用，未曾发布运行产品。

合同新增评分配置、分层模板与审核决策Schema。材料工具包含形状/引用/语义与反例检查，仍不是完整draft-2020-12实现或应用状态机测试。

独立迁移不改变v0.2业务/财务/策略合同；历史交付材料在本机local-evidence中保留，设计历史仍可通过原Git提交读取。迁移决策见[ADR-0003](./docs/adr/0003-independent-project.md)。

当前v0.3在v0.2上补齐二轮F01…05设计合同，见[V03-CHANGELOG](./review/V03-CHANGELOG.md)与[跨模块推演](./review/V03-COUNTEREXAMPLES.md)。11 §7…9/12 §8是新增权威语义；T-39…43列出未来运行验收。设计已写与材料检查已执行分开记录，尚未启动W-08、部署、真实源/模型或通知。GPT Pro是可选独立复核，不作为开发前置。

设计细化入口：[本地交互原型](./prototype/index.html)、[字段目录](./design/database-catalog.json)、[本轮核对记录](./review/DESIGN-DETAIL-REVIEW.md)。原型浏览器交互检查与材料检查分别记录，不冒充产品或目标用户验收。

可理解性收口：[独立评审](./review/USABILITY-REVIEW.md)、[8项处置与证据](./review/USABILITY-FIXES.md)、[终审正文备用](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/FINAL-REVIEW-PASTE.txt)。原型已按评审调整，GPT Pro终审已取得；其三项关键问题已修正，见[终审处置](./review/GPT-PRO-FINAL-DISPOSITION.md)。v0.3设计可收口，产品仍未开发。

编码准备已完成：[收口记录](./review/CODING-READINESS.md)。新增资料解析/批次输出合同、摘要与多来源/时间精度、阅读独立分支及合成状态原型；T-44…49仍为未来产品预期。下一步按17推进授权后的M0/W-08，不再增加全套终审。

### 原始科目与正式封存续建（2026-10-06）

本轮118项后端测试、构建及合成库迁移升降级通过。新增原始科目规范化、许可港股快照适配、内部worker与只读正式结果；真实来源与真实库启用尚未完成，详情见[实施与迁移审查](./review/REAL-COMPLETION-PLAN.md)及[来源核查](./research/real-completion-sources.md)。`./tools/vip original-import --snapshot /absolute/path --kind financials|hk-price --workspace ID --company ID`默认仅校验，`--write`是明确真实入库动作。`./tools/vip seal --prepare-artifacts`和按既有seal-id/批准挂牌日历排期的`seal`命令会写正式机制/状态，默认不随dev启动；真实库0010、artifact登记及正式任务需对应业务批准。不能用仅有参考价或猜测日历生成FINAL或封存时间。

### 财务续建与港股覆盖纠正（2026-10-06最新）

两家公司合计100项原始值，两家公司标准财务五指标和两个财务维度已通过真实独立核算与API/UI回读；166项合成库检查及构建通过。EODHD实际支持市场不含HK，不能据全球套餐文案承诺港股覆盖；令牌有效但真实港股接入未完成。当前股数/经营判断及批准日历/最终收盘/真实封存仍缺证据，研究partial，完整必选未通过。详情见[续建结果与具体依赖](./review/REAL-FINANCIAL-CONTINUATION.md)。显式命令`./tools/vip eodhd-import --capture --workspace ID`先检查覆盖再请求身份/价格，默认仅本机捕获校验，`--write`才入库；正常启动不采集，个人来源不能直接用于多人/商业服务。
