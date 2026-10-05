# W-08.4 有效判断与人工覆盖 — 验证证据

- commit: 见本次提交
- 新增迁移 0004_judgment：judgment_slot / judgment_revision

## 交付

- DecisionService：对 accepted 链接按 auto-review 政策门槛（confidence≥0.90）自动生成 accepted impact revision；有效指针指向最新 revision
- 人工覆盖：researcher（analysis.override）提交新值，If-Match-Generation 做 CAS；代不匹配 → 409 保留输入；成功后 generation+1，有效指针切到 HUMAN 值
- API：`POST /api/judgments/auto-run`、`GET /api/judgments`、`POST /api/judgments/{slot_key}/override`

## 预期 vs 实际（pytest 19 passed）

| 场景 | 预期 | 实际 |
|---|---|---|
| 自动判断 | accepted≥4，effective direction=positive | 通过 |
| 人工覆盖 | CAS 成功后 effective 变成 -0.2 | 通过 |
| 陈旧 generation | 409 | 通过 |
| viewer 覆盖 | 403 | 通过 |
