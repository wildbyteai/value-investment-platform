# GPT Pro：当前产品UX设计完善与整体评审（只读GitHub）

日期：2026-10-06，实施后主干交接版。此入口承接docs/18修订2及当前产品整体交接，不使用附件、压缩包、本机路径或本地浏览器。下方完整提示词可直接发给GPT Pro。

## 完整提示词

请作为产品设计与投资研究业务评审者，参与完善本项目UI、中文文案、交互设计，并核对方案→设计→实际实现→核心逻辑的一致性。先给设计与评审结果，暂不实施、不写仓库。

你的材料只能从GitHub读取：私有仓库 https://github.com/wildbyteai/value-investment-platform ，**分支 `main`**。此前修订与当前源码已合并主干，先解析main当前完整commit SHA，记录并将后续所有文件读取固定到该SHA。如果用户另指定完整SHA，以它为准；不要混读不同提交。主干包含当前源码与设计的干净快照，不含早期本地研发提交历史；文档中的原实现commit仅是本机证据来源标识，不要求你能读取那些提交。

若你没有这个私有仓库的读取权限，请明确停止文件评审，指出无法访问；不要索要凭证、要求公开仓库、要求附件或假装已看过材料。GitHub链接不自动赋予访问权限。

### 先读这些GitHub文件

以下链接帮助定位，实际读取时用解析到的commit SHA替换main部分。

1. [PROJECT](https://github.com/wildbyteai/value-investment-platform/blob/main/PROJECT.md)、[README](https://github.com/wildbyteai/value-investment-platform/blob/main/README.md)、[AGENTS](https://github.com/wildbyteai/value-investment-platform/blob/main/AGENTS.md)：当前阶段、范围与规则。
2. [18 UX/文案重设计修订2](https://github.com/wildbyteai/value-investment-platform/blob/main/docs/18-ux-and-copywriting-redesign.md)：已评审实施的设计方案，重点读术语字典、七页流程、依赖和UX18验收。另读[既有评审处置索引](https://github.com/wildbyteai/value-investment-platform/blob/main/review/PRE-MAIN-DISPOSITION.md)，核对已修订与未实现的区别。
3. [当前交接](https://github.com/wildbyteai/value-investment-platform/blob/main/review/CURRENT-HANDOFF.md)、[版本验证与缺口](https://github.com/wildbyteai/value-investment-platform/blob/main/versions/v0.0.1/VERIFICATION.md)、[真实数据证据](https://github.com/wildbyteai/value-investment-platform/blob/main/versions/v0.0.1/REAL-DATA.md)：当前真实主路径、历史检查和未完成能力。不要执行交接中的本机命令。
4. 实际UI源码：[app.tsx](https://github.com/wildbyteai/value-investment-platform/blob/main/frontend/src/app.tsx)、[style.css](https://github.com/wildbyteai/value-investment-platform/blob/main/frontend/src/style.css)、[client.ts](https://github.com/wildbyteai/value-investment-platform/blob/main/frontend/src/client.ts)，以及拆分的ui.tsx、judgments.tsx、template.tsx。这是当前产品；`prototype/`只是历史合成设计原型。
5. 业务依据：`docs/01-product-requirements.md`、`02-business-design.md`、`06-ux-and-design-system.md`、`11-templates-automation-and-roles.md`、`12-time-numerics-and-corrections.md`、`10-acceptance.md`、`13-first-slice.md`。字段/API问题按需读04/05/15/17、design/database-catalog.json及contracts/openapi-v0001.json。
6. 核心逻辑与接口：`backend/app/services/scoring_service.py`、`strategy_service.py`、`state_machine.py`、`decision_service.py`、`research_pipeline.py`、`data_mode.py`、`baostock_financial.py`；`backend/app/api/collab.py`、`judgments.py`、`templates.py`、`strategy.py`、`research.py`、`intake.py`及对应models/tests。另读judgment_authoring.py及test_ux18.py，并按review/UX18-IMPLEMENTATION.md核对UXR-01…12实际处置；不沿用旧基线缺口推定现状。
7. 数字/政策真源：`config/scoring-standard-v1.json`、`templates-standard-v1.json`、`rubrics-standard-v1.json`、`metric-definitions-v2.json`、`strategy-standard-v1.json`、`roles-standard-v1.json`、`numeric-policy-v1.json`；必要时读其余Schema、config和原验收矩阵，不需要先读旧大包。

`review/REVIEW-PACK.md`、`GPT-PRO-PROMPT.md`及PASTE系列是编码前历史快照，不能作为本轮当前状态。GitHub中`review/design-detail/*.png`是历史设计原型截图，不是当前React运行UI；只能据实际可读的GitHub图片评价该原型。当前真实UI截图留在本机且不作为你的输入。你没有实际当前像素/浏览器时，明确“本轮仅基于源码/文案/设计评估，当前视觉与实际操作未验证”，不要要求附件或打开127.0.0.1。

### 固定上下文与不能混淆的边界

用户要真实源头数据，先跑通可用研究闭环。设计基线v0.3；本地产品v0.0.1部分实现，完整必选验收未通过。当前已有两家公司真实百科、38条A股日线、40条供应商财务指标、可读固定修订和可保存研究预览；首次有证据研判录入路径已实现并以原创夹具验证，未替真实公司填写判断；完整原始财务科目/口径、港股/正式FINAL/封存仍缺。Q/V/策略未知、运行partial，不是完整投资分析；81 passed是2026-10-06实施检查记录，不能说你亲自重新运行通过；67 passed保留为10-02历史。

18修订2已经用户实施授权，最新逐项处置与验证见review/UX18-IMPLEMENTATION.md；文档本身不能替代代码与完整版本验收。保留多人角色、三层模板、人工有效覆盖、模型proposal与DecisionService区分、A/H独立估值、时点/截止/不可变历史、通知后置、不交易。未知≠明确不符合；供应商比率≠完整财报；n/N≠加权coverage；研究预览≠正式封存；模拟满足≠正式入选。权重/锚点/指标从发布版本与config取，不用UI设计重新发明公式或固定数值。

修订1设计已纠正（本轮实现须从源码核对）：缺数误写“不满足准入”、错误五维权重、“三年平均ROE”、统一五档评级/无符号影响、写死报价/日期/条数、暗示调仓结算，以及无后端接口的按钮。请核对处置是否充分，不把旧问题直接当当前设计缺陷。

### 请参与设计，而不只列问题

从普通研究员的主线出发：今天看什么→公司怎样→哪份原文支持→缺什么依据/怎样补→如何保存本次研究→每只A/H证券为何待评估或符合→如何关注与维护。请用日常中文复述并完善18，按实际业务影响挑选最小充分改法。

- 给出今日概览和公司页的建议首屏结构、四标签/抽屉内容、业务与支持导航分层；关键操作有明确入口，进阶能力不因简化而丢失。
- 对七页逐一给简洁信息架构/主操作/空与缺数状态；重点完善首次真实研判、证据选择、criteria与period、正负影响、并发/权限失败后的恢复。
- 给可直接采用的文案：页标题、结论、按钮、未知/不通过/未正式评估、来源/价格/口径/历史状态、发布/冲突/无权提示。避免新的“严格保护”“准入守护”等口号替代具体原因。
- 查核心逻辑与界面承诺是否对应：模板动态权重/来源、不偷偷归一化、策略草稿真实基准、权限、首次研判、取消关注、评分差异及历史比较依赖。区分现有接口可做、需补后端、需用户改变合同三类。
- 保持数据真实性与权限，但不要把可选框架、全部未来极端情况、采购或更多评审轮次变成当前闭环前置；不把“数据缺口仍存在”当理由忽略UI改善。

### 输出格式

1. 整体结论：18是否可作为下一阶段设计依据，需先修什么；分别判断设计、现有产品、完整验收和生产就绪。列实际读取的revision/文件及未验证项。
2. 一条完善后的主用户路径，以及七页建议表（首屏信息、主要动作、缺数/空/失败状态、实现依赖）。无需重写全套架构。
3. 重点问题表：稳定ID、严重性、具体文件/行号/文字、误读或失败场景、业务后果、最小修改、可检查预期；标明已知缺口、确定问题、待验证或个人偏好。
4. 文案修改表与18局部设计修订建议，可给精简线框或Mermaid；没有像素证据不宣称视觉验证。
5. 下一步最小端到端实施顺序，对齐18的A/B/C和UX18-D/验收ID、既有R/W/T；说明各片用户获得什么、正常/缺数/权限/冲突/恢复预期与数据/接口依赖。
6. 最多两个真正需要用户决定的业务分歧，其余给合理默认建议。涉及公式、阈值、状态、权限或真实数据范围变化，单列影响及理由，不自行视为已批准。

请只返回设计与评审结果，不操作数据库、代码、GitHub写入、真实源、外部模型、部署、通知或交易，不新增审批流程，不要求本机或附件访问。
