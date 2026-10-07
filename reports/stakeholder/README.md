# 需求方图文报告

报告版本0.6，2026-10-07。成果：PDF审阅版（本机成品，不入Git）与可编辑Word（本机成品，不入Git）。页数以最新制作证据为准，管理层摘要、贯穿数字沙盘、八时点状态与三类角色工作流，6张信息图；附件保留14项框架/平台及6项数据服务。

[业务叙述稿](./business-narrative.md)是正文唯一维护入口。[案例数据](./case-study.json)标记合成，算术读取现有评分/策略配置。[方案](../../docs/20-stakeholder-report-design.md)、[框架费用](./frameworks-and-costs.md)、[公开依据](../../research/report-component-cost-basis.md)供核对。组件附件保持框架/平台层级，底层库、SDK和开发工具仅留内部components-and-costs.md。

附件D已补六张本机开发版窄屏实拍及操作说明，保留六张业务图；系统支持页及生产验收画面以紧凑待补说明管理。完整报价、正式结果和签收按进度补充，当前阶段集中于正文第8节。

在项目根目录本地制作：

```sh
/Users/kyle/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B tools/build_stakeholder_report.py
/Users/kyle/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -B tools/render_stakeholder_report.py
```

渲染输出为tmp/stakeholder-report/render-v0.6。重建将[制作证据](../../review/stakeholder-report-build-evidence.json)重置为待检查；须按最新PDF页数逐页看PNG，并记录算术、语义、来源hash及成品hash。旧渲染多余页不能代表当前页数，文档检查不替代产品验收。

0.3成品、正文、方案和制作证据均保留；build-v0.3.py是历史代码快照，不是当前入口。素材、费用或进展变化时同步维护正文、图注及来源。当前只完成本机报告，没有部署、采购或发送需求方。

0.5加入投资视角、事件因子解释、技术自主权及透明预算口径；沙盘的0.8为人工接受的影响置信假设。实际截图只说明开发界面，不代表完整功能或生产验收；任意历史反事实演练不称已交付。0.4成品及维护快照保留，新制作日期2026-10-07，公开价目核查日期仍为2026-10-06。

## GitHub源码归档

GitHub保留报告Markdown源稿、合成案例JSON、生成/渲染Python脚本、合成信息图和制作元数据。实际截图像素及包含它们的PDF/Word留在本机忽略目录；截图元数据仅用于追溯，不表示已取得对外分发许可。GitHub评审直接阅读business-narrative.md和方案/费用文件即可，不依赖附件。

生成器为本机制作工具：当前版本需要Pillow、python-docx、中文字体、截图清单及清单指向的本机像素；渲染另需要本机文档运行时和LibreOffice。不能把克隆仓库后缺少这些本机依赖当作产品运行依赖。历史build-v*.py和源稿/证据是当时快照，不是当前入口。

本次归档只检查源码语法、JSON、合成图示/当前链接与排除边界，不重新生成成品、不覆盖已有制作证据。当前v0.6制作证据仍标awaiting_render_and_visual_inspection；旧版本的逐页检查不代表最新成品已完成检查。
