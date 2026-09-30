# 价值投资策略管理系统

> 设计基线 v0.3 · 2026-09-30 · A 股与港股 · 用户范围已确认，工程设计待实施验证

从定时采集到公司研究、可解释评分、策略筛选及状态提醒的一套系统。优先建立可信、可恢复、可维护的流程和工程基础；价投规则提供可替换的标准版本，不承诺预测或收益。本仓库当前交付设计与可检查合同，不含可运行产品。

## 独立项目入口

项目已独立于BYTEWATCHER，项目根目录直接管理Git、设计和后续开发。[PROJECT.md](./PROJECT.md)负责阶段与管理入口，[AGENTS.md](./AGENTS.md)负责执行规则；原BW-0051仅保留历史迁移指向。

## 用户路径

今天发生了什么 → 哪家公司受到什么影响 → 依据在哪里 → 公司质量与证券估值发生什么变化 → 是否进入策略区间 → 为什么发生变化 → 人工覆盖与维护规则。

管理端处理数据源、身份映射、人工审查、规则版本、运行故障与审计；业务端专注候选池、公司档案、时间线、评分解释、策略与变化记录；通知后置。两端复用设计系统，不把后台技术字段直接塞给研究人员。

## 文档导航

| 文档 | 用途 |
|---|---|
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
| [13 首个开发切片](./docs/13-first-slice.md) | 可开始实施的合成全流程任务书，尚未开发 |
| [范围变更决策](./docs/adr/0002-v02-confirmed-scope.md) | 用户确认与技术修订，保留旧决策历史 |
| [标准策略](./config/strategy-standard-v1.json) | 人可维护的初始版本；与策略 JSON Schema 对照 |
| [合同目录](./contracts/README.md) | 策略、分析结果、异步事件的机器可检查合同 |
| [迁移后二轮评审](./review/ROUND-2-REVIEW.md) / [二轮请求](./review/ROUND-2-REQUEST.md) | 固定迁移基线复审，提案与已确认合同分开 |
| [GPT Pro 提示词](./review/GPT-PRO-PROMPT.md) | 独立审查和生成改进版的完整指令 |
| [整包评审材料](./review/REVIEW-PACK.md) | 完整单文件上下文，可读 GitHub 或粘贴正文 |
| [开源初步候选](./research/open-source-shortlist.md) / [第二轮核查](./research/second-review.md) | 固定源码核查、候选取舍与边界，尚未集成 |
| [v0.2变更账本](./review/V02-CHANGELOG.md) / [v0.3处置](./review/V03-CHANGELOG.md) | 历史需求映射与二轮五项设计合同完善 |
| [不附文件的使用方式](./review/PASTE-INSTRUCTIONS.md) | 私有 GitHub 直读提示词、完整正文及分段复制入口 |

## 当前授权与状态

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
