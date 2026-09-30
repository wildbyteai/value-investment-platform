# 合同目录

JSON Schema draft 2020-12；本阶段提供关键跨端对象的设计合同，完整 OpenAPI／物理 SQL 迁移在 M0 实施。禁止将合同存在解释为运行时已接入校验。

- [strategy.schema.json](./strategy.schema.json)：受限 all/gte/lte AST，不接受任意代码、任意字段；深度≤5、最多30个叶节点由运行时语义校验补充。
- [analysis-result.schema.json](./analysis-result.schema.json)：仅 unapproved proposal，关联与影响独立；no_link=true 时不能有 links 或影响。
- [job-event.schema.json](./job-event.schema.json)：事件只传引用与版本，不能传正文或 secret。
- [标准策略](../config/strategy-standard-v1.json) 与 [评分配置](../config/scoring-standard-v1.json)：初始数字真源；业务文档解释公式和规则含义。评分配置有scoring.schema.json，分层模板有scoring-template.schema.json，独立AUTO/HUMAN决策有review-decision.schema.json；当前材料工具检查形状、引用、权重与示例反例。
- [合成例子](../examples/analysis-proposal.json)、[任务例子](../examples/job-event.json)、[状态预期](../examples/state-machine-cases.json)：全为虚构，不含任何真实证券或业务记录。

money/ratio/score 均采用十进制字符串；semantic validator 另外检查量纲、字段匹配、enter/retain滞回、业务权限、同workspace引用与 evidence ownership。UUID/date-time 的 format 需要运行时启用验证；不能以 JSON Schema 通过代替这些业务检查。Schema 允许更改配置参数，不意味着参数经过投资效果验证。

本阶段工具用Python标准库做保守的Schema子集形状、范围与示例一致检查，并逐文件检查 JSON 语法和 Schema 本地引用；没有安装完整 JSON Schema validator，正式 draft 2020-12 validation 属于 M0 未运行项。此限制在 validation-result 中明列，不能将文档检查说成业务验收。

当前strategy/job/scoring/analysis-result Schema为2.0；analysis-result包含关联、影响、rubric与风险proposal，仍不能自我批准。模板父hash采用UTF-8、ensure_ascii=False、indent=2与末尾换行的JSON文件字节SHA-256，发布固定此canonical格式。config路径中的v1表示首套标准配置，其指标定义引用v2，不是设计v0.1。

模板层级/继承/发布和审核优先级见11，数值/时点/更正见12。shape校验不能证明身份、证据、父scope或业务权限；所有跨对象关系还需语义校验。examples中的AUTO accepted由DecisionService生成，不能直接使用模型proposal冒充accepted。
