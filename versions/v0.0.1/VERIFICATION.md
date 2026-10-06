# v0.0.1 交付修复：运行证据与剩余验收

2026-10-06本次最新：194 passed（仅隔离合成test库，1条已有弃用warning）、UI构建及实际真实API回读通过；诺诚健华23标准事实/4有效指标，ECB22日真实参考FX完成。旧研究/修订hash与7项pending建议保持，未降低必选验收或自动确认建议。仍partial，真实seal=0；详细来源/原件/恢复/幂等与具体阻断见[本次缺口续建](../../review/REAL-GAP-CLOSURE.md)。以下记录保留各历史时点结果。

## 2026-10-06 UX18实施验证（最新）

固定实施基线main c44d0afa8b4453ede35b25ae11edd8d6e6e52695，本次变更见收录本节与test_ux18.py的实施提交（最终SHA以Git提交/main回读为准）。用户已授权落实GPT Pro评审并合并主干。81 passed，1项已有Starlette/httpx警告；TS检查/构建、OpenAPI导出与TS生成通过。14项UX18回归使用本机专用vip_v0001_test原创合成夹具，真实资料库未用于写入验收；无schema迁移。

首次作者录入到评分/研究快照、证据/hash/权限/期间/期限校验、幂等、历史正文与元数据一致、模板注册/重复/完整政策替换/逐字段来源、模拟保留当前规则并绑定所见输入、策略质量门、独立自选取消、运维读取以及经营ready而证券missing时阶段partial通过。解除覆盖先清有效指针，再由worker固定cutoff核验合法建议并产生新AUTO修订；过期建议不恢复。**下面10-01 F02中的“解除回AUTO”仅是当时错误实现/测试结果，已由本轮不恢复旧AUTO的合同一致性修正替代，不能继续当作验收预期。**

真实库只读浏览器核对：公司→原文→返回保留公司/标签，首次研判锚点/证据/期间表单且未选档位禁保存，两历史快照读取比较不重算，读取失败保留原资料，390×844整页无横溢，键盘标签切换、Escape/焦点返回，独立system_admin仅运维支持。未在真实公司上虚构档位/评分、自选或研究快照。200%缩放、真实手机、屏幕阅读器及目标用户计时/理解签收未运行。详细逐项处置、证据与边界见[UX18实施记录](../../review/UX18-IMPLEMENTATION.md)。

本节只证明此次整改路径；以下历史结果与未完成必选保留。原始财务科目、港股行情、FINAL日历/封存、完整风险创建传播、纠错journal/恢复、Excel、三层模板完整绑定及目标用户签收仍未通过，不将81项测试或主干合并等同完整版本验收。


2026-10-01，基线 `30bb51b`，分支 `codex/v0.0.1`。本轮修复由当前Codex会话串行执行，无子Agent，无实际外部模型调用。源码状态与文件hash见 `verification.json`，原8个提交的历史报告不作为本轮通过证明。

## 已运行且通过

| 修复/场景 | 实际命令/环境 | 结果与证据 |
|---|---|---|
| F01 session应用 | `./tools/vip test`，真实本地PG合成测试库 | s0为有效但不符合规则、静默建立OUT基线；首次ENTER=s2，重复s1不计数，s3 last=IN，s4恢复不ENTER；初始有效true静默建立IN，已确认OUT遇缺数据则UNKNOWN；provisional、漏session、迟到结果；golden重放不重复 |
| F02 判断覆盖 | 同上，两个独立PG连接竞争 | 同generation一成功一冲突，旧AUTO不改；HUMAN/audit/outbox原子；同key返回原修订，不同载荷冲突；解除回AUTO；非法档位问题身份/NaN拒绝 |
| F03 worker | 同上与实际独立worker进程 | 双worker仅一个claim；过期租约恢复；旧fence拒绝；丢ACK不重复WorkEffect；已处理幂等；只重试指定工作区任务，researcher403、跨workspace404 |
| F04 财务和评分 | 同上、真实API浏览器回读 | ROE=0.150000000000，CFO/利润=1.303030303030；A PE=12、V=86.666666666667，H PE=14.5、V=70；实际11项rubric与自定义留存、加权覆盖、人工档位及影响改变经营分；同一合成事实转载只贡献一次，HUMAN优先且保留事实身份/证据参数；过去cutoff不能使用刚取得资料；baseline-only贡献=0 |
| F05 页面连续操作 | `node tools/verify_product.cjs`，本机Chrome，127.0.0.1:8766真实API | 9组通过、page_errors=[]；真实原文、A/H/自选、影响−0.2、档位1、笔记、策略模拟/发布、模板预览/发布、viewer只读、4视口与键盘；详见BROWSER-RESULTS.json |
| F06 真实资料 | `cd backend && .venv/bin/python scripts_public.py --enable-wikimedia` | Wikimedia单来源，两家公司、两个近30日文本修订；请求→忽略目录raw→本地库→原文/摘要→正确公司时间线；真实公司无任何合成财务输入 |
| F07 运行与迁移 | `./tools/vip migrate-test`，`./tools/vip migrate`，`./tools/vip dev-down && ./tools/vip dev` | 合成库升级/降级/升级成功；alembic check无遗漏迁移；local库迁移前pg_dump并pg_restore --list检查，旧行保留；仅停止签名匹配的项目PID，等待退出后重启，8765原进程未动 |
| 构建/合同 | `backend/.venv/bin/python tools/export_openapi.py`、`npm --prefix frontend run generate`、`npm --prefix frontend run build` | 同源OpenAPI生成TS类型，TypeScript检查与本地React构建通过，无CDN/外部字体 |

最终后端结果：**41 passed, 1 warning**（Starlette/httpx兼容提示，不影响本轮场景）。测试夹具会重建 `vip_v0001_test`，conftest在导入app前核验目标与非合成来源；迁移演练的重置也只限该库。`vip_v0001_local`保存真实资料，不能用作破坏性测试。

原Makefile进入backend后的路径已修正；本机`make`自身因Xcode许可未接受而无法执行，未修改系统许可。`tools/vip`提供等价且已实际执行的项目入口；没有声称本机make测试通过。

## 真实来源与许可

来源仅为 Wikipedia 英文百科的文本（不下载图片/媒体），许可依据 Wikimedia Terms of Use §7，CC BY-SA 4.0。保留固定修订URL、作者历史入口、许可链接和“摘要截取/格式移除”的改变说明。本地确定性处理，禁止外部模型，导出入口未启用。

| 公司 | 取得的公开修订 | 发布时间意义 | 原始响应SHA256 |
|---|---|---|---|
| 比亚迪股份有限公司（A/H） | https://en.wikipedia.org/w/index.php?oldid=1376152500 | 2026-09-22T11:18:12Z，百科修订时间 | fd0fea3cf4400048fca73f6560bb9e3cbdbacd6d5b649fddba5b658473ca8554 |
| 珠海格力电器股份有限公司（A） | https://en.wikipedia.org/w/index.php?oldid=1374143041 | 2026-09-10T02:48:34Z，百科修订时间 | 43045bf7b4fab23141a15f474a8582f69fb3e2764c7860798aba63a45ade0760 |

这里交付的是真实公司资料阅读，不是取得最新财报或正式行情。摘要不是有效影响判断。真实条目不会进入合成AUTO proposal；真实公司评分/估值仍UNKNOWN。原始正文、备份、私人运行日志和截图留在忽略目录，不入Git。政策撤权后正文/list/timeline禁读。

## 完整版本仍未通过的必选项

**本轮通过的是上表列出的具体路径，不能据此宣布docs/13完整出口或v0.0.1全部完成。** 以下仍是既定必选，不是可选加固；未改变预期：

- T-43完整固定截止封存、逐类manifest、知识序列/一致性snapshot、受限worker封存/ACL/risk generation门；当前持久化evaluation仅为明确标注的合成状态机演练，不是来自真实Q/V的正式收盘评估。simulate确实使用Q/V，但不会应用membership。
- T-40公司风险与H挂牌风险独立作用/解除；关联/事件的完整证据审核、冲突传播和原子财报吸收。当前合成事实key可去重贡献，未实现全部事件/claim合同。
- T-32/34完整历史纠错重放、独立撤权journal与备份恢复门。当前有不可变内容revision/observation、历史知识筛选，但尚未执行独立journal恢复或备份实际恢复。
- T-44完整Excel表头/同义列/合并分段/超链接适配，T-45…49全矩阵；当前仍是直接JSON合成条目导入，非Excel解析器。
- 完整三层发布绑定/父版本升级不热改release、财务报告义务/同口径全部失败向量、12位非整数衰减黄金向量；已覆盖的局部案例见上表，不能外推全通过。
- 同源TS生成类型已交付，但API输出DTO尚未全部固定；完整草稿规则AST编辑、角色分配/多角色组合及全部状态页面仍未完成。
- T-UX-01…04五名目标用户计时/理解签收未运行。9组浏览器是自动化验证；四视口不代替真实手机或屏幕阅读测试。200%缩放、屏幕阅读仍未运行。

以上没有新增采购/权限阻断；剩余工作可以沿现有授权继续按必选验收实施。当前版本状态是“部分实现与验证”，不是全部完成，也不具备生产部署或交易授权。

## 可复现入口

```sh
# 项目根；本机的可用入口
./tools/vip migrate           # local库先备份再升级，不重置
./tools/vip seed-synthetic    # 幂等追加原创演示，真实条目保持
./tools/vip test              # 仅合成测试库，可重建
./tools/vip build-ui
./tools/vip dev               # API+worker；8765占用时选8766
./tools/vip dev-down          # 只停止记录且签名匹配的PID
# 有界真实文本导入需显式启用，正常启动不会采集
./tools/vip public-import
```

本轮留下API/worker运行于127.0.0.1:8766，专属状态在.runtime/processes.json。端口不代表认证就绪：本地mock身份仅用于演示，不能对外开放。

2026-10-01后续真实数据任务：默认真实入口已隔离合成对象，最新回归45 passed（1已有warning），真实API/浏览器回读通过；本轮真实财报/行情并未新增，分析仍UNKNOWN。详细证据、来源权利与剩余依赖见[REAL-DATA](./REAL-DATA.md)，旧41项/9组记录保留为此前工作树结果。

2026-10-02免费源切片：两家公司38条真实BaoStock A股日线已入本机资料库，可阅读固定修订、显示实际价格、核对区间统计并保存研究预览；本轮56 passed、固定修订补充15 passed、构建/迁移/真实API重试/浏览器执行与阅读通过。记录见[REAL-DATA](./REAL-DATA.md)和real-pipeline-readback.json。运行partial；真实财报/股本/经营判断、港股行情、正式日历/FINAL/封存仍缺失。前述完整版本必选未被降低，也没有正式策略应用。

2026-10-02三年范围已获用户授权。新增两家公司40条免费真实财务指标，读原文/报告期/披露日/字段比较及研究v2保存通过；旧研究命令重试保留原v1输入。67 passed（1已有warning）、TS构建、真实回读与浏览器表格/固定原文通过。财务指标不是完整财报：原始科目、单位与范围、报告义务/rubric/正式封存等缺口仍未补齐，Q/V/策略UNKNOWN。证据见REAL-DATA与real-financial-readback.json，前述必选标准未降低。

## 2026-10-06 原始科目/港股适配与正式封存机制

基线abac2a17fbe6bb81af3c4bc960b80b65588c9877，分支codex/real-data-sealing。新增原始科目/港股快照适配及显式内部封存worker；固定截止/提交阶段知识账本/一致性snapshot/完整manifest/租约fence/稳定token/不可变评估与状态变化事务实现。当前最新118项后端检查通过（合成test库，1项已有弃用警告），OpenAPI/TS生成和构建通过；迁移测试升级、降级、再升级通过。详细正常、失败、时点/恢复/权限证据见review/REAL-COMPLETION-PLAN.md与backend/tests/test_sealing.py、test_original_inputs.py。

真实资料库仍0009，未执行本轮schema/来源/正式membership写入。8766只刷新API以匹配新静态产物，已授权原worker同PID保留，未启动正式worker；真实只读浏览器可见策略v5及“正式封存迁移尚未安装；研究预览仍可使用”，原两家公司和缺口页面仍可用。真实来源核查见research/real-completion-sources.md：核实比亚迪官网完整报告入口，未获取完整原始科目；港交所条款限制此类程序化接入，未绕过、未采购/注册。完整真实分析、真实正式封存与完整首slice仍未完成，不能将测试夹具或引用入口计为真实接入完成。

## 2026-10-06 真实库启用与原始财报业务验证（最新）

基线b38dfc7，分支codex/real-source-activation；用户已授权获取/本地写库。0010及artifact实际登记，旧11类记录hash不变；两家8份原报告、85科目入库，原文/单位/列/页PDF核对通过。格力23标准事实/5财务指标、盈利质量与财务韧性真实计算通过；普通股发生期后变动时停止沿用旧股数估值，其他经营维度仍缺。最新固定研究c0f95221-552f-4a27-8fc6-f3d6d5ea3e23重试ID与GET manifest相同；两家原值、三年现金指标、格力全部标准指标独立核算通过。最终144 passed（隔离原创合成test库，1已有warning）、TS/静态构建通过；浏览器检查及细证据见review/REAL-SOURCE-ACTIVATION.md。

正式机制API available=true，但真实seal=0；没有批准日历/FINAL与同日FX，不生成猜测封存或会员状态。比亚迪完整权益工具/普通股/债务匹配、格力最新股数、HK token来源、经营判断仍未齐。财报真实取得不等同全部评分已完成；研究partial，完整首slice未通过。前一节未迁移/未取样表述保留为历史时点，最新状态以本节为准。原始数据仅本机，GitHub材料没有真实值或凭证。

## 2026-10-06 财务续建（最新）

安全基线a3d1a4e后本轮工作树：166 passed（1项已有弃用warning）、前端构建通过；测试仅核验过的本机隔离合成库。比亚迪标准23事实/五指标及两家公司100原值真实独立核算、固定研究POST幂等/GET manifest/原文回读与浏览器两个财务维度通过。EODHD令牌真实鉴权成功但官方70市场无HK；无真实港股价格验收。当前股数/经营研判/日历及FINAL依赖仍缺，真实seal=0、研究partial，不能称首slice完整通过。具体revision、场景、证据及恢复边界见[续建记录](../../review/REAL-FINANCIAL-CONTINUATION.md)。旧144/118/81结果保留为前轮历史。
