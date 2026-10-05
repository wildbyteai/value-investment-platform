# W-08.8 UI 全链收口 + 真实源最小接入 + 版本交付

## 交付

- 单页中文研究 UI：`backend/static/index.html`（FastAPI StaticFiles 挂载，无需 npm 构建）
  - 顶部选身份（login）+ workspace → 带 X-Vip 头调真实后端
  - 四个标签：今天有哪些新消息 / 公司受影响与评分（含 A/H 独立估值、UNKNOWN）/ 策略变化（不可变记录、投递 0）/ 我的自选与笔记
- 真实源 adapter：`app/services/real_source.py`，默认禁用
  - 网络经代理可达（example.com 200），但 stooq CN/HK 代码返回 404，未确认获许可的 A+H 完整收盘/股本/币种源
  - 按任务书规则：不把合成价格混入真实评估，真实评分保留缺口并显示 UNKNOWN；启用需显式许可源（VIP_REAL_SOURCE_URL）
- 启动方式见 `Makefile` 与本文件末尾

## 预期 vs 实际

| 检查 | 实际 |
|---|---|
| pytest | 28 passed |
| uvicorn 启动 | Application startup complete |
| GET /api/health | 200 |
| GET /（静态 UI） | 200，返回中文工作台页面 |
| GET /api/identities | 5 users / 2 workspaces |

## 未通过 / 未运行 / 缺口

- 真实行情接入：无已确认获许可的公开 A+H 源，adapter 骨架就绪但未启用（按规则保留 UNKNOWN）
- 通知渠道：v0.0.1 不实现（change_record.delivery_count 始终 0，仅记录）
- Celery/Redis、生产部署、真实交易、远程库：均不在 v0.0.1 范围

## 运行

```bash
cd backend
.venv/bin/alembic upgrade head
.venv/bin/python scripts_seed.py
.venv/bin/python -m pytest tests/ -q
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8765
# 浏览器打开 http://127.0.0.1:8765 ，选身份进入
```
