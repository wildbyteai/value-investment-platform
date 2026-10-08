# 后端分层地图

> 给人看的后端导航。一句话：**资讯 → 公司 → 策略 → 告警**，代码也按这四层放。

| 层 | 菜单 | 包 | 负责 | 主要 API |
|---|---|---|---|---|
| 资讯 | 资讯雷达 | `app/domains/news` | 抓取/导入资讯 → 标准化 → 去重成事件 → 关联公司、关联度、影响分（AI 预判，人确认） | `/api/news/*`（R5，见 ADR 0008） |
| 公司 | 公司档案 | `app/domains/companies` | 公司与证券、财务、关联资讯、经营/财务评分 | `/api/companies/*`、`/api/scoring/*` |
| 策略 | 策略（划击球区） | `app/domains/strategy` | 价值策略门槛、击球区三条件、入池状态 | `/api/strategy/*`、`/api/strike-zone/*` |
| 告警 | 监控告警 | `app/domains/monitoring` | 只盯落进击球区的球，站内通知 + 邮件 | `/api/alerts`、`/api/notifications/*`（R6，见 ADR 0009） |
| 设置 | 后台设置 | `app/api/admin.py`、`app/sources` | 数据源、任务、模型、权限 | `/api/admin/*` |

## 规则

1. 依赖只往上游走：告警可以用策略，策略可以用公司，公司可以用资讯；反过来不行。
2. 服务层只抛 `app.core.errors` 里的领域异常，不 import FastAPI。
3. 服务层不提交事务；请求或任务入口用 `with unit_of_work(db):` 一次提交。
4. 业务数字只放 `config/*.json`；击球区见 `config/strike-zone-v1.json`。
5. 新数据源先在 `app/sources/registry.py` 登记，再写代码。

## 旧模块归属（逐步迁入）

- 资讯：`services/intake_service.py`、`item_history.py`、`issuer_disclosures.py`、`models/intake.py`
- 公司：`models/company.py`、`services/scoring_service.py`、`original_financials.py`、`baostock_financial.py`、`share_capital.py`、`issuer_reports.py`、`hk_market.py`、`judgment_authoring.py`、`decision_service.py`、`reference_research.py`、`research_pipeline.py`
- 策略：`services/strategy_service.py`、`state_machine.py`、`sealing_service.py`、`seal_worker.py`、`models/strategy.py`、`models/sealing.py`
- 通用：`services/transactions.py`（审计 + outbox）、`knowledge_clock.py`、`algorithm_versions.py`、`data_mode.py`

## 运行

- 资讯导入：后台上传每日 Excel（`POST /api/news/import`），或登记 RSS 源后由 cron 执行 `python -m app.jobs news`（建议每天 08:30 北京时间）。
- 资讯采集定时器：后台设置 › 采集定时器 填提示词、选能联网的模型（通义 / 智谱 / Kimi，用厂商自带搜索）和可选 Skill；cron 每 5 分钟执行 `python -m app.jobs collect`，到期的定时器各自执行。见 ADR 0012。
- AI 关联打分：设置环境变量 `VIP_DEEPSEEK_API_KEY`；换模型在 后台设置 › 模型配置。没有密钥时退回规则匹配。
- 告警：cron 执行 `python -m app.jobs alerts`（建议交易时段每 30 分钟 + 收盘后一次）；研究员确认资讯关联时也会立即检查。邮件需配置 `VIP_SMTP_*`，发件人 admin@bytewatcher.xyz；每人在“监控告警 › 通知设置”填写收件邮箱。
