# 16 页面原型、设计连接与核对任务

2026-10-01 · v0.3设计细化。页面语义与状态合同以06为准，业务以11/12为准。本轮制作本地可点击原型，未启动W-08产品实施。

## 1. 设计方向与打开方式

原型入口：[index.html](../prototype/index.html)。直接用浏览器打开即可，不安装依赖，不启动API/数据库；HTML、CSS和JavaScript均为本地文件，无CDN/外部字体/模型。原型有独立演示标识，用比亚迪（002594/01211）与格力电器（000651）的真实名称和证券代码展示；资讯正文、财务、评分与行情全部虚构，另有独立虚构风险案例，操作存于内存。

沿用06的浅灰背景、深墨文字、蓝色操作、琥珀缺口、绿色有效与红色明确风险。信息左对齐；14–16px系统中文正文、28px页面标题、等宽数字；主要区域只设置一个主动作。独特重心是“事件事实与判断依据”的研究路径，不用行情大屏或装饰性KPI取代研究。变化列表按证券标明范围，公司页按经营主体组织，A/H状态始终并列。

先画页面规格和关系，再制作HTML；审查时保留事实、作用对象、覆盖度、数据时点与原文入口，工程hash/token收进说明而不占业务首屏。桌面左右阅读证据与判断；手机竖向排列，业务导航在底部，规则编辑应回桌面。原型仅用于设计讨论与交互检查，尚未完成人员可用性验收。

## 2. 页面地图与字段来源

| 页面/路由 | 主要动作 | 显示/输入对象 | 拟用API（尚未运行） | 流程/需求 |
|---|---|---|---|---|
| 今日研究 `#changes` | 当前结论/优先动作；历史市场/类型筛选→固定解释 | transition类型、公司、security、known_at、解释 | GET /changes、/dashboard | BF-01/04，R-08/09 |
| 当时解释 `#change/enter` | 读固定依据→看当前状态 | release、evaluation、前后状态、snapshot | GET /changes及固定解释 | BF-04/05，R-07/08 |
| 公司列表 `#companies` | 搜索主体/证券→公司档案 | company、证券关系、Q/coverage、质量 | GET /companies | BF-01，R-04/09 |
| 新闻资讯 `#news` | 公司/类型/发布日期筛选→原文→返回原筛选 | information item/revision、published_at、source、摘要、关联公司与事件 | GET /information | BF-01/02，R-02/04/09/14 |
| 公司档案 `#company/a`、`b` | 新闻资讯、研究事件、分数、财务、证券估值、关系、笔记、自选 | event、score/metric snapshots、note、watchlist | GET /companies/{id}及timeline/scores；/securities/{id}/valuation | BF-01/02，R-04…06/09 |
| 原文 `#evidence/{id}`（旧`#evidence`默认订单样例） | 逐篇完整正文/高亮、三种时间、同事件其他原文→公司/判断；返回保留筛选、不可访问说明 | item_revision、evidence.locator、source policy | GET /information/{id}/revisions/{revision}、/evidence/{id}/access | BF-01/02，R-02/03/11 |
| 人工覆盖 `#decisions/a` | 先读判断→主动编辑impact/档位/拒绝风险，草稿默认沿用原值；解除覆盖 | slot、完整新judgment、reason、valid_until、revision | POST /decisions/{slot}/overrides与release-override | BF-02，R-03/05/16 |
| 模板 `#templates` | 看继承/覆盖/最终值；改龄期/事件参与；预览/发布 | draft、template父链、registry、effective_config、origin | resolve/simulations/publish、/scoring-bindings/publish | BF-03，R-15 |
| 策略 `#strategy` | 候选→阈值草稿→固定模拟→确认新发布；回滚提案 | security、Q/V、AST、preview、release | drafts/simulations/publish、rollback-preview | BF-03/04，R-07/08 |
| 自选 `#watchlist` | 移入/移出证券→公司研究 | watchlist/entry、owner、security | GET/PATCH /watchlists/{id} | R-09 |
| 来源 `#sources` | 合成导入；暂停/恢复；配置发布预览 | source、policy、schedule、run | /admin/sources及preview/publish/pause/resume | BF-01，R-01/10 |
| 任务 `#jobs` | 看业务影响→仅恢复一项失败 | job、run、result/error、affected security | /jobs/{id}/retry-preview、retry | BF-05，R-10/12 |
| 质量 `#quality` | 缺价恢复、更正窗口预览与说明 | quality gap、correction、后续sessions | /quality、/correction-previews、/corrections | BF-05，R-10/12 |
| 身份 `#identity` | 分清company/security/listing、变更范围预览 | 身份关系、generation、preview | /identity/merge-preview、split | R-03/06/10 |
| 用户 `#roles` | 五角色组合→差异→保存 | membership_user.roles/capabilities/version | GET /admin/roles、PUT /admin/users/{id}/roles | R-11/17 |
| 模型费用 `#models` | 查看mock政策、用量与接入状态 | analysis usage、model_policy、credential_ref | /models/policies、/costs | R-10/11 |
| 审计 `#audit` | 看业务动作及修订引用 | audit_event（不含秘密） | /audit | R-10/12/13 |

页面展示的时间、分数与模拟结果是固定合成对照。比亚迪名称案例是完整编辑主路径；格力电器名称案例用于验证主体独立、单证券演示与企业差异不传播，未为B配置第二份完整人工编辑样例。无实时服务端查询，也无前端评分/规则引擎。

## 3. 原型交互约定

- 资讯原文逐篇对应，不把所有卡片送到同一披露；同一订单事件的公告与新闻可互链。资讯按发布时间倒序，筛选状态在原文往返时保留，未知原文ID显示未找到；格力电器财务入口不会跳到比亚迪原文。事件日期未知或只有日期/报告期时明确标注，不编造具体发生时刻。
- 主界面使用评分档位、资料有效期、连续几个交易日等中文解释，合同中的rubric/FINAL/session等标识仍留在设计文档中；不改机器合同。
- 首页/公司页先结论和下一步，再查看数字；当前缺价与上次入选分开。策略A股旧估值68明确为09-29历史值，关键原因必须是当天缺价。评分解释入口在当前公司内展示已发布权重/阈值/日期，不跳待发布模板；模板编辑与策略维护为进阶入口。
- 新闻/原文/研究事件共用当前有效影响与理由；资料原文不包含测试目的。人工编辑初始折叠，主动展开后复制当前影响值；0–4资本配置锚点来自标准rubric。保存后显示人工判断已保存与依赖重算等待，格力电器不受比亚迪重算等待影响。
- 自选分别按A/H市场和代码操作；手机先显示当前结论与缺价，身份演示设置折叠。
- 人工修改直接保存，显示新人工值与重算等待；查看者只读。impact/rubric/risk各有独立演示修订状态；旧AUTO不因其他slot被覆盖而显示HUMAN。
- 409演示保留新值和理由，先比较当前版本再重试。证据、身份、有效期和时点的服务端完整校验仍是目标设计，不由原型证明。
- 原型模板为另一个待发布扩展草稿，与当前已发布企业35/20/25/15/5%方案分开；扩展草稿盈利继承制造业30%，成长5%及客户留存5%，六维总权重100%。提供90/180日证据龄期、enabled/H与baseline-only两个分支；不允许任意注册自定义字段。完整配置示例仍由examples和contracts定义。
- 修改模板设置或策略阈值会使旧预览消失；发布按钮只对相应合成角色开放。模板研究员可编辑，发布需策略管理员；system_admin不自动有业务读取/发布/覆盖。
- A/H价格、币种与估值独立。09-29合成评分72、覆盖100%；09-30 A缺价待评估并保留last=IN，H因估值条件未满足为OUT；挂牌风险单独使用虚构公司/SYN-H，不属于真实公司名称案例。缺价只影响证券估值/评估，不抹去公司有效经营分。影响替换后的公司重算等待则经营分快照仅供旧值比较，证券候选页同步标记等待与旧值。
- fixed history与current明确分开。纠错演示保留s2记录、检查s4/s6，独立s6成立时当前IN不变。
- 来源暂停后演示导入不可点；失败项恢复仅限一证券一session，不代表全量重跑。角色差异保存及更正仅为内存演示。
- 手机支持查看与轻量覆盖；模板与策略复杂编辑回桌面。加载、空、部分失败、不可见、冲突、UNKNOWN/等待、更新提示、停牌可以用底部设计控件切换。

## 4. 所有需求的设计落点与剩余验证

| 需求 | 本轮落点 | 后续验证/范围说明 |
|---|---|---|
| R-01 源与调度 | BF-01、source/policy/schedule/run/checkpoint、来源原型 | 真实适配/限流/授权尚未接入 |
| R-02 原文修订检索 | BF-01/05、item observation/revision/evidence、原文页 | 全文/语义在W-03；原型有公司/资讯筛选与逐篇原文关联，不宣称完整全文/语义检索完成 |
| R-03 多公司关联 | 判断slot自然键、受限候选/证据、身份关系 | 原型主样例仅单公司；0/多公司/歧义由T-05/06实施验证 |
| R-04 时间线 | BF-01、event/fact/证据关联、资讯与研究事件两种时间线 | 资讯按发布时间倒序、原文分别列出发生/发布/取得时间；未实现分页、按known/event时点查询 |
| R-05 公司评分 | baseline/contribution/snapshot、维度解释与覆盖 | 固定样例，Decimal黄金向量与去重/吸收未运行 |
| R-06 证券估值 | company→security→listing、财务/价格/FX/义务、A/H切换 | 真实币种/股本/财报修订由T-10/36/37验证 |
| R-07 策略维护 | BF-03、draft/version/preview/release、模拟发布原型 | 未实现AST/时点模拟引擎；样例输出不证明正确计算 |
| R-08 状态与变化 | BF-04/05、seal/membership/transition/correction、历史解释 | 两相邻session/并发/硬风险由T-13/40/43验证；通知继续后置 |
| R-09 业务工作流 | 新闻资讯/今日研究→公司→对应原文→覆盖，自选/笔记 | 未做目标研究员用户测试 |
| R-10 管理 | 源/任务/质量/模型/身份/审计与表映射 | 操作均演示；费用/真实故障尚未连接 |
| R-11 权限/机密 | 五角色入口、对象作用范围、复合workspace FK设计 | 客户端门禁不代表服务端安全通过；全路径权限测试未运行 |
| R-12 恢复 | BF-05、ledger/fence/outbox及同事务边界 | 未运行崩溃、丢ACK、备份恢复与独立journal |
| R-13 工程规范 | 字段目录生成工具、原型检查与输入hash、既有材料工具 | 生产CI/迁移/回滚在实施阶段，不能算完成 |
| R-14 统一UX | 共享tokens、组件模式、四视口交互检查 | 键盘抽测；5用户计时、读屏、200%浏览器缩放/真机未运行 |
| R-15 三层模板 | BF-03、冻结父链/registry/config/binding、三列原型 | 服务端解析/维度总权重/升级验证未运行 |
| R-16 AUTO/HUMAN | BF-02、统一修订根/人工链/decision指针、覆盖/解除界面 | 真实优先级、到期重评和事务回滚尚未运行 |
| R-17 多人RBAC | 成员表、能力解析与五角色演示 | 真实会话、撤权、并发授权/最后管理员保护尚未实现 |

## 5. 核对方法与证据边界

设计材料：运行 `python3 tools/render_database_design.py` 检查表/字段引用并生成字典；运行 `python3 tools/validate_design.py` 检查既有合同与更新材料。

原型：运行 `node tools/verify_prototype.cjs <Playwright模块路径> <浏览器可执行路径>`，在独立无头浏览器中打开本地file原型，阻断HTTP请求，检查固定维度向量/总分与实际模板配置一致、资讯顺序/筛选/逐篇正文/返回/同事件原文互链/虚构风险隔离、导航、完整人工值/冲突保留、角色入口、预览失效、自选笔记、失败项恢复、合成更正、当前/历史分开、已发布评分入口、主动编辑、档位锚点、自选A/H及手机首屏，以及1440/1280/390/430宽度。结果见[prototype-checks](../review/design-detail/prototype-checks.json)。这些是原型交互与页面布局检查，不是T-UX-01…04的5人计时任务，也不证明真实权限/DB/评分引擎。

截图：[股票候选](../review/design-detail/desktop-strategy.png)、[只读判断](../review/design-detail/desktop-judgment.png)、[新闻资讯](../review/design-detail/desktop-news.png)、[资讯原文](../review/design-detail/desktop-original.png)、[手机资讯](../review/design-detail/mobile-news.png)、[桌面变化](../review/design-detail/desktop-changes.png)、[公司研究](../review/design-detail/desktop-company.png)、[模板](../review/design-detail/desktop-template.png)、[手机公司页](../review/design-detail/mobile-company.png)。截图代表对应合成正常状态，不表示所有设计状态均经过人类可用性验证。

本轮成果足以对照流程、字段和主用户路径；实现选型时再落实PG版本/迁移、生成类型合同及cutoff提交可见性协议，沿用原T预期。无需为了可选平台或新增全量评审暂停设计收口。

本轮可理解性8项处置与剩余验证见[USABILITY-FIXES](../review/USABILITY-FIXES.md)，历史评审固定在ca4167d。GPT Pro终审提示以业务闭环/界面友好为主，不重复全部防御性工程评审；提示词已准备不代表终审已执行。

## 6. GPT Pro终审后的三项局部修正

09-29固定评分/A-H估值使用历史财务原文`byd-report-historical`（09-27发布/取得）；09-30的`byd-report`仍在新闻中作为后来更新。评分页后续订单/资本配置判断不作为该旧评分输入。修改区保留当前有效值和唯一的新值输入，去除重复新值摘要。策略发布固定版本/门槛，新评估等待，固定旧结果明确归发布1；公司研究对照也标发布1。发布新模板不强制更新旧策略。

三项已执行检查为PD-FINAL-01…03，证据及边界见[终审处置](../review/GPT-PRO-FINAL-DISPOSITION.md)。新增截图：[历史评分依据](../review/design-detail/desktop-score-evidence.png)、[修改区](../review/design-detail/desktop-judgment-edit.png)、[新规则与历史结果](../review/design-detail/desktop-strategy-published.png)。更详细的基础/贡献/财务分母解释留在已有开发切片，不要求增加终审轮次。
