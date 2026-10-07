# 后端分层地图

> 给人看的后端导航。一句话：**资讯 → 公司 → 策略 → 告警**，代码也按这四层放。

| 层 | 菜单 | 包 | 负责 | 主要 API |
|---|---|---|---|---|
| 资讯 | 资讯雷达 | `app/domains/news` | 抓取/导入资讯 → 标准化 → 去重成事件 → 关联公司、关联度、影响分（AI 预判，人确认） | `/api/news/*`（R5） |
| 公司 | 公司档案 | `app/domains/companies` | 公司与证券、财务、关联资讯、经营/财务评分 | `/api/companies/*`、`/api/scoring/*` |
| 策略 | 策略（划击球区） | `app/domains/strategy` | 价值策略门槛、击球区三条件、入池状态 | `/api/strategy/*`、`/api/strike-zone/*` |
| 告警 | 监控告警 | `app/domains/monitoring` | 只盯落进击球区的球，站内通知 + 邮件 | `/api/alerts/*`（R6） |
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
