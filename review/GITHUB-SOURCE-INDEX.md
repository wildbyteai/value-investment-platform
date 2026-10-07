# GitHub主干源码与评审入口

2026-10-07。从仓库 `main` 读取并固定当次提交SHA；本索引可直接在GitHub阅读，不依赖附件或本机访问。

| 内容 | 入口 |
|---|---|
| 产品主线 | [产品主线](../docs/00-product-mainline.md)、[ADR-0005 主线与击球区](../docs/adr/0005-product-mainline-and-strike-zone.md) |
| 当前状态、已验证与缺口 | [PROJECT](../PROJECT.md)、[版本验证](../versions/v0.0.1/VERIFICATION.md) |
| 业务需求与确认合同 | [需求](../docs/01-product-requirements.md)、[业务设计](../docs/02-business-design.md)、[已确认选择](../docs/11-templates-automation-and-roles.md)、[时点与数值](../docs/12-time-numerics-and-corrections.md) |
| 架构与接口/数据设计 | [架构](../docs/03-architecture.md)、[数据](../docs/04-data-design.md)、[接口](../docs/05-api-and-jobs.md)、[字段目录](../design/database-catalog.json)、[合同目录](../contracts/README.md) |
| 页面、文案与实际实现 | [UX18](../docs/18-ux-and-copywriting-redesign.md)、[前端源码](../frontend/src/)、[后端源码](../backend/app/)、[历史整改](./UX18-IMPLEMENTATION.md) |
| 参考研究计算 | [实现及验收](./REFERENCE-RESEARCH-IMPLEMENTATION.md)、[参考计算服务](../backend/app/services/reference_research.py)、[证据](./reference-research-evidence.json) |
| 需求方完整文字报告 | [当前正文](../reports/stakeholder/business-narrative.md)、[合成案例](../reports/stakeholder/case-study.json)、[报告设计](../docs/20-stakeholder-report-design.md)、[框架/费用](../reports/stakeholder/frameworks-and-costs.md) |
| 报告工具与维护 | [生成源码](../tools/build_stakeholder_report.py)、[渲染源码](../tools/render_stakeholder_report.py)、[报告目录](../reports/stakeholder/README.md) |
| 后续检索与生产准备 | [Elasticsearch决策](../docs/adr/0004-elasticsearch-search-platform.md)、[资源配置](../docs/19-production-resources-and-configuration.md)、[费用公开依据](../research/report-component-cost-basis.md) |
| 测试、迁移与运行 | [后端测试](../backend/tests/)、[迁移](../backend/alembic/versions/)、[前端依赖](../frontend/package.json)、[运行入口](../tools/vip) |

当前参考研究已可用，正式封存与完整首slice仍有既有缺口。Elasticsearch只是确定的后续方案。报告合成案例解释目标业务，不能作为真实公司评级或运行验收；本轮不重跑产品测试，257项通过属于4f95778的已有证据。

实际原文、真实输入值、密钥、备份、私人日志、截图像素及包含它们的PDF/Word保留本地；报告源稿、合成图示与制作元数据可读。v0.6制作记录仍待最新逐页检查，不用旧成品检查结果替代。

早期 `codex/v0.0.1` 源码已经过干净快照统一到主干，旧本机历史含已记录的凭证问题，因此不直接合并或推送该历史；保留本机分支。其他开发分支均已纳入main。此次只提交当前干净文件，不删除/改写历史，也不变更真实资料库。

本次文件hash、分支核对、语法/JSON/链接及排除检查见[源码归档证据](./github-source-consolidation-evidence.json)。
