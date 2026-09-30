# 12 时点、数值与纠错合同

v0.2设计。修复第二轮研究B-01…04与S-01…09；研究报告记录旧版证据，本文件定义当前目标行为。未运行产品或灾备演练。

## 1. 财务指标与rubric

指标定义数字真源为[metric-definitions-v2.json](../config/metric-definitions-v2.json)。CFO现金转换率=最近三个完整财政年度合并CFO合计/同三个年度合并净利润合计；不能用集团CFO除归母利润。ROE采用归属普通股股东的TTM利润/匹配范围平均普通股权益；证券PE另用同权普通股每股归属盈利。合并净利润、归母利润、普通股利润分别存储，不互相代填。无法匹配合并范围、会计期、单位/币种则invalid。

TTM按合法已知期间计算；市场未提供季度资料时可使用“最近年度+本期累计−去年同期累计”，仍缺必要期间则missing，不拼造季度。3年历史本来需要旧年度，不按公告年龄一刀切。财务新鲜度由report_obligation记录发行人、市场/板块、财年末、报告类型、所需期、到期日、正式例外及来源。旧报告更正不能当新期间。到期前用最新合法可用期，超过批准宽限仍缺应有报告则stale；三年指标同时检查三个完整年度及最新应有年度。

HK主板通常全年业绩≤年结后3个月、半年业绩≤期末后2个月，仅是第二轮已核查的常规例子，不涵盖所有例外或报告派发期限。A股、其他板块、发行人例外必须在真实适配器接入前固定义务映射；未配置不能自称新鲜。合成切片直接提供冻结义务表，不阻碍开发。

[rubrics-standard-v1.json](../config/rubrics-standard-v1.json)提供11项0–4档锚点。每项判断记录period、档位、支持/反驳证据、confidence、effective/known时间、有效期和AUTO/HUMAN决策。无证据或未调查用null；冲突不能取中位数。rubric不是统计概率或投资收益。

## 2. 最终收盘与知识边界

每证券首版绑定一个primary Listing，保存exchange、currency、calendar_ref与close_policy。A/H为不同security、共享company；报价/FX来源属于listing。多币种柜台若未配置独立估值口径则unsupported，不能共享一个不标币种的V。首版membership仍为workspace+release+security，其release固定primary_listing_id。

日历只给expected sessions及市场时段，不能证明价格FINAL。港股适用CAS证券的最终收盘不能用16:00连续交易末值替代；半日和非CAS按获许可源的价格类型处理。适配器必须输出session、price_kind、is_final、source_revision、observed_at。日历固定版本、年份范围、临时休市和深市映射；覆盖不足显式UNKNOWN，不用工作日猜测。

标准evaluation_as_of为该证券批准session的最终市场时点，knowledge_cutoff固定为该时点后60分钟；这是初始可维护宽限，不是已验证源SLO。FINAL判定需要全部冻结输入合法或明确质量缺口，到cutoff不能取得最终价则该session生成UNKNOWN缺口。重试沿用cutoff，不使用重试时now延长。

| 输入类别 | 收盘评估的可用条件 |
|---|---|
| 日收盘行情 | 正确session和最终价格类型；在固定cutoff前observed，允许供应商收盘后发布 |
| 公告/经营事实 | 首次published≤evaluation_as_of且observed≤cutoff，有效期适用；收盘后新公告进入下一session，日内硬风险走独立即时判断 |
| AUTO/HUMAN判断 | decision.known_at≤cutoff，引用输入也满足对应类别条件；晚批准不能回填 |
| 确定性计算 | 可以cutoff后完成，但只能消费已冻结合法manifest；generated_at记录真实完成时间 |

实时硬风险在其决策实际生效时更新风险状态，不把当晚新信息伪装为收盘前信息。research_reconstruction、reanalysis和历史纠错与live分开，不混算性能或补发过去信号。

## 3. 相邻session、单调应用与暂停

enter/exit均需两个相邻expected FINAL sessions。同session provisional更新不计数；FINAL只应用一次；UNKNOWN、应有session漏评估、停牌、范围级暂停打断pending。周末或日历批准休市不算漏评估。s1 true、s2缺口、s3 true只能1/2。迟到s2不能倒灌当前membership，也不能把s1与s3重新拼成连续满足。

membership记录last_applied_session、generation、finalization_token及pending session IDs。提交检查release/binding/input generation、当前session单调性、唯一finalization_token和行锁/CAS。更早session保留历史结果，不能改当前指针；同session封存后更正走下节。硬风险独立revision/generation同样检查，不能由旧风险解除覆盖新风险。

个人静默/订阅暂停只影响后续notification delivery；不属于共同membership的SUSPENDED条件。范围级暂停需strategy.manage权限并明确影响全部订阅者；首版没有个人通知开关。市场停牌仍SUSPENDED并保留last_confirmed。

## 4. 历史纠错与当前状态

FINAL后的输入修订建立correction_run，不覆写原evaluation、finalization_token或transition。correction记录原对象、错误类别、合法替换manifest、影响范围、算法/模板版本、截止和新解释。只有原数据/映射/计算错误属于纠错；现在新出现的知识是新判断，不能回填过去。

从受影响窗口之前的未受影响FINAL锚点，沿冻结后续sessions重放原发布策略及对应模板，逐项标记哪些evaluation/transition失效或保持成立。历史视图保留“当时记录”和“更正说明”；不删除实际发生过的ENTER/EXIT。纠错结果产生CORRECTION记录。若重放影响当前状态，使用最新合法输入完成当前reconciliation；提交前CAS最新release、generation、last_applied_session，过时则重新预览而不覆盖。

若s2 ENTER、s4 EXIT、s6 ENTER，后来纠正s2，不能直接把当前IN改为OUT；必须检查s4/s6依据和相邻确认。后续s6独立成立则当前仍IN，只追加历史说明。若确需改变当前状态，产生一条CORRECTION状态调整而非伪造今天的市场EXIT。首次基线/CONFIG_CHANGE/CORRECTION/RISK/MARKET分别分类。

## 5. 经济事实去重与吸收

event容纳多个claims；economic_fact_id定义公司/对象+动作+财务期间/合同批次等同一经济事实。贡献slot=(company,economic_fact_id,dimension)。多event或转载指向同一事实也只允许一个有效贡献。事实矛盾保留support/refute，不通过“更高来源权重”无条件消灭冲突。

新baseline吸收事实时，baseline revision、吸收的fact/slot版本、有效贡献指针和outbox同事务提交；不能先加新baseline再异步减旧贡献。跨workspace/不可访问来源的贡献不会偷偷进入可见总分。派生snapshot继承required_source_ids/visibility；证据撤权导致当前结果重新检查、降覆盖或失效，而非仅隐藏证据链接。

讯息的content revision与observation分开：A→B→A可以复用A内容blob，但必须有三次不可变observation(sequence,observed_at,revision_ref)，当前指针由最新observation确定，不因内容hash重复丢失回退历史。对象清理必须同时检查DB活跃引用及保留期限，不能仅凭对象tag删除。

## 6. 确定性数值与任务身份

[numeric-policy-v1.json](../config/numeric-policy-v1.json)是算法数值规范。金额和比率十进制字符串；后端Python Decimal作为唯一规则计算路径。precision=50、ROUND_HALF_EVEN；每个持久化计算节点quantize到小数点后12位（系数输入保留原有效精度），按metric→baseline→单事实贡献→按fact ID排序求和→贡献cap→维度clip→Q/V顺序处理。策略比较使用持久化12位值，显示1位小数不参与比较。

age是UTC有效事件时间到as_of的完整秒数除86400，不按本地午夜跳日；日期粒度事件采用来源时区当日00:00并标precision，不精确宣称秒级时间。衰减通过precision=70的guard上下文计算Decimal(2)**(-age/H)，然后ROUND_HALF_EVEN量化12位；实现锁定Python/decimal运行版本、算法hash，并提供非整数幂黄金向量。不同语言仅离线误差对照，不能另做membership判断。时间到valid_until采用半开区间，t≥valid_until贡献0。

解析/索引等静态job身份=workspace+stage+entity_revision+algorithm_version+mode+input_hash。评分/到期/收盘/覆盖解除等时间相关job再包括as_of、knowledge_cutoff、time_bucket/session、calendar、template_resolution、numeric_policy和decision_policy版本。重试沿用完整逻辑键；时点不同必须是不同job。新job不意味着允许旧输入覆盖当前，generation/fencing仍必要。

## 7. 旧备份恢复后的撤权

恢复安全合同保留，但实现不要求新微服务。正常权利撤销先向独立于应用备份的耐久revocation_journal追加序号、scope和hash链，取得durable receipt后再撤销DB权限和投影；拒绝读取可以先发生，撤销操作未完整耐久则状态pending禁止恢复开放。journal使用独立保留的对象存储/介质，latest watermark不能来自同一份旧DB备份。

恢复始终在隔离环境、无发送；验证journal完整性和最新watermark，施加自备份cutoff之后全部撤权，重建ACL/索引并测试，再开放受影响读路径。不能验证最新依据时fail closed相关范围。首版合成场景用独立本地journal fixture验证合同；真实资料接入/生产恢复前才选择实际独立耐久存储并演练，不把尚未配置的灾备说成已实现。
