# 08 安全、运维与可靠性

## 1. 安全边界

研究资料、用户笔记、策略和订阅默认私有；公开来源也要遵守平台抓取、保存、商用与模型处理权限。平台验证码、登录、反爬和访问控制不得绕过；只接获许可 API、公开允许访问页面或用户合法提供资料。首期不采集企业机密、客户资料或真实持仓。

OIDC 验证服务端 issuer/audience/signature/expiry，首版简单RBAC，MFA作为身份服务可配置增强，不强制逐项审批。RBAC capability+workspace/owner/source ACL；五角色可兼任、组织研究默认共享、私人对象明确共享。PG RLS作为可选纵深保护，采用时必须覆盖下面的连接池测试，应用连接不使用绕过 RLS 的超级用户；后台 Worker 以作用域 service principal 访问。RLS 会话变量每事务设定，连接池复用必须清除，负面测试覆盖切 workspace。

管理员不隐式拥有策略发布、内容复核和所有私有规则读权限。证据下载签名短有效期并重新校验，非公开对象不能直接被公网索引。搜索／向量过滤、计数、缓存、日志、导出同样检查权限。

## 2. 输入及采集防护

源连接 URL 仅允许批准域名／协议；拒绝 loopback、内网、metadata endpoint，重定向和 DNS 重解析再次验证，采集 Worker egress allowlist 防 SSRF。解析隔离、最大文件／解压限制、MIME 验证、不执行宏或脚本；网页渲染器独立沙箱且无内部网络凭证。抓取超时、并发和 request budget 固定。凭证存 secret manager，数据库仅引用；日志不记 token/cookie/body/private URL。

原文转义渲染，CSP 和安全下载 headers；prompt injection 由无工具、封闭上下文和输出校验隔离。研究员证据可见≠外部模型有权接收；两项权利独立。允许外部模型正常接入；来源配置一次明确外部分析许可，避免每次调用询问。所有export任务检查当前source权利，归档文本不因历史可见自动外传。

## 3. 变更与审计

发布策略、修改源权利、批量补采、主数据合并／拆分、模型切换、权限变更、恢复和索引重建有必要的preview、expected_version、scope、reason 与审计。preview 不能授权超出人员原权限的执行。审计 append-only、应用不可 UPDATE/DELETE，独立保留备份；管理员可管权限但不能抹审计。

审计记录 object_revision、前后 hash、操作者、request/trace、时间与业务原因；敏感前后内容不入日志。删除与授权撤销留 tombstone，传播到缓存、全文、向量和恢复后数据，不把“删索引”当删源数据。

## 4. 部署与升级

开发：项目隔离 Compose、合成 fixtures、mock source/model/channel、无外部出站为默认。启动前 verify DB host/environment/data classification，不能因为 localhost 就假定可删。生产：TLS reverse proxy、API、分配额 Worker、PG、Redis、OpenSearch、S3、可观测性；数据库／索引管理端口不公网暴露。

生产 sizing 待基线压测，不建议在一个低内存节点同时承诺 OpenSearch 与 8,760 万向量。初步 PoC 可用 8–16 vCPU/32–64 GB 总资源分配且独立磁盘额度，均为估算；根据实测决定托管 PG、检索和存储。region、供应商、实际价格、备份流量与许可证上线前决定。

迁移遵循 expand→双版本兼容→验证→切换→contract，DDL / index build 评估锁影响；不能把一次数据库迁移和多个破坏性 API 改动绑一起。发布先 staging 合成或已批准脱敏数据、金丝雀、观测窗口、再全量。所有生产写入另需授权。

应用回滚到兼容版本；数据回滚先备份和影响预览，不自动 down 破坏迁移。策略 rollback 生成新 release；prompt 模型 rollback 指向旧 validated policy；索引新 alias 切换后保留旧索引有限期。版本与事件 Schema 至少支持当前与上一稳定版本，未知字段受合同版本策略约束。

## 5. 观测与健康

技术指标：队列 lag、任务 age、错误分类、重试、lease 过期、outbox 未发、PG 锁等待、索引 watermark、外部渠道投递 UNKNOWN；业务指标：源新鲜度、metadata_only 比例、未关联／待复核比例、证据缺失、coverage 分布、UNKNOWN 策略数量、入退转移率；成本指标按任务阶段与来源展示。

/health/live 只证明进程；/health/ready 验证关键依赖；/ops/pipeline/status 验证最近成功采集、分析、评分、评估与策略变化主记录；通知阶段另验投递。受保护 ops 接口不能公网泄露配置。HTTP 200 不证明研究流程可用。

严重程度：P1 跨用户泄露／数据损坏／错策略触发，立即阻止相关发送或读路径；P2 关键数据链路超过新鲜度阈值，标 UNKNOWN 并通知运营；P3 搜索或非关键源降级。运营告警限频合并，状态变化才提醒，恢复通知有受影响范围。

## 6. 恢复操作手册

| 故障 | 安全处理 | 验证与退出条件 |
|---|---|---|
| 源 429/失权 | Respect Retry-After 或暂停；不换身份绕过 | 授权确认、小样本采集、缺口补齐且 mode=backfill |
| 模型不可用 | 原文仍保存，分析排队／人工 | 按标注门禁恢复 shadow，不能一次性无界全量重跑 |
| Redis 丢队列 | ledger sweeper 重建 due 任务 | 任务最终完成，输出／转移无重复 |
| Worker 提交后宕机 | 重试读唯一业务键 | 不生成第二次 score/transition/delivery |
| 索引损坏 | PG 查询降级；固定 cutoff 重建+追增量 | 校验 count/hash 抽样/ACL、watermark 后切 alias |
| 财报或公司错配 | 冻结相关自动评估，复核并建新 revision | 影响预览、有限重算；通知纠正说明保留原通知 |
| 外部通知超时未知 | UNKNOWN_DELIVERY，查询或人工确定 | 不盲重试；变化记录保留（通知模块后续） |
| PG 故障 | 停止写与发送；从备份在隔离环境恢复 | RPO/RTO、manifest、审计、策略基线完整后恢复 |

PG 定期全备+WAL、对象受权利约束版本备份，至少按季度隔离恢复演练。恢复后按12 §7独立journal/latest watermark施加撤权再放开读取；不能从旧DB取所谓最新依据；历史任务默认 mode=replay、静默投递，不能自动给所有人补发几个月告警。演练需实测耗时和丢失窗口。

## 7. 发布阻断项

发现任何 ACL 泄露、未来数据污染历史、重复实际发送、部分失败被显示为有效结果、无出处强影响生效、无权源可抓取／分析、开发身份入口在生产可用，都阻断上线。可选功能、更多数据库或全机型测试不阻断本次已定义 slice。

开发阶段不堆复杂审批/权限系统，保留账号身份、服务端RBAC、对象隔离、凭证保护和操作追溯。对真实接入和部署的授权边界不由“权限先松后紧”自动替代；当前仅修订设计。模型缓存和派生分数也继承来源状态，撤权/更正不能只删原文链接。


v0.3覆盖/风险/封存的最小权限与恢复补齐：每次提交重新验证capability、workspace、证据ACL、risk/slot generation与worker fence；客户端actor/known_at不可信任。封存中途崩溃从已冻结manifest恢复，失权输入fail closed，双worker使用同seal slot；应用落后或新release不能回写当前membership。未知目标/维度拒绝，不能以管理员身份修正业务判断。合同版本变化仅为未运行设计，未来旧payload兼容规则见V03-CHANGELOG，不能静默扩大旧风险。
