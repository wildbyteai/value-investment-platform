# W-08.3 公司关联与研究 — 验证证据

- commit: 见本次提交
- 新增迁移 0003_company：company / security / item_company_link / economic_fact

## 交付

- 两家合成公司：合成甲制造（A 股 600001.SH/CNY + 港股 0001.HK/HKD，同公司不同证券）、合成乙制造（600002.SH/CNY）
- 规则关联器：标题包含公司名 → accepted（relevance 0.9/confidence 0.95，满足 auto-review 政策门槛 0.50/0.90）；多匹配 → ambiguous；无匹配 → no_link
- API：`GET /api/companies`、`GET /api/companies/{id}/timeline`（只含 accepted）

## 预期 vs 实际（pytest 15 passed）

| 场景 | 预期 | 实际 |
|---|---|---|
| A/H 双证券 | 同公司两条 security，market CN_A+HK，币种 CNY+HKD | 通过 |
| 关联统计 | accepted≥4，no_link≥2（合成消费/科技），ambiguous=0 | 通过 |
| 公司时间线 | 只含 accepted；乙公司条目不出现在甲时间线 | 通过 |
| 重跑关联 | 不重复 link 行 | 通过 |
