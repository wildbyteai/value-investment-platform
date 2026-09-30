# v0.3跨模块固定推演

全部合成、设计预期；NOT RUN产品/数据库/UI。原场景不更改，新增细化以T-39…43追踪。下表“记录”均为期望，首版delivery=0，无真实发送。

| 场景/覆盖 | 输入及顺序 | 应有事实/分数/状态与恢复 | 追踪 |
|---|---|---|---|
| C01 多公司/无关联 | 一份原文直接涉及A/B，另一份无封闭候选匹配 | 两条独立证据关联；no_link不得附影响/风险；歧义pending且不贡献；重试原逻辑键不重复 | T-05/06/17 |
| C02 A/H风险分离 | 同company A/H；只H挂牌退市→之后公司债务违约→拒绝H判断 | 首次H OUT/RISK，A不因此改变；违约A/H适用；拒绝H仍公司风险OUT。最后风险解除从OUT重新正常确认，不即刻ENTER | T-10/40 |
| C03 市场休假/停牌 | 港股session开放/A股批准休市；随后H停牌 | A休市不算漏评估，H各自日历；H SUSPENDED保留last_confirmed并清pending，恢复后重新两session确认 | T-11/30/31 |
| C04 财报修订/TTM | 旧财报合并CFO75/合并利润100；归母利润50；缺一季度但有本/上年累计 | 比率0.75非1.5；TTM合法推导并保留来源，缺必需期missing；旧报告更正不满足新期义务 | T-07/36/37 |
| C05 晚到/封存 | 价格+15 FINAL，公告−5 published/+40 observed/+50决策，+60冻结/+65完成 | +15仅provisional不计数，最终manifest有公告/决策；+65真实生成仅一次应用；+61 known不回填，原错误才CORRECTION | T-38/43 |
| C06 转载/吸收 | 同订单五篇转述、两个event映射一个economic_fact；财报吸收并故障 | 单slot贡献；baseline、吸收指针和outbox同事务，失败全回滚，恢复无双计 | T-03/08/34 |
| C07 来源冲突/证据缺失 | 两份正文互相矛盾；另风险只有标题 | 留support/refute而非按高权重强取；pending不贡献/不风险OUT；缺价或必需基准UNKNOWN保留last_confirmed | T-06/09/21/28 |
| C08 缺失覆盖/未知恢复 | Q高但coverage0.75；s1 true、s2缺口、s3 true | 不因高Q入选；s2 UNKNOWN清pending，s3只1/2；旧s2迟到不拼连续计数；原基线不丢 | T-09/13/30 |
| C09 人工完整修改 | AUTO impact+0.8→HUMAN−0.2；rubric3→1；新AUTO到达 | 新不可变修订/accepted决策/CAS审计outbox同事务；重算A/H经营分，估值独立；旧值保留；新AUTO不覆盖；到期固定cutoff合法重评 | T-27/28/39 |
| C10 并发/崩溃 | 两人generation4编辑；双worker同seal；commit后崩溃/Redis清空/旧lease迟到 | 一人成功另一人409保输入；同manifest唯一token/transition，ACK丢重读原结果；ledger恢复，旧fence拒绝，权限撤销提交重验 | T-14/18/39/43 |
| C11 模板/策略发布 | 180日治理输入age120改90；发布父版/企业版；同百分制不同口径 | 新90 stale且必需项UNKNOWN，180旧release不变；source/origin/hash固定；模拟预览新binding/release为CONFIG_CHANGE，不伪市场EXIT | T-12/25/26/41 |
| C12 自定义维度 | company模板启用注册x_customer_retention H90；随后baseline-only；模型送未注册维度/H30 | 合法维度weight/baseline/policy齐全，总和1；基准解释保留；baseline-only拒绝事件，不造贡献；未知/不适用/H不符422 | T-08/25/42 |
| C13 历史纠错/新release | s2 ENTER、s4 EXIT、独立s6 ENTER；纠正s2同时发布新release | 原记录不删除，冻结窗口重放；独立s6仍IN。当前reconciliation CAS新generation，新release不被旧结果覆写；只CORRECTION | T-14/32 |
| C14 撤权/旧备份 | 引用资料撤权后恢复早期DB备份，journal缺最新watermark | 独立journal未确认就关闭相关读路径；确认后施加全部撤权，派生分数/缓存/搜索也失效；隔离恢复无发送 | T-15/19/34 |
| C15 外部发送未知（后置） | 将来渠道不支持幂等，发送超时 | UNKNOWN_DELIVERY查询/人工确认，不盲重发、不重跑membership；本阶段不创建delivery，delivery=0 | T-16（后续） |

本轮材料检查覆盖其中字段形状、继承和少量确定性边界；并未执行上述整条路径。用户任务指标仍以06 §7/8为准，不能从这张表推导UAT通过。
