# 当前版本整体评估交接

更新日期：2026-10-06（上海时间）。当前从main实际SHA固定读取；UX18整改处置及最新验证见[实施记录](./UX18-IMPLEMENTATION.md)。以下2026-10-05整理与原实现基线保留历史上下文：实现基线：`90520263304befe18bf5b22217c630d7e243b3cf`，分支 `codex/v0.0.1`。本次仅整理评估入口、文档状态和交接包，不改产品逻辑、不新增真实数据。最终包的精确提交、逐文件SHA256和文件清单以包内 `REVIEW-MANIFEST.json` 为准。

## 先读与当前结论

从[评估提示词](./CURRENT-REVIEW-PROMPT.md)开始；项目管理真源[PROJECT](../PROJECT.md)，业务确认真源[11](../docs/11-templates-automation-and-roles.md)，验收预期[10](../docs/10-acceptance.md)，实际运行/剩余必选[VERIFICATION](../versions/v0.0.1/VERIFICATION.md)。设计基线v0.3与产品版本v0.0.1属于不同层次，不能按编号认定实现进度。

后续用户授权的GitHub-only交接使用[GPT Pro专用入口](./GPT-PRO-UX18-PROMPT.md)及[18修订2](../docs/18-ux-and-copywriting-redesign.md)，从`main`最新代码解析并固定当次SHA，不使用附件或本机截图。本文的实现基线与本地zip说明保留当时上下文；18已获实施授权，UXR-01…12整改见本轮实现记录；旧材料不代表当前状态。

本机原研发提交历史未向GitHub推送；已将干净评审快照与入口修订合并主干，保留已核验main历史和新的安全提交。本文原commit是本机历史标识，不要求远程可读；当前源码/证据均可在main核对。先前评审的处置与未实现边界见[主干交接索引](./PRE-MAIN-DISPOSITION.md)。

当前产品**部分实现与验证**，不是完整交付或生产就绪。用户要求真实研究不使用假数据；原合成研发/测试仍用于隔离验证，不代表实际经营结论。此前8切片报告、设计评审和原型检查均保留历史意义，不能替代当前源码和验收证据。

## 一条实际主路径

真实来源显式采集 → 本地原始响应 → 可读资料/不可变修订 → 公司/证券关联 → 今日概览/公司研究 → 阅读原文并返回原标签 → 有合格依据与权限时录入一项研判 → 保存本地研究预览 → 查看当次固定A/H结果/原文及比较历史 → 分别管理自选。没有证据时停留待评估，不造分。

两家公司为比亚迪（A/H）和格力（A）。目前6份可读资料：2篇公司百科、2份A股日线、2份财务指标；38条日线（30天范围），40条财务指标记录（四类接口×五个期间×两家公司）。财务期间为2023/2024/2025年末、2025/2026中期。正文、价格及原始财务值不放入本次评估源码包；可分享的元数据回读在versions中。

供应商财务指标仅进入`financial_observations`，不代填标准`financials`；单位/币种/合并与归母/普通股/累计与单季、原始CFO/权益/债务/现金/EBITDA等依据不足。当前真实Q/V/策略为UNKNOWN，研究为partial，未正式封存、未改变membership。已有字段描述比较不是完整经营分析。外部模型能力属于确认设计，当前真实流程没有模型外发。

## 评估导航：方案到实现

| 评估对象 | 方案/合同 | 当前实现入口 | 验证入口及限制 |
|---|---|---|---|
| 目标、角色、领域、主流程 | CONTEXT；docs/01、02、11、14 | backend/app/models；frontend/src/app.tsx | docs/10；VERIFICATION；不能仅看原型 |
| 数据/时间/原文/修订 | docs/04、05、12、15、17；design/database-catalog.json；contracts/information-* | intake_service.py、item_history.py、models/intake.py、api/intake.py；alembic/versions | test_w082_intake.py、test_real_data.py、test_research_pipeline.py；REAL-DATA |
| 免费真实来源/输入 | research/real-data-providers.md；REAL-DATA | real_source.py、baostock_source.py、baostock_financial.py、data_mode.py；scripts_public/baostock/financial.py | real-*-readback.json；test_financial_observations.py；非完整财报 |
| 评分、模板、A/H估值 | docs/02、11、12；config/scoring、metric、rubrics、templates、numeric | scoring_service.py、api/scoring.py、api/templates.py、models/runtime.py | test_w085_scoring.py、test_remediation.py；合成计算通过不代表真实Q/V可算 |
| 判断/人工覆盖/政策 | docs/07、11；contracts/review-decision、human-judgment、override-command | decision_service.py、api/judgments.py、models/judgment.py | test_w084_judgment.py、test_remediation.py；真实经营判断尚缺 |
| 策略、状态机、历史 | docs/02、12、13；config/strategy；contracts/evaluation-* | state_machine.py、strategy_service.py、research_pipeline.py、api/strategy.py、api/research.py | test_w086_strategy.py、test_research_pipeline.py；正式FINAL/封存仍未完成 |
| RBAC、事务、异步恢复 | docs/03、05、08、11；config/roles | api/deps.py、security.py、transactions.py、worker_service.py、worker.py | test_w081_rbac_audit.py、test_w087_collab.py、test_remediation.py；本地mock身份 |
| UI、文案、交互 | docs/06、16；prototype/；历史USABILITY评审/处置 | **frontend/src/app.tsx、style.css、client.ts**；生成api-schema.ts；backend/static | BROWSER-RESULTS.json（10-01）；REAL-DATA（10-02）；目标用户签收未运行 |
| 构建/运行/迁移/交付 | docs/03、08、09、13、17；SCOPE/REMEDIATION | tools/vip、local_manage.py、export_openapi.py；frontend/package.json；backend/pyproject.toml | VERIFICATION；正常启动不采集；不要直接执行历史迁移/导入命令 |

表中服务简称均位于`backend/app/services/`，测试位于`backend/tests/`；版本证据均位于`versions/v0.0.1/`。生成客户端与实际输出DTO的覆盖情况也应独立核对。

## UI评估路径

本机入口：http://127.0.0.1:8766/ 。2026-10-05仅只读GET `/api/health`回200，body为`{"status":"ok","db":"ok"}`；这不是本轮业务/UI验收。其他机器访问自身127.0.0.1不会到达此服务，不要为评审直接对外开放端口。

本轮七页为今日概览、公司研究、研究快照、资讯与研判、策略候选池、我的工作台、系统支持；按能力显示，独立system_admin只进入运维支持。公司内四标签默认经营质量与待补依据；业务规则与证据正常可读，技术JSON进入对象旁对话框。建议只读顺序：资料列表→摘要与原文→公司研究的A/H及缺口→已有历史研究→此次来源固定原文→现有判断/规则/变化→我的研究/任务状态。避免点击运行研究、保存覆盖、发布、自选/笔记等写按钮。

检查经营质量与估值区分、未知状态、提供商原始数值、时间意义和来源类型是否易懂；检查模板JSON编辑、诊断JSON、全局409文案等是否支持真实任务。请自行判断，不预设它们一定有缺陷。

`prototype/`是可点击合成设计原型；当前运行UI是React实现，二者不能互相代替。10-01的9组浏览器操作含合成修改场景，10-02新增真实研究/财务表回读，不表示全部七页或完整业务已验收。

明确可本机查看的10-02截图：`local-evidence/real-financial/financial-table.jpg`（财务指标表，窄视口；不在源码包）。它只证明当时该页面像素，不证明今天UI或其他页面。没有浏览器/像素访问的Agent须将视觉评估标为未验证。

## 验证状态与剩余必选

最新2026-10-06：81项后端测试通过（1个已有Starlette兼容警告），TS/构建/OpenAPI生成及真实资料只读浏览器主路径、失败保留、历史比较、390px布局、键盘/焦点和独立运维身份通过。真实研判写路径在原创合成test库端到端验证，未替真实公司录入判断。10-02的真实接入检查仍是历史证据；完整必选未通过。

已知未完成（详见VERIFICATION，不降低原标准）：

- T-43完整固定截止封存、manifest、snapshot、worker/ACL/risk门；真实正式FINAL日历/封存及港股行情。
- T-40公司与挂牌风险的独立作用/解除、完整关联/事件claim审核/冲突传播/财报吸收。
- T-32/34完整历史纠错重放、独立撤权journal及备份实际恢复。
- T-44 Excel适配与T-45…49完整矩阵。
- 三层模板发布绑定/父版本升级、全部财务失败向量/报告义务及非整数衰减黄金向量。
- 完整API DTO、草稿规则AST编辑、角色分配/组合及完整状态页面。
- T-UX-01…04目标用户计时/理解签收、200%缩放/屏幕阅读/真实设备。

## 读取、复现与数据边界

评估包包含已提交设计/合同/配置、源码、迁移、原创合成示例与测试及元数据证据，不含Git历史、凭证、真实正文/行情值/财务原始响应、数据库dump、截图、私人日志、依赖目录或压缩后的UI产物。部分源码固定公共来源/本地端口及demo身份，属于项目配置，不代表可用生产凭证。

本机PG是共享集群的项目专用角色/库，不是物理独立集群。`vip_v0001_local`有真实公开资料，保持只读；`vip_v0001_test`是原创合成夹具。不要因数据库名、loopback或test标签就跳过实际位置/数据分类核验。

默认复现只读代码与现有证据。若之后另获授权验证，常用入口：`./tools/vip test`（会重建隔离test库，运行前核验）、`./tools/vip build-ui`（写构建产物）、OpenAPI导出与TS生成（会改文件）；`verify_real_pipeline.py`会POST持久化研究，**不是只读探针**。迁移/采集/seed/重启均不是评估前置。依赖未配置时报告限制，不索要真实库凭证。

2026-10-05整理时没有发送给其他会话/服务或创建Agent；后续用户已明确授权本轮实施和私有GitHub主干交付，最新处置见UX18-IMPLEMENTATION。代码与项目资料仍按机密边界管理，在已获准环境中使用。

## 历史材料与传递

旧`review/REVIEW-PACK.md`、`FINAL-REVIEW-PASTE.txt`和`PASTE-*`是编码前评审快照，含当时“未实现”叙述；不再用它们作为当前产品整包。历史design/USABILITY/GPT-PRO处置可用于理解来源，但问题是否仍存在需要独立核对当前代码。

当前推荐：将[评估提示词](./CURRENT-REVIEW-PROMPT.md)发给评估Agent，让其读取本项目当前提交；无仓库权限时，在允许处理源码的环境提供本地生成zip。构建：`python3 tools/build_current_review_bundle.py`，只从干净HEAD读取白名单已提交文件，不连接DB/网络；包内manifest固定提交和hash。不要把历史大包追加到当前包造成上下文冲突。
