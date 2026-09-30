# 独立项目管理入口

项目：value-investment-platform（价值投资策略管理系统）。项目标识不使用Matter ID。

## 项目归属与阶段

本项目已从BYTEWATCHER事项迁出，独立目录、独立Git仓库、独立执行规则。项目根目录就是Git根目录，不再嵌套repo/。GitHub为wildbyteai/value-investment-platform，保持私有。

当前阶段：v0.3二轮设计完善；已在独立工作区复核F01…05并同步文档、Schema、配置、示例与T-39…43。处置与证据边界见review/V03-CHANGELOG.md；原v0.2评审/probes保持历史记录。GPT Pro独立复审为可选复核，尚未执行，产品尚未实施。本文件定义项目管理状态，已确认业务边界以docs/11为准，验收以docs/10为准。BW-0051仅为历史来源标识，原事项保留迁移指向，不再管理本项目。

## 权威文件与管理方式

| 内容 | 唯一权威位置 |
|---|---|
| 导航与交付说明 | [README](./README.md) |
| 项目执行与边界 | [AGENTS](./AGENTS.md) |
| 已确认业务选择、模板/自动审核/角色 | [11](./docs/11-templates-automation-and-roles.md) |
| 业务需求与设计 | [01](./docs/01-product-requirements.md)、[02](./docs/02-business-design.md) |
| 工程架构、数据、API、UX、AI、运维 | docs/03…08 |
| 实施任务和首个切片 | [09](./docs/09-delivery-plan.md)、[13](./docs/13-first-slice.md) |
| 验收和追踪 | [10](./docs/10-acceptance.md)，R/W/T标识继续使用 |
| 决策与设计变更 | docs/adr/、review/V02-CHANGELOG.md、review/V03-CHANGELOG.md |
| 机器配置与合同 | config/、contracts/；文档引用，不复制数值真源 |
| 评审交接 | [GPT Pro完整提示词](./review/GPT-PRO-PROMPT.md)、review/REVIEW-PACK.md |
| 本机历史与迁移证据 | local-evidence/，忽略Git并持久保留 |

日常工作直接在本项目创建分支、编写设计、执行已授权任务和记录证据，不再创建BYTEWATCHER Matter或依赖其registry/SOURCE_OF_TRUTH。代码开发分支默认codex/前缀，当前文档阶段在main提交；保留完整Git历史与原remote。

每个开发切片引用既有R/W/T和输入manifest，说明正常/失败/权限/恢复预期。设计、已实现与已验证分开记录。依赖或合同变化写ADR/变更账本，不以报告替代代码或验收事实。

项目全过程的优先级遵循[AGENTS“项目管理与设计优先级”](./AGENTS.md#项目管理与设计优先级)：以业务闭环的落地安排工作，按实际影响选择设计与验证，不把全量工程清单或可选完善作为每一步的前置门槛。2026-10-01用户明确此原则适用于整个项目管理过程；当前阶段仍为设计完善。

## 已确认能力与推进顺序

多人五角色RBAC；通用基础/行业/企业定制评分；自动判断符合政策即生效、人工有效覆盖优先；外部模型接入；开发不设固定成本上限；管理与业务端统一体验；通知后置，策略变化先完整记录。A/H基本资料可查，首批50–100家完整监控是试运行范围。

先完成设计评审，再按单独实施授权推进W-08合成全流程，随后单个获许可真实源→多源/检索→真实评分/策略→运行验收。技术大多有成熟方案，阶段划分按依赖和验证安排，不能因技术实现难度删减已确认需求。

## 历史证据与外部动作

原事项README、matter.yaml和各交付/回读文件完整保存在local-evidence/bytewatcher-origin；本机路径与迁移manifest位于local-evidence/migration，不提交GitHub。历史原文不覆写，其旧相对路径与阶段描述按当时commit解释，当前项目内容从Git历史读取。

GitHub授权覆盖本项目新生成设计、合成示例、验证工具和评审材料；真实业务资料、凭证和私人日志不上传。本轮迁移/评审未授权部署、采购、真实采集、真实模型调用、通知或交易。评审报告提出修改时仍区分建议与已采纳合同。
