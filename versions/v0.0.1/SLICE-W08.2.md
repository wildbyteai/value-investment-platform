# W-08.2 资料先可读 — 验证证据

- commit: 见本次提交（codex/v0.0.1）
- 环境: 同 W-08.1；新增迁移 0002_intake

## 交付

- `source_registry` / `information_item` / `item_source_ref` 表；ingestion_run 扩展 manifest/输出列
- `services/intake_service.py`：读取 `examples/information-intake.json`，按 (source, entry_key) 幂等 upsert
- API：`POST /api/intake/synthetic`（data_admin）、`GET /api/intake/items`（时间线：已知日期新→旧在前，未知日期单列最后）、`GET /api/intake/items/{id}`（摘要 + body_access + reference_access）
- 摘要不触发评分/判断；body 默认 not_acquired/no_locator，不虚构原文

## 预期 vs 实际（pytest 11 passed）

| 场景 | 预期 | 实际 |
|---|---|---|
| 导入合成夹具 | 6 条 imported，run=completed | 通过 |
| 时间线排序 | 已知日期在前，未知日期(digest-2)最后 | 通过 |
| 重复导入 | 不重复条目（计数不变） | 通过 |
| 部分失败 | 注入失败 1 条 → run=partial，好条目仍可读 | 通过 |
| 条目详情 | body=not_acquired，2 个来源引用状态正确 | 通过 |
| viewer 导入 | 403 | 通过 |

命令：`cd backend && .venv/bin/python -m pytest tests/ -v`
