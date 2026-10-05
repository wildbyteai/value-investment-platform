# W-08.7 恢复与协作 — 验证证据

- commit: 见本次提交
- 新增迁移 0007_collab：watchlist / note；复用 outbox claim 幂等

## 交付

- 自选 watchlist（own）、笔记 notes（own）API
- worker outbox claim：已投递行再次 claim 返回 already_dispatched 幂等空操作，不重发

## 预期 vs 实际（pytest 28 passed）

| 场景 | 预期 | 实际 |
|---|---|---|
| 自选/笔记 | 可加、可列、重复自选不报错 | 通过 |
| outbox claim | 首次 claimed；二次 already_dispatched 不重发 | 通过 |
