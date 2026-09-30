# 合同目录

JSON Schema draft 2020-12；本阶段提供关键跨端对象的设计合同，完整 OpenAPI／物理 SQL 迁移在 M0 实施。禁止将合同存在解释为运行时已接入校验。

- [strategy.schema.json](./strategy.schema.json)：受限 all/gte/lte AST，不接受任意代码、任意字段；深度≤5、最多30个叶节点由运行时语义校验补充。
- [analysis-result.schema.json](./analysis-result.schema.json)：仅 unapproved proposal，关联与影响独立；no_link=true 时不能有 links 或影响。
- [job-event.schema.json](./job-event.schema.json)：事件只传引用与版本，不能传正文或 secret。
- [标准策略](../config/strategy-standard-v1.json) 与 [评分配置](../config/scoring-standard-v1.json)：初始数字真源；业务文档解释公式和规则含义。评分配置暂未提供完整 Schema，在 M0 同源 DTO 完成，当前材料工具核对其权重与基本数学条件。
- [合成例子](../examples/analysis-proposal.json)、[任务例子](../examples/job-event.json)、[状态预期](../examples/state-machine-cases.json)：全为虚构，不含任何真实证券或业务记录。

money/ratio/score 均采用十进制字符串；semantic validator 另外检查量纲、字段匹配、enter/retain滞回、业务权限、同workspace引用与 evidence ownership。UUID/date-time 的 format 需要运行时启用验证；不能以 JSON Schema 通过代替这些业务检查。Schema 允许更改配置参数，不意味着参数经过投资效果验证。

本阶段工具用 Python 标准库做有限的合同形状、范围与示例一致检查，并逐文件检查 JSON 语法和 Schema 本地引用；没有安装完整 JSON Schema validator，正式 draft 2020-12 validation 属于 M0 未运行项。此限制在 validation-result 中明列，不能将文档检查说成业务验收。
