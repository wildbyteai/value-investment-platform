# W-08.5 模板与 A/H 解释 — 验证证据

- commit: 见本次提交
- 无新表；scoring_service 读取 config/scoring-standard-v1.json 与 templates-standard-v1.json

## 交付

- 模板解析 base→industry(manufacturing)→company：甲制造应用公司层 patch（profit_quality 0.35），乙制造只到行业层（0.30）
- 公司质量分：证据不足 → quality_score=null + INSUFFICIENT_EVIDENCE，不臆造 50 分
- 证券估值：pe_ttm 线性映射；A 股(pe12)与 H 股(pe14.5)独立算分且不同；乙公司缺 pe → UNKNOWN_PE

## 预期 vs 实际（pytest 23 passed）

| 场景 | 预期 | 实际 |
|---|---|---|
| 模板差异 | 甲含 company 层且 0.35；乙不含且 0.30 | 通过 |
| 证据不足 | quality_score=null，原因明确 | 通过 |
| A/H 独立估值 | 两证券分值不同、币种独立 | 通过 |
| 缺 pe | valuation_score=null，UNKNOWN_PE | 通过 |
