# W-08.6 策略到变化 — 验证证据

- commit: 见本次提交
- 新增迁移 0006_strategy：strategy_version / security_state / change_record

## 交付

- 状态机 step()：OUT / ENTER_PENDING / IN / EXIT_PENDING / UNKNOWN；硬风险直接 OUT+RISK
- docs/10 §3 golden 序列（s0–s9）在甲公司 H 证券上一次跑完，不可变 change_record，delivery_count=0（通知后置）
- API：`POST /api/strategy/run-golden`（strategy.publish）、`GET /api/strategy/transitions`

## 预期 vs 实际（pytest 26 passed）

| 场景 | 预期 | 实际 |
|---|---|---|
| golden 序列 | transitions=[ENTER, MISSING_DATA, EXIT, ENTER, RISK]，最终 OUT | 通过 |
| 两次 ENTER | 相邻 session 各一条 | 通过 |
| change_record | 5 条不可变、delivery=0 | 通过 |
| researcher 发布策略 | 403 | 通过 |
