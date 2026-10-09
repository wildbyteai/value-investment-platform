# 后端分层地图

> 给人看的后端导航。一句话：**资讯 → 公司 → 策略 → 告警**，代码也按这四层放。

| 层 | 菜单 | 包 | 负责 | 主要 API |
|---|---|---|---|---|
| 资讯 | 资讯雷达 | `app/domains/news` | 抓取/导入资讯 → 标准化 → 去重成事件 → 关联公司、关联度、影响分（AI 预判，人确认） | `/api/news/*`（R5，见 ADR 0008） |
| 公司 | 公司档案 | `app/domains/companies` | 公司与证券、财务、关联资讯、经营/财务评分 | `/api/companies/*`、`/api/scoring/*` |
| 策略 | 策略（划击球区） | `app/domains/strategy` | 价值策略门槛、击球区三条件、入池状态 | `/api/strategy/*`、`/api/strike-zone/*` |
| 告警 | 监控告警 | `app/domains/monitoring` | 只盯落进击球区的球，站内通知 + 邮件 | `/api/alerts`、`/api/notifications/*`（R6，见 ADR 0009） |
| 账号 | 后台设置 › 账号与角色 | `app/domains/identity` | 用户、工作区、五种固定角色、按权限下发菜单、密码与会话 | `/api/auth/*`、`/api/me`、`/api/admin/users*`、`/api/admin/roles` |
| 设置 | 后台设置 | `app/api/admin.py`、`app/api/collectors.py`、`app/domains/market_data` | 数据源、资讯源、采集定时器、模型、告警发送 | `/api/admin/*` |
| 平台 | 后台设置 › 审计日志 / 后台任务 | `app/domains/platform` | 审计记录 + outbox、后台任务、数据模式、算法版本 | `/api/admin/audit`、`/api/worker/*` |

## 目录

```
backend/app/
  main.py            装配：路由、错误处理、安全中间件、静态前端
  api/               HTTP 层：一个资源一个文件，只做参数校验、权限依赖和调用领域服务
  domains/           业务逻辑，按层分包（见上表）；不 import FastAPI
    news/ companies/ strategy/ monitoring/ identity/ market_data/ platform/
  models/            全部表定义，一个领域一个文件（news.py、monitoring.py、identity.py…）
  core/              与业务无关的基础设施：errors、paging、uow、paths、http_security、secret_guard
  jobs.py scheduler.py worker.py admin_cli.py   命令行入口（cron、定时器、outbox、账号）
```

`app/services/` 与 `app/sources/` 已于 2026-10-09 全部迁入 `app/domains/`，旧路径不再存在；历史文档里的 `services/...` 路径按下表对应。

## 规则

1. 依赖只往上游走：告警可以用策略，策略可以用公司，公司可以用资讯；反过来不行。账号、平台、行情数据源谁都可以用。
2. 领域服务只抛 `app.core.errors` 里的领域异常，不 import FastAPI。
3. 领域服务不提交事务；请求或任务入口用 `with unit_of_work(db):` 一次提交。
4. 业务数字只放 `config/*.json`；击球区见 `config/strike-zone-v1.json`。读仓库里的文件用 `app.core.paths`，不要数 `Path(__file__).parents`。
5. 新数据源先在 `app/domains/market_data/registry.py` 登记，再写代码。
6. 接口规范（路径、错误格式、分页、权限、菜单）见 [23 工程规范](./23-engineering-conventions.md)。

## 旧模块现在在哪

| 原路径 | 现路径 |
|---|---|
| `services/intake_service.py`、`item_history.py`、`issuer_disclosures.py` | `domains/news/` |
| `services/scoring_service.py`、`judgment_authoring.py`、`decision_service.py`、`original_financials.py`、`baostock_financial.py`、`share_capital.py`、`issuer_reports.py`、`reference_research.py`、`research_pipeline.py`、`research_seed.py`、`real_source.py` | `domains/companies/` |
| `services/strategy_service.py`、`state_machine.py`、`sealing_service.py`、`seal_worker.py`、`knowledge_clock.py` | `domains/strategy/` |
| `services/baostock_source.py`、`eodhd_source.py`、`futu_source.py`、`ecb_fx.py`、`hk_market.py`、`sources/registry.py` | `domains/market_data/` |
| `services/transactions.py`、`worker_service.py`、`data_mode.py`、`algorithm_versions.py` | `domains/platform/` |
| `security.py`、`core/sessions.py`、`core/passwords.py` | `domains/identity/permissions.py`、`sessions.py`、`passwords.py` |
| `domains/news/models.py`、`domains/monitoring/models.py` | `models/news.py`、`models/monitoring.py` |

算法版本（`algorithm_versions.py`）按文件名登记指纹，搬目录不改指纹，历史研究与封存哈希不变。

## 运行

- 资讯导入：后台上传每日 Excel（`POST /api/news/import`），或登记 RSS 源后由 cron 执行 `python -m app.jobs news`（建议每天 08:30 北京时间）。
- 资讯采集定时器：后台设置 › 采集定时器 填提示词、选能联网的模型（通义 / 智谱 / Kimi / OpenAI / Claude / 豆包，用厂商自带搜索）和可选 Skill；cron 每 5 分钟执行 `python -m app.jobs collect`，到期的定时器各自执行。见 ADR 0012。
- 模型：后台设置 › 模型配置 登记模型并可直接填写 API Key（`VIP_SECRET_KEY` 加密入库），在“按场景配置模型”里分别指定 资讯采集 / 资讯研判打分 用哪个；场景定义 `config/model-scenes-v1.json`，取用逻辑 `domains/news/model_scenes.py`。见 ADR 0015。没有可用 Key 时资讯关联退回规则匹配。
- 告警：cron 执行 `python -m app.jobs alerts`（建议交易时段每 30 分钟 + 收盘后一次）；研究员确认资讯关联时也会立即检查。邮件需配置 `VIP_SMTP_*`，发件人 admin@bytewatcher.xyz；每人在“监控告警 › 通知设置”填写收件邮箱。
