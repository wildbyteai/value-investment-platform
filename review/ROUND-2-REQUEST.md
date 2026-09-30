# 第二轮GPT Pro评审请求

项目已独立管理，迁移前后v0.2业务合同未变。迁移后的冻结基线是`1b16f381a8742b910cdaa8ba5b928a32857a5b69`。当前review目录包含本轮Codex报告和探针，报告不是已采纳的新合同。

实际输入请以发起消息指定的完整commit为准；未指定则先读取main一次并解析完整SHA，随后所有文件固定该SHA，不混版本。无需附件或本机路径。

1. 读取PROJECT/README、[ROUND-2-REVIEW.md](./ROUND-2-REVIEW.md)、[ROUND-2-PROBES.json](./ROUND-2-PROBES.json)，再按[GPT-PRO-PROMPT.md](./GPT-PRO-PROMPT.md)完整读取设计原文。
2. 独立判断F01/F02是否真实影响人工编辑与风险传播；F03/F04是否需要policy/dimension注册合同；F05要尊重docs/04已有cutoff≤generated_at，不能误报当前允许提前封存。
3. 对每项给accepted/rejected/modified/deferred及证据、理由和修订内容；新发现另编号。继续完整检查金融口径、状态、权限、恢复、UX与开源复用，不限于五项。
4. 保留docs/11已确认需求。输出完整v0.3主文、改动合同/配置/示例、实施任务书和追踪账本，全部在对话正文交付。不得只提供附件、虚构下载链接或声称文件已入仓库。
5. 评审可给具体方案，不修改GitHub、不运行真实模型/来源、不部署或通知。不可读私有仓库时诚实说明缺失读取范围，不要求公开仓库或传Token。

本请求准备完成不代表GPT Pro已运行。外部评审完成后由本项目归档其实际正文/来源，先复核再采纳设计，不把建议当用户确认或产品验收。
