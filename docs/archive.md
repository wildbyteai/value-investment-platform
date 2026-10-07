# 主干归档说明（R2 仓库瘦身）

2026-10-07，R2 把编码前评审包与旧版报告移出主干，**不改写 Git 历史**。所有文件原样保留在标签 [`archive/r2-pre-slimming`](https://github.com/wildbyteai/value-investment-platform/tree/archive/r2-pre-slimming)（即 R2 之前的 main）。主干中指向它们的链接已改为该标签地址。

| 移出内容 | 原因 |
| --- | --- |
| `review/REVIEW-PACK.md`、`review/PASTE-ALL.txt`、`review/PASTE-PART-01…41.txt`、`review/PASTE-INSTRUCTIONS.md`、`review/FINAL-REVIEW-PASTE.txt`、`tools/build_review_pack.py` | v0.3 编码前给 GPT Pro 手工粘贴的整包快照及其生成器，约 4MB，已被 `review/CURRENT-HANDOFF.md` 与 `tools/build_current_review_bundle.py` 取代 |
| `review/design-detail/*.png` | 旧原型截图（约 3MB），由 `tools/verify_prototype.cjs`、`tools/verify_intake_prototype.cjs` 本机重新生成，现已加入 `.gitignore`；同目录的检查 JSON 保留 |
| `reports/stakeholder/` 下 0.2–0.5 的源稿、方案、`build-v0.3/4/5.py`、`render-v0.5.py`、制作证据、`case-study-v0.4.json`，以及 `figures/v0.4`、`figures/v0.5`、`figures/F-*`、`figures/S-*-placeholder` | 历史版本快照与重复/废弃图示；当前入口为 `tools/build_stakeholder_report.py` + `business-narrative.md` + `figures/v0.6` |

暂不移出：`backend/static`（后端直接托管的界面构建产物）。移出前需要在 CI 或启动流程中自动构建前端，留到 R4 前端重建时一起处理。

找回某个文件：`git show archive/r2-pre-slimming:<路径>`，或在 GitHub 切换到该标签浏览。
