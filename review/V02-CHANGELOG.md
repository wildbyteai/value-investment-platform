# v0.1 → v0.2 变更账本与证据边界

日期2026-09-30；旧基线`8b9d9de36d197b1932c4102cc98888d224984085`，本次为设计修订。用户已确认最终边界，工程代码、数据库、UI和真实接口尚未实施。旧版本由Git历史保留；当前权威入口是README与docs/11。

## 1. 用户决定

| 变更 | 原设计 | 当前设计 | 追踪 |
|---|---|---|---|
| 多人权限 | 一个私人组织，但访谈曾提出简化个人起步 | 首版五角色RBAC可兼任，前后端统一授权，不降为个人工具 | R-11/17，11 §5，T-20/29 |
| 三层模板 | 固定公司评分配置 | base→industry→company固定父版本、差异覆盖、有效配置/来源、升级预览 | R-05/15，11 §2/3，T-25/26 |
| 自动审核 | 高影响/硬风险先人工批准、人工基准 | DecisionService可AUTO接受关联/影响/rubric/硬风险，人工覆盖有效期间优先 | R-03/05/16，11 §4，T-27/28 |
| 外部模型 | 许可范围待确认 | 允许作为正常能力接入；来源配置与服务端基础权限，不堆复杂审批 | R-11/16，07/08/11 |
| 成本 | 开发和部署预算待决定 | 开发不设固定预算门，记录用量；真实供应商/资源采购后续选择 | 01/07/09 |
| 通知 | 首版站内主记录、订阅与提醒中心 | 当前生成可查策略变化与固定解释；全部收件人通知/订阅/投递归W-07后续 | R-08/09，02/05/06/09，T-13/16 |
| 技术范围 | 按小团队阶段交付 | 保留完整框架能力，分阶段只按依赖验证，不以技术复杂为由删需求 | R-13/14，09/13 |

## 2. Pro可见反馈与独立研究落实

完整Pro附件未取得，本表不宣称合并其60文件包；当前v0.2由本会话独立编写。第二轮报告保留对旧基线的研究事实，建议与当前合同冲突时以本表/11/12为准。

| 发现 | 当前修订 | 配置/合同影响 | 验收追踪 |
|---|---|---|---|
| B-01 财务/rubric | 合并CFO配合并净利润；11项0–4证据锚点 | metric-definitions-v2/rubrics/scoring Schema | T-09/10/36 |
| B-02 时间任务 | 时间相关job固定as_of/cutoff/session/版本；重试不换逻辑时点 | job-event Schema2.0/evaluation_context | T-01/08/18/35 |
| B-03 FINAL更正 | 更正窗口、历史CORRECTION、当前reconciliation分开 | correction记录/API/manifest | T-07/14/32 |
| B-04 旧备份撤权 | 旧DB外独立durable journal/latest watermark；恢复隔离 | 12 §7/08恢复合同 | T-15/19 |
| S-01 相邻session | 缺应有评估打断pending，休市不打断，旧session不倒灌 | strategy Schema2.0/FINAL token | T-13/30 |
| S-02 最终价/日历 | listing报价final标记，CAS/半日/覆盖不足/深市映射 | price/listing/calendar adapter | T-11/31 |
| S-03 输入时点分类 | 收盘价宽限可用，收盘后新公告不可入本次；判断不回填 | evaluation context与冻结manifest | T-07/38 |
| S-04 历史/当前分离 | 保留s2历史，独立s6仍合法时不抹当前IN | correction window +最新generation CAS | T-32 |
| S-05 个人暂停 | 共同membership与后续subscription分离 | 无首版个人通知开关 | T-13/16/20 |
| S-06 新鲜度 | 按报告义务/所需期，旧更正不满足新期 | 移除financial_max_announced_age_days | T-09/37 |
| S-07 人审容量 | 用户选择自动生效，因此无需固定日人审；仍统计异常pending/覆盖负担 | AUTO政策、经济事实slot队列 | T-27/28/T-UX-01 |
| S-08 数值规范 | Decimal上下文/12位存储/运算顺序/UTC秒/显示分离 | numeric-policy-v1、scoring引用 | T-08/35 |
| S-09 Listing | company/security/listing明确定义，首版primary柜台固定 | 报价/V关联listing，membership仍security | T-10/11 |

其他采纳项：economic_fact贡献slot、baseline原子吸收、原文A→B→A observation、派生分数继承来源权限、服务端笔记/草稿/保存视图、对象清理核对DB活跃引用；对应T-33/34与11/12。

## 3. 开源取舍

继续模块化单体和PG业务真源；优先FastAPI全栈模板工程基座，Refine作为管理端候选不因TanStack而排除，Prefect作为Celery替代不因既有文档而排除。实际集成在W-08有界验证，不叠加同职能引擎。Qlib/LEAN隔离研究、FinanceToolkit公式对照、Scrapy获许可HTML适配；RQAlpha/AKShare许可和数据用途仍需分别核对。固定源码和观察证据见research/second-review.md，未安装或运行。

## 4. 一致性与未验证项

R-01…14/W-01…07/T-01…24保留，追加R-15…17/W-08/T-25…38及T-UX-04。首版通知范围按用户决定调整，T-16实际发送部分后续执行，不降低状态变化与去重验收。策略/评分文件名v1保持第一套标准配置名称，Schema/指标定义独立升版本，尚无生产配置被替换。

材料检查结果见validation-result.json：JSON、有限Schema形状、引用/hash、模板/规则一致性、合成黄金算术/负例等；不能替代完整JSON Schema库验证或产品运行验收。未执行数据库迁移/并发、真实源/模型、检索标注、UI/设备/UAT、性能和备份恢复；没有收益验证。GitHub提交与回读证据留在当前Matter，不把本机路径、原始网页或凭证上传。
