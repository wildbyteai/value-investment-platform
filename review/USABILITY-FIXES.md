# 可理解性评审处置与终审交接

2026-10-01。用户授权落实独立评审、整理提交，并准备以业务闭环和UI友好为重点的GPT Pro终审提示词。本轮只修改设计、合成本地原型及验证材料，未启动产品开发。

## 基线与采纳范围

本轮开始于`main` / `bc7cea39b6627de7028fd2ce2f2a72d4c042c72b`，工作区干净。旧独立报告[USABILITY-REVIEW](./USABILITY-REVIEW.md)固定于`ca4167d3f0fd9c52c8b08a98f834f94dd3204b59`，全文保留；它提及的旧截图和行号须从该提交读取。当前截图为本轮新版，不用它们冒充旧版评审输入。

采纳8项可理解性问题的最小改法：调整阅读顺序、短文案、现有链接去向和证券对象，不引入框架、审批或新业务能力。11/12、评分配置、风险范围及全部R/W/T保持原合同；档位解释取自既有标准配置。

## 逐项处置

| 旧发现 | 本轮改动 | 已执行原型核对 |
|---|---|---|
| 1 首屏先数字、缺研究结论 | 首页改“今日研究”，先说明用途、当前结论及主要动作，再显示演示期间历史；公司先结论和A/H原因 | PD-UX-01；桌面首页/公司截图 |
| 2 旧入选/估值被当作当前 | 比亚迪A股明确09-30缺价待评估、上次09-29已入选；策略行68.0标09-29历史值，当前原因写缺价。人工修改后公司列表、自选及策略都显示等待新评估 | PD-UX-02/04；桌面策略截图 |
| 3 尺度、覆盖含义不清 | 经营分/100、当前70阈值、日期、覆盖不是正确率；估值分方向和60阈值；影响值不是总分加减；资本配置0–4完整锚点 | PD-UX-03/05/06；PD-UI-07固定向量与配置对照 |
| 4 新闻缺有效判断 | 订单资讯、事件及原文旁显示系统/人工方向、理由与影响值；财务材料如实显示用于评分、没有独立事件影响判断 | PD-UX-04/05；桌面资讯/原文/判断截图 |
| 5 读分数却进入另一份草稿 | “为什么得到这个分数”直接进入该公司评分解释，先看已发布五维规则与证据；模板页先当前规则后待发布草稿，维护入口留在进阶区域 | PD-UX-03；桌面模板截图 |
| 6 原文像测试脚本、默认负值缺依据 | 原文移除测试目的，订单材料加入延期备货、库存和资金占用成本；先读当前判断，主动展开修改，影响草稿复制当前值0.8、档位草稿复制当前档位3；研究者写理由后才能保存新值 | PD-UX-04/05；PD-UI-01/03 |
| 7 手机关键状态靠后 | 公司结论、A股缺价原因及最近确认先于经营大分数；身份选择收进演示设置，声明仍可见 | PD-UX-08；390×844首屏截图 |
| 8 公司自选暗中只选A股 | 每只证券都有明确市场/代码的关注按钮，A/H独立保存；港股“查看估值依据”直接选择港股，不沿用上次A股选择 | PD-UX-07；PD-UI-07 |

示例主线是：比亚迪经营分达到已发布规则要求，但A股今天缺价；查看缺价后读订单与验收原文，核对系统的盈利判断，再查当前评分依据及港股估值。有不同意见的研究员主动展开修改并写理由；保存后判断已生效，新的经营分与证券评估尚未生成。格力的评分不受这次修改影响。

真实名称/代码只用于帮助理解，资讯、财务、价格和评分均为虚构；SYN-H风险仍属于独立虚构公司。没有伪造真实外部新闻链接。全部评分/模拟仍是固定展示样例，没有前端策略计算。

## 验证证据与界限

[浏览器报告](./design-detail/prototype-checks.json)：`2026-10-01T01:49:23.956Z`，运行时HEAD为上述`bc7cea3`，`source_sha256`绑定实际未提交原型、工具与三份配置输入。隔离无头系统Chrome，本地file页面，HTTP阻断；**73项通过**，无页面脚本错误和HTTP请求尝试。原65项场景继续保留，新增PD-UX-01…08；覆盖1440/1280/390/430宽度的关键页、编辑冲突保留、预览失效、原文互链与自选。

检查发现并修正：冲突重绘使编辑面板意外折叠；HTML数字输入不接受前导`+`而显示空值；档位草稿未复制当前档位；资本配置第4档说明不完整；港股依据入口未选择港股。新闻增加快捷入口后，原文互链断言限定至事件列表，仍要求每篇对应原文与返回保留。未更改业务预期来适配错误实现。保留[第一次失败记录](./design-detail/prototype-checks-ui-refine-attempt-01.json)；最终通过报告记录当前输入。

本轮已实际查看[桌面首页](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/design-detail/desktop-changes.png)、[公司](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/design-detail/desktop-company.png)、[判断](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/design-detail/desktop-judgment.png)、[策略](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/design-detail/desktop-strategy.png)、[原文](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/design-detail/desktop-original.png)、[手机首屏](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/design-detail/mobile-first-screen.png)和[手机资讯](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/design-detail/mobile-news.png)。手机首屏能看到公司结论及A股缺价，分数位于后面；截图检查不等于真实研究者已经看懂。

材料检查另见[validation-result](./validation-result.json)，检查引用、配置、合成合同与输入hash。没有执行真实用户5人计时、T-UX验收、屏幕阅读/真机、产品数据库/API/worker、真实权限、评分/模板/策略引擎、真实源或模型、部署；不得把本轮通过数写成这些验收通过。

06/16、原型README、PROJECT/README及V03账本同步；旧评审保持历史。此次取舍符合AGENTS的业务落地优先级，不以可选加固或更多评审阻塞设计收口。

## GPT Pro终审入口

[GPT-PRO-PROMPT](./GPT-PRO-PROMPT.md)先冷读页面、走业务主线、核查8项处置，再检查会影响结果的必要工程一致性；不要求重写全仓库、重新全量开源选型、穷举防御代码或增加审批/评审轮次。结论限于设计是否可收口，不能冒充上线验收。

优先使用已授权私有GitHub读取并固定实际commit；无连接时用[核心正文](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/FINAL-REVIEW-PASTE.txt)，完整[REVIEW-PACK](https://github.com/wildbyteai/value-investment-platform/blob/archive/r2-pre-slimming/review/REVIEW-PACK.md)按疑问查阅。正文不含截图像素，无法看图必须明确视觉未执行。**GPT Pro终审尚未执行，本轮只准备提示与材料，没有对外模型调用。** 产品开发与真实接入仍需要单独授权。

## 后续终审状态（2026-10-01）

上文是645ab64形成时的收口记录；随后用户提供GPT Pro终审共享页并授权修正三项。终审已取得，历史依据/新值显示/策略版本局部修正完成，见[终审处置](./GPT-PRO-FINAL-DISPOSITION.md)。不把当前截图回填为旧评审实际输入，也不要求再次终审。
