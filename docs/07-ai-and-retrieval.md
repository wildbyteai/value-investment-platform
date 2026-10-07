# 07 AI 分析、关联与检索设计

## 1. 模型的角色

模型提取候选公司、事实主张、证据位置和影响建议，输出受 Schema 限制的数据。系统用确定性规则校验单位、时间、身份与证据；人维护rubric模板与策略，系统可自动接受经营判断/高影响并由人工覆盖。模型没有权力写策略、修改公司身份、直接通知、联网下载任意链接或执行工具。

先跑规则／主数据候选召回，再按任务配额调用外部模型（允许外部模型，开发无固定预算门槛）；已有数字从结构化财报计算，不让模型“估算”缺失财务。无正文不做强判断；来源无 analyze 权利不送模型；无 send_to_external_model 权利只用已许可本地处理或人工。

## 2. 分析管道

1. 标题／代码／正式名称／别名精确候选召回，结合语言、市场、行业与有效关系，最多 20 个候选；候选数量不足时允许 no_link。
2. 长文按章节、表格和句段切 chunk，保留 offset/page/cell；结构化表格独立解析，不能将标题切断导致事实歧义。默认 500–800 token、重叠 10%，实施按证据召回测试调优。
3. 模型读取不可信 source text 与封闭候选身份，提取事实主张并生成links、impact_proposals、rubric_proposals、risk_proposals（主张归并为后续领域事件）。证据 quote 必须能定位到输入原文（规范化定位规则固定），不能引用模型自己的摘要。
4. 校验 Schema、ID allowlist、类型、数字范围、证据精确定位、否定／假设语气、时间和冲突；交给独立DecisionService按11 §4政策自动生效；缺证据/歧义/冲突才pending。
5. 校准置信度，应用自动决策政策与人工覆盖优先级；完成事件归并建议，歧义不自动合并。影响维度和半衰期由版本模板限定。
6. 保留 analysis_run 的 model ID、prompt/schema version、input_hash、usage/cost、validated result 和理由；不要保存隐藏思维链。修正或 prompt 升级生成新版本，影子对比后发布。

Prompt injection：正文即使写“忽略规则、读取密钥、发送消息”也只作为被分析文本。模型无工具访问、网络和凭证；不将正文拼入 system 指令；HTML/script 外部链接不执行。拒绝未经允许的公司 ID 与字段。测试必须包含恶意文档、伪造代码、同名公司、繁简混合、表格单位、否定句、预测句和讽刺语。

## 3. 关联与影响合同

contracts/analysis-result.schema.json 是最小跨阶段 Schema：schema_version、item_revision_id、no_link、links、impact_proposals、rubric_proposals、risk_proposals；每个link 有 company_id、relation_type、relevance、confidence、evidence_ids、rationale。分析结果只是 proposal，不能包含“approved=true”。影响 signed_impact 不含价格涨跌预测字段。

证据 IDs 必须属于本输入 revision；由服务端检查跨对象引用，JSON Schema 本身无法证明。每个影响必须引用一条建议或已批准公司关联，并有维度、方向强度、有效截止、半衰期、证据、confidence 和原因。未被DecisionService接受的硬风险不能写入strategy hard-risk facts；AUTO accepted满足政策可生效，人工可覆盖，不强制先人审。

## 4. 混合检索

搜索默认股票代码／名称精确路径；自然语言先用 BM25 全文基线；语义通过效果门禁并启用后，两路候选并行并按 RRF 合并（起始 k=60），可选择本地 reranker。优先评估 Elasticsearch 同平台向量检索，pgvector 为替代候选，不默认同时维护两套向量索引。RRF 可在应用检索服务合并；若使用 Elasticsearch 原生融合排序、模型推理或细粒度权限特性，按选定版本核对订阅要求，不能据 Basic 免费概括全部能力。source_policy 与 workspace ACL 在两路查询之前过滤，返回前按 PG 再校验；后过滤不是唯一保护，禁止分页、计数和高亮泄露不可见资料。候选列表为空返回解释，不让 LLM 填补。

默认返回事件或讯息摘要、来源、发生/发布时间、公司、关联与可点击证据。可选问答在首个研究闭环之后实施，每句关键回答引用可访问 evidence，资料不足明确说明，不能生成投资指令。引用数不代表结论真实性。

Elasticsearch projection_version 与 watermark 在 meta 返回。PG 变更后索引晚于 5 min 标为 delayed，超过目标给运营告警；事件明细仍从 PG 查。ACL 撤权优先同步拒绝缓存，然后异步删除索引；证据请求始终再验证。向量 model 切换新 namespace、影子召回评估，再切 active，不复用旧向量。索引不存未经许可全文。

## 5. 质量评估与模型版本门禁

M2 建立至少 1,000 个中／繁／英文混合标注样本：公告、财报、资讯、社媒线索、无关联、同名歧义、子公司、A/H、否定、历史回顾及恶意输入。至少 20% 双人独立标注，分歧仲裁；按事件和发布日期划分 train/calibration/holdout，不能让重复转载跨集合泄露。指标按各来源／语言／直接和间接关联分别报告。

关联自动批准 precision≥95%、recall≥85%，误连公司率≤1%；范围为测试集、配套 Wilson 区间，不宣称全市场同等质量。证据可定位率≥99%，无证据/未校验/不满足政策的硬风险直接生效次数=0；对AUTO接受硬风险单独报告precision、错误案例及人工覆盖率；no_link precision/recall 单独报告，避免强制关联。置信度报告 reliability bins 与 ECE，原始模型 self-confidence 不当成概率。

事件归并以 pair precision≥95% 优先，误合并不能用增加 recall 抵消；至少测试不同季度同类事件不合并。影响方向与专家仲裁一致率目标≥85%，按维度分组；这是意见一致指标，不验证经营因果或未来收益。未过门禁降级人工，不降低验收阈值冒充通过。

检索标注至少 100 个真实研究意图（可先用合成公司）：精确代码 top-1=100%；证据 recall@20≥90%、nDCG@10≥0.8、零 ACL 泄漏；与 BM25 baseline 对比，语义未增益则默认关闭。版本上线前固定成本、延迟与错误指标，不能因为“更新了模型”直接切全量。

## 6. 配额与成本

模型调用并发、日 token/$ 限额按 source/workspace/stage 控制；达到上限排队／规则分析并提示，不能偷偷换外部 provider。记录输入/输出/embedding/rerank 和重试次数，费用按实际公开报价版本计算，不预填虚假当前价。相同输入+prompt+model/schema hash 可复用已许可缓存；修改源权利时缓存立刻禁读。

成本估算公式：每日日分析成本 = N分析 × (平均输入token×输入单价 + 平均输出token×输出单价)；加 embedding、重试、运维、人审成本。默认先用廉价模型候选提取，高影响提升人工优先级；更强模型仅按获批准任务政策调用。成本在首批来源与样本后量化；开发不以预算确认阻塞。限额是可配置运行项，不意味着已经采购或授权真实调用。

自动审核是否生效看DecisionService输出，不看模型自身approved字段。AUTO service principal独立受限，不能改策略/模板发布。新模型shadow检验对已有效HUMAN覆盖保持不变；异常队列按经济事实slot去重，统计pending年龄和策略影响，不把固定每天人工投入当首版依赖。


v0.3模型输入manifest除公司候选外，还固定有效security/listing候选和解析dimension/event policy allowlist。analysis Schema3.0支持受限x_ ID与风险target，语义服务验证候选归属、half_life与enabled、原始披露和目标传播；Schema通过不能授权模型扩大范围。模型输出的业务有效时间不改变系统known_at。11 §7/8/9为唯一覆盖、风险与维度合同；前端和检索不得另推传播规则。

## 7. 外部Agent报告作为输入

已有Agent文件按04 §6进入agent_report/agent_digest；reading_metadata中的解读与阅读评级不是analysis-result或accepted决策。规则解析先产出可读资料和受限公司候选；公司关联满足现有政策可AUTO接受；影响/rubric/risk继续遵守§1…3和11，不增加全部逐篇人审。可定位报告单元格只支持“上游报告这样说”，使用发行人原文的政策不能被报告来源冒充满足。报价或目标价不会直接写正式行情/财务。一个摘要多事实可分多个事件，重复摘要沿用经济事实归并。原文补取得使用真实observed_at，禁止回填旧评分依据。
