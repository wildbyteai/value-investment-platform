# UX18 实施与评审处置

2026-10-06，用户明确授权全部落实 GPT Pro 评审与18设计，最终合并主干。
基线 main c44d0afa8b4453ede35b25ae11edd8d6e6e52695；评审来源 https://chatgpt.com/s/t_6ac432e21fd48191859d3cca418df2ad 。

范围：UXR-01…12、UX18-01…12。依据11模板/判断/质量合同、12时点/数值、18体验方案；不改变FINAL估值门或researcher策略模拟权限。实现首次真实定性判断、历史一致性、策略模拟发布绑定、质量门、解除覆盖等待重评、自选闭环、公司四标签与七页导航、历史比较及对象诊断。

验收预期：未选档位不能保存为0；匹配公司/rubric/criterion/期间；证据须关联、有权、hash一致、原文定位可核对；非法/过期证据不能评分；release清指针且不恢复旧AUTO；旧正文不混用当前元数据；未注册/重复/禁必需维度/非法权重拒绝；草稿保留其他当前规则、过期模拟不能发布；质量门不足UNKNOWN、有效硬风险排除、数值AND先false再unknown；自选A/H独立、取消幂等、身份隔离；失败保留输入、不报虚假成功；经营或任一证券估值缺失阶段partial；ops只读元数据不获得研究内容权限。

验证：隔离vip_v0001_test合成原创夹具（写前实际服务器与来源分类核验）；当前真实库仅只读产品验收，不生成虚假真实研判。无需schema迁移。不采购、采集、外发模型、通知、交易或生产部署。真实缺口仍UNKNOWN，正式封存/完整首slice不包含在本轮通过声明。

视觉：沿用18的灰白/蓝研究台token、中文系统字体；左导航、公司概览/独立证券/四标签；首屏一句结论、最多两缺口与一个主操作。业务依据可读、JSON进入有焦点约束的原生dialog。窄屏四入口加更多，表格独立滚动。

结果、处置和已运行证据如下；最终提交SHA以主干交付回读为准。

## 逐项处置与追踪

评审原文固定于上述main基线；本轮逐项整改并保持原业务合同。测试简称均位于[backend/tests/test_ux18.py](../backend/tests/test_ux18.py)，原R/W/T映射继续见18 §6.2、10及13，不将本轮检查外推为全量通过。

| 评审 | 处置 / 实现入口 | 已检查预期与证据 | UX18追踪 |
|---|---|---|---|
| UXR-01 | 新judgment_authoring服务、catalog/POST判断DTO、judgments作者对话框；score_company按rubric/criterion/期间及有效时间选择 | author_create/read/score/run/immutable/idempotent，非法/过期/工作区/权限拒绝，两个期间身份与expiry用例通过；一项不等于整维得分 | D03；03/07/08 |
| UXR-02 | grade初始为空，配置锚点radio；已有覆盖明确未选择状态；StrictInt拒绝空串/bool/超范围 | 空档位不提交，合法0与未知分开；浏览器作者表单未选档位禁保存 | 07/08 |
| UXR-03 | item_history固定item_snapshot；intake指定revision正文/标题/摘要/日期/阅读元数据同源 | history_metadata_consistent_and_legacy_unknown：后来更新不改旧元数据；无法还原旧字段明确unavailable，当前legacy_current分开；6份固定原文GET/hash回读 | 05/06 |
| UXR-04 | 注册维度、重复patch、必需维度、权重和政策类型校验；quality/event政策完整替换；field_origins到叶字段；模板双模式一份草稿 | template_registered_duplicate_replacement_origins与complete_policy用例；只改政策不改变权重来源，无自动归一化 | D04；02/03/10 |
| UXR-05 | changed_rules复制当前完整规则；模拟receipt/token绑定actor/workspace/规则/版本/关键输入；30分钟与CAS，发布存scoring_binding_manifest | strategy_preserves_rules_and_binds_simulation：未改规则不变，版本/输入变化拒绝旧模拟；历史解释与模拟preview独立状态 | D05；02/08/10 |
| UXR-06 | 服务端gates分风险、暂停、适用范围、必需维度/覆盖/财务时效/批准输入/FINAL/股权币种门，后处理普通数值AND；真实规则正常可读 | quality_gates_risk_scope_suspend_and_numeric_and：风险目标独立，缺必需依据UNKNOWN，质量通过后false优先于unknown；不推进正式membership | 01/04/06 |
| UXR-07 | release生成不可变released并清有效指针；worker固定cutoff与generation fencing重校验候选、生成新AUTO修订；列表/评分同一有效选择器，人工到期不回退旧AUTO | release_no_resurrection、release_worker_revalidates及expired_proposal：旧指针不复活，合法建议产生新修订，过期建议待重评；重复效果幂等 | 07/08；T-27/28/39局部 |
| UXR-08 | 409保留服务端实际原因；刷新失败保留已加载资料，提交成功与回读失败分开；用户/workspace remount、请求epoch/live/route及mutation guard隔离过时响应 | 浏览器临时阻断资料GET：中文连接失败、原6资料保留；撤销阻断恢复。后端CAS/幂等/权限场景通过；未穷尽所有浏览器并发调度 | 05/08/11 |
| UXR-09 | 自选GET返回稳定ID；本人+workspace POST/DELETE及audit/outbox；A/H卡片和我的工作台回读一致；加载失败显示未知 | watchlist_identity_scope_and_cancel_idempotence：独立A/H、本人/工作区隔离、重复取消幂等；未写真实用户自选 | D02；09 |
| UXR-10 | score输出criterion/status/reason/revision/age及动态覆盖；缺口按实际未完成维度汇总，保留已有有效评价项；研究score阶段同时检查经营与所有证券 | score_stage_partial_when_company_ready_but_security_unknown及首次录入用例：一项有效可见，经营ready而证券missing仍partial；旧快照保留原结果 | D01；01/03/06/11 |
| UXR-11 | worker/tasks和sources用已有ops.read；运维仅元数据；按capability导航 | system_admin_ops_without_research_access：运维200/研究403；最终API GET回读及浏览器独立admin只显示系统支持，无增加角色权限 | 11 |
| UXR-12 | 七页研究流，公司四标签默认质量/待补；业务依据正常可读，技术诊断在对象附近；原生dialog、键盘tab、窄屏四入口+更多 | 实际像素核对390×844公司A/H堆叠、整页宽390；ArrowRight/Home切标签、Escape关闭dialog并返回诊断按钮焦点；200%/真实设备/读屏/目标用户未验证 | 05/11/12 |

## 本轮已运行检查

实施分支为codex/ux18-implementation；所有本轮源码、测试、合同、页面产物、本文与只读回读一起提交，从安全main基线派生。最终实施revision是收录本文及ux18-readback.json的Git提交，交付响应给出完整SHA并回读远程main；评审时固定该SHA，不混读旧历史。回读文件[ux18-readback.json](../versions/v0.0.1/ux18-readback.json)还记录核心源码/合同/构建产物SHA256，绑定实际测试/运行树，不保存真实原文或原始财务响应。

| 环境 / 命令或操作 | 结果 | 实际范围 |
|---|---|---|
| 本机Homebrew PG14，vip_v0001_test；`./tools/vip test` | **81 passed，1 warning**，最后复测5.16秒 | 含14项本轮回归；写前实际服务器/来源分类已只读核验，conftest再拒绝非合成来源；warning为已有Starlette/httpx兼容提示 |
| `npm --prefix frontend run build` | TS检查/esbuild通过 | 使用锁定依赖与本地产物，无新框架/依赖；生成backend/static |
| `backend/.venv/bin/python tools/export_openapi.py`；`npm --prefix frontend run generate` | 同源生成通过 | 创建判断DTO、catalog、watchlist/ops/模拟token等已同步OpenAPI和TS；不是全部目标DTO已完成 |
| `python3 tools/verify_ux18_readonly.py`，最新8766 | GET-only通过 | 2公司/6份可读固定原文/3旧研究，2次manifest/hash一致；A/H各自仍未知，3个rubric目录；ops元数据200、admin研究403、空工作区公司0；不保存正文 |
| 真实公开资料库只读浏览器 | 主路径/历史/恢复/窄屏/键盘通过 | 默认公司标签、A/H参考报价/缺口、20条财务字段/五期间、固定原文返回保留公司标签，新增研判表单有真实锚点且空档位禁保存；两次旧研究资料/财务条数与Q/V/缺口/模板可读比较，不重算 |
| `git diff --check` | 通过 | 无schema迁移；原始资料、截图、凭证、dump和私人日志不入提交；旧含凭证分支历史不推送 |

本轮未在真实公司上输入虚构判断或运行写验收。经营评分仍需完整有效维度；自动判断的证据语义充分性不能由quote/hash一致推定，研究员对所选锚点与支持/反驳负责，服务端按当前证据类别/期限决定是否计分。真实来源权限继续实时校验；新snapshot仅从以后新修订开始完整记录，旧历史不能反向补造。

## 运行与授权收口

本机8766加载本次API/页面。仅签名核验停止本项目API/worker及本轮临时8767，8765原进程保留。自动审批起初拒绝恢复worker，指出它会处理未来任务写真实资料库；只读核验当前outbox为空后仍要求明确批准。用户随后明确回复“授权恢复原 worker”，批准vip_v0001_local中后续判断/研究任务的不可变修订、任务效果及audit/outbox写入；已恢复原API/worker（不新增采集/通知/迁移）。`./tools/vip dev-api`新增仅API启动入口，允许今后在worker保持停止时读页面；停止仍用签名校验的dev-down。

回退界面/逻辑可回到本轮基线并重新构建、停止/重启本项目服务；没有schema变化。已提交业务修订不可直接删除/覆写，后续使用合法新修订，不用代码回退来改写历史。

## 未完成与明确后置

本轮完成上述整改，不宣称原完整首slice或生产就绪：完整财报原始科目/口径、港股行情、FINAL日历与T-43封存、T-40完整风险创建/传播、历史纠错与撤权journal/实际恢复、Excel与接入矩阵、完整三层父链发布绑定、角色组合及T-UX目标用户签收仍见VERIFICATION。公司判断到期正确失效并等待合法新修订；本轮不声称完整到期调度/模型自动提议链已实现。

Pro允许后补的纯文本笔记作者/时间DTO、Markdown、评分差异图、完整策略AST/估值门槛编辑及更多设备检查未加入，不阻断本轮主研究闭环。策略维护只编辑现有受限经营门槛；模板预览不伪造评分差异。保留已确认价格/权限合同与上述完整必选，不能用新页面改名绕过验收。
