# W-08.1 运行基础 — 验证证据

- commit: 见本次提交（codex/v0.0.1）
- 环境: Python 3.12.13 / FastAPI 0.141.1 / SQLAlchemy 2.1.1 / Alembic 1.20 / PostgreSQL 14.23
- 数据库: `postgresql+psycopg2://vip_app@127.0.0.1:5432/vip_v0001_local`（独立角色 vip_app，与其他项目库物理隔离）

## 交付

- FastAPI 应用 `backend/app/main.py`，路由：`/`、`/api/health`、`/api/identities`、`/api/me`、`/api/demo/runs`（POST/GET）、`/api/demo/audit`、`/api/demo/outbox`(+dispatch)
- Alembic 迁移 `alembic/versions/0001_initial.py`：workspace / app_user / membership / audit_log / outbox / ingestion_run
- 种子 `scripts_seed.py`：2 个 workspace（演示组织、隔离测试组织）× 5 角色（viewer/researcher/strategy_manager/data_admin/system_admin）
- 权限矩阵从 `config/roles-standard-v1.json` 加载，角色—权限映射不硬编码第二份

## 预期 vs 实际

| 场景 | 预期 | 实际 |
|---|---|---|
| 健康检查 | db ok | `{"status":"ok","db":"ok"}` 通过 |
| data_admin 创建导入 run | 200，run/audit/outbox 同事务写入 | 通过（pytest + live curl） |
| audit 回读（system_admin） | 能看到 ingestion_run.create | 通过 |
| outbox 回读 + worker dispatch | 未投递可查，dispatch 后消失 | 通过 |
| viewer 创建 run | 403 | 403 |
| viewer 读 audit | 403 | 403 |
| researcher 建源 | 403（缺 source.manage） | 403 |
| 无身份头 | 401 | 401 |

## 测试命令

```
make migrate && make seed
cd backend && .venv/bin/python -m pytest tests/test_w081_rbac_audit.py -v
# 6 passed
```

真实端到端（live uvicorn 127.0.0.1:8765）已人工 curl 复核上述 200/403 行为。
