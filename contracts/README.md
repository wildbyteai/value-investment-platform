# 合同目录

JSON Schema draft 2020-12；本阶段提供关键跨端对象的设计合同，完整 OpenAPI／物理 SQL 迁移在 M0 实施。禁止将合同存在解释为运行时已接入校验。

- [strategy.schema.json](./strategy.schema.json)：受限 all/gte/lte AST，不接受任意代码、任意字段；深度≤5、最多30个叶节点由运行时语义校验补充。
- [analysis-result.schema.json](./analysis-result.schema.json)：仅 unapproved proposal，关联与影响独立；no_link=true 时不能有 links 或影响。
- [job-event.schema.json](./job-event.schema.json)：事件只传引用与版本，不能传正文或 secret。
- [标准策略](../config/strategy-standard-v1.json) 与 [评分配置](../config/scoring-standard-v1.json)：初始数字真源；业务文档解释公式和规则含义。评分配置有scoring.schema.json，分层模板有scoring-template.schema.json，独立AUTO/HUMAN决策有review-decision.schema.json；当前材料工具检查形状、引用、权重与示例反例。
- [合成例子](../examples/analysis-proposal.json)、[任务例子](../examples/job-event.json)、[状态预期](../examples/state-machine-cases.json)：全为虚构，不含任何真实证券或业务记录。

money/ratio/score 均采用十进制字符串；semantic validator 另外检查量纲、字段匹配、enter/retain滞回、业务权限、同workspace引用与 evidence ownership。UUID/date-time 的 format 需要运行时启用验证；不能以 JSON Schema 通过代替这些业务检查。Schema 允许更改配置参数，不意味着参数经过投资效果验证。

本阶段工具用Python标准库做保守的Schema子集形状、范围与示例一致检查，并逐文件检查 JSON 语法和 Schema 本地引用；没有安装完整 JSON Schema validator，正式 draft 2020-12 validation 属于 M0 未运行项。此限制在 validation-result 中明列，不能将文档检查说成业务验收。

v0.2时strategy/job/scoring/analysis-result Schema为2.0（v0.3当前版本见下节）；analysis-result包含关联、影响、rubric与风险proposal，仍不能自我批准。模板父hash采用UTF-8、ensure_ascii=False、indent=2与末尾换行的JSON文件字节SHA-256，发布固定此canonical格式。config路径中的v1表示首套标准配置，其指标定义引用v2，不是设计v0.1。

模板层级/继承/发布和审核优先级见11，数值/时点/更正见12。shape校验不能证明身份、证据、父scope或业务权限；所有跨对象关系还需语义校验。examples中的AUTO accepted由DecisionService生成，不能直接使用模型proposal冒充accepted。


## v0.3合同升级

analysis-result/scoring为3.0、scoring-template/review-decision为2.0；strategy/job仍2.0，不因设计版本统一强制改号。旧合同字节保留在固定Git历史；未运行产品不存在生产迁移。

新增[override-command](./override-command.schema.json)、[human-judgment](./human-judgment.schema.json)、[dimension-registry](./dimension-registry.schema.json)、[evaluation-seal](./evaluation-seal.schema.json)及[完整冻结manifest](./evaluation-input-manifest.schema.json)。review-decision只引用opaque UUID修订，不携带替换值；OverrideCommand的四类judgment与HumanRevision同形，材料工具检查同步。模型风险带target/有效期；维度ID形状扩大后还须manifest白名单校验。registry/模板政策及兼容半衰期映射由语义校验保持一致，类型通过不证明业务授权。

新例子分别见examples/v03-human-replacements.json、v03-risk-targets.json、v03-template-custom.json和v03-seal-command.json；都是设计预期。v0.2探针仍绑定原commit/hash，不用当前Schema重写其观察。schema版本选择、旧风险消歧与不可回填规则见[V03-CHANGELOG](../review/V03-CHANGELOG.md)。
