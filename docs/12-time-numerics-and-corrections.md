# 12 时点、数值与纠错合同

v0.3设计。修复第二轮研究B-01…04与S-01…09；研究报告记录旧版证据，本文件定义当前目标行为。未运行产品或灾备演练。

## 1. 财务指标与rubric

指标定义数字真源为[metric-definitions-v2.json](../config/metric-definitions-v2.json)。CFO现金转换率=最近三个完整财政年度合并CFO合计/同三个年度合并净利润合计；不能用集团CFO除归母利润。ROE采用归属普通股股东的TTM利润/匹配范围平均普通股权益；证券PE另用同权普通股每股归属盈利。合并净利润、归母利润、普通股利润分别存储，不互相代填。无法匹配合并范围、会计期、单位/币种则invalid。

TTM按合法已知期间计算；市场未提供季度资料时可使用“最近年度+本期累计−去年同期累计”，仍缺必要期间则missing，不拼造季度。3年历史本来需要旧年度，不按公告年龄一刀切。财务新鲜度由report_obligation记录发行人、市场/板块、财年末、报告类型、所需期、到期日、正式例外及来源。旧报告更正不能当新期间。到期前用最新合法可用期，超过批准宽限仍缺应有报告则stale；三年指标同时检查三个完整年度及最新应有年度。

HK主板通常全年业绩≤年结后3个月、半年业绩≤期末后2个月，仅是第二轮已核查的常规例子，不涵盖所有例外或报告派发期限。A股、其他板块、发行人例外必须在真实适配器接入前固定义务映射；未配置不能自称新鲜。合成切片直接提供冻结义务表，不阻碍开发。

[rubrics-standard-v1.json](../config/rubrics-standard-v1.json)提供11项0–4档锚点。每项判断记录period、档位、支持/反驳证据、confidence、effective/known时间、有效期和AUTO/HUMAN决策。无证据或未调查用null；冲突不能取中位数。rubric不是统计概率或投资收益。

## 2. 最终收盘与知识边界

每证券首版绑定一个primary Listing，保存exchange、currency、calendar_ref与close_policy。A/H为不同security、共享company；报价/FX来源属于listing。多币种柜台若未配置独立估值口径则unsupported，不能共享一个不标币种的V。首版membership仍为workspace+release+security，其release固定primary_listing_id。

日历只给expected sessions及市场时段，不能证明价格FINAL。港股适用CAS证券的最终收盘不能用16:00连续交易末值替代；半日和非CAS按获许可源的价格类型处理。适配器必须输出session、price_kind、is_final、source_revision、observed_at。日历固定版本、年份范围、临时休市和深市映射；覆盖不足显式UNKNOWN，不用工作日猜测。

标准evaluation_as_of为该证券批准session的最终市场时点，knowledge_cutoff固定为该时点后60分钟；这是初始可维护宽限，不是已验证源SLO。价格is_final只说明报价类别；收盘evaluation封存另需§8协议，全部冻结输入合法或明确质量缺口，到cutoff不能取得最终价则该session生成UNKNOWN缺口。重试沿用cutoff，不使用重试时now延长。

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


## 8. 收盘输入冻结与唯一封存（F05）

价格FINAL、输入冻结、evaluation封存、membership应用是独立状态。session_due→provisional→ready_to_seal→sealed；终态sealed结果可为valid/UNKNOWN/SUSPENDED，不意味着全输入有效。provisional的knowledge_cutoff使用本次实际已知截止且≤generated_at，目标收盘截止另存planned_seal_cutoff；不得把未来+60作为提前run的已知截止。目标cutoff前只可provisional，不创建finalization_token、不计session、不推进普通membership。只有服务端clock≥固定cutoff且日历/最终市场时点合法才能ready_to_seal；没有最终价仍可封存明确UNKNOWN质量缺口，日历/时点未知则记不可封存缺口，禁止用worker now猜cutoff。

strategy服务内部[seal命令](../contracts/evaluation-seal.schema.json)固定release/security/primary_listing/session/as_of/cutoff、manifest ID/hash及expected_generation。用户或模型不能自行封存；调用身份须有受限strategy worker capability，提交仍检查workspace、来源权利与lease fencing。[manifest合同](../contracts/evaluation-input-manifest.schema.json)与[合成示例](../examples/v03-seal-manifest.json)逐类强制输入或缺口；示例hash真实绑定命令，不是已获数据。manifest包含身份/日历、价格/FX/股本、财务/报告义务、关联/影响/rubric/风险/人工覆盖、全部政策/模板/算法版本，逐类revision或显式缺口；不能只冻结价格。

输入选择以§2为准。每类在cutoff内的最后合法修订按known/observed+稳定revision排序；决策与依赖引用也须同cutoff。同时间冲突记录conflicting，不任意择高分。全部参与提交的输入写入事务时由数据库生成knowledge序列和不可回填时间；cutoff后写入不得伪造为早期已知。冻结在PG一致性snapshot内完成，持久化input_refs/quality gaps、内容hash、cutoff watermarks与selection算法版本。队列中的未完成分析不算已知判断，不等待并放宽cutoff；缺口如实UNKNOWN。

冻结manifest与seal slot的generation/CAS同事务，只允许一个(worker fence有效的)冻结候选。固定键(workspace,release,security,session,live)唯一seal slot；provisional有独立run，不占最终键。cutoff后算分可在事务外运行；worker崩溃/丢ACK重用已冻结manifest，双worker不得以各自manifest分别宣称同session FINAL。未sealed候选需要因合法校验失败重新冻结时先CAS废弃旧generation且保留历史记录；已sealed只能走CORRECTION。迟到原数据更正与新知识按§4区分，不能借重试改manifest。

最终事务校验manifest hash、cutoff≤sealed_at/generated_at、当前release/binding、seal generation、worker fence和最新risk/ACL generation；写immutable evaluation、seal_at/token、应用指针、transition解释、audit/outbox同事务。唯一token按seal slot稳定生成；幂等重试返回原结果。若release/session已更迭，封存历史可保留但application_status=superseded，不应用当前membership。实时硬风险仍独立优先，旧普通评估不能解除新风险。撤权使旧冻结输入不可读/不可应用，记录失效并走安全重算/纠错，不为复现保留违规正文。

固定推演（T-43）：以本证券最终市场时点为+0；+15价已is_final只能provisional；一份published=−5min公告+40 observed、+50判断生效→在+60冻结时可用；+60生成manifest，+65实际完成则generated_at=+65，唯一封存且仅一次计数。+61才known的判断不进入此manifest；收盘后新公告也不因+60前observed进入本收盘。缺价封存UNKNOWN清pending；重试不把cutoff延到+70。状态/原子性是设计合同，尚无worker/数据库运行证据。

### 2026-10-06 原始科目实现注记

原始科目转换实现允许有界的`reviewed_signed_sum_v1`：同期间/合并范围/币种的原值分量按±1求和，保留各分量单位、原值、固定修订/hash/定位与独立转换依据；拒绝重复、嵌套、期间/币种/股数与金额混用及将转换结果标为original_value。TTM与指标公式不变。

已知期后发行、回购或库存股过户会使报告期末股数不再适合后续价格。标准输入可保留有原文依据的`ordinary_shares_valid_until`和`share_change_evidence`；到该exclusive时点后，估值返回SHARE_BASIS_EXPIRED、同权股数门失败，直到取得更新股数证据。财报义务有效期和股数有效期分别判断，股数变化不抹去仍有效的合并现金/盈利指标。该字段不回填旧修订或知识截止；来源实际取得时间仍独立记录。

股数证据覆盖边界与已知股数变动是两种情况。仅核验到报告日时，可保留`ordinary_shares_verified_through`（当地日期，inclusive）和`share_basis_evidence`；之后估值返回SHARE_BASIS_NOT_CURRENT、同权股数门失败，而仍有效的现金/盈利指标保持可用。该字段不宣称之后发生已知股份变动、不借报告义务期限扩大证据覆盖、不回填known_at；与上述已知变动exclusive时点共同限制估值。当前比亚迪真实输入采用此保守边界，尚未验证为当前股数。

### 独立股本时点输入（2026-10-06）

财务报告期末股数保留在原financials，不用后来的月报/翌日报表改写。独立`share_capital`输入固定结存日、各普通股类的已发行/库存/在外原值、原行列与同权依据；逐类校验“已发行=在外+库存”，合计只加在外数量，不再次扣库存股。估值可选择合法已知且较新的独立结存，财务指标不变；核验覆盖inclusive截止及已知变动exclusive时点仍限制估值，不能用重放或未检索到变动延长覆盖。输入与其原文/来源许可进入冻结manifest；实际数据库提交知识时间不回填。

本机深市有界准备使用常规**全日交易终场**作为既有“最终市场时点”的实现：2026现行规则§3.6盘后固定价格交易至15:30，因此10月8–13日计划会话`evaluation_as_of=15:30+08:00`、cutoff=16:30；§4.2.3定义的竞价收盘价仍形成于15:00，现有供应商参考日线未因此升级FINAL。临时休市或时段调整须在实际会话重新核对，此准备不代表已发生会话封存，也不改变港股随机CAS时点要求。[官方依据](../research/real-calendar-basis.md)与[实施证据](../review/REAL-CLOSURE-SUPPLEMENT.md)分别记录。

## 2026-10-06 参考研究计算补充

用户授权参考研究模式：真实参考日线与历史股本可在明确日期/假设下形成参考PE和估值分；未核验覆盖期内股数不变不是当前股数事实，已知股份变动必须另列情景警示。股本结存和利润期间不得晚于价格日期；无同权依据、币种不符、缺同日汇率、非正普通股TTM利润或财务失效时仍不生成PE。三年累计利润非正导致现金利润比不适用，与正TTM可算PE是两个不同口径。

已覆盖维度的参考经营分复用 `observed_quality`，按模板权重归一并同时展示加权覆盖及缺失维度；pending建议不计分。逐条件比较复用本工作区实际发布规则；总结果在经营覆盖或必需依据不足时保持PARTIAL。参考结果与日期、算法hash、规则hash和固定输入存于新研究快照，不改变正式评分、FINAL、有效股本门、封存或membership。旧快照缺少新增字段时显示“旧快照未留存”，不得用当前资料补算历史。[本轮验收和证据](../review/REFERENCE-RESEARCH-IMPLEMENTATION.md)。
