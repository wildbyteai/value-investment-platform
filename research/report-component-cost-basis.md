# 需求方报告：组件许可与公开费用依据

基础设施/既有组件核查日期：**2026-10-06（客户端日期）**；Elasticsearch补充核查日期：**2026-10-07**。本附件服务于 [20 报告方案](../docs/20-stakeholder-report-design.md) 与 [组件费用表](../reports/stakeholder/components-and-costs.md)，只提供许可、价目和可复算量级示例；未选定云厂商、境外托管、数据采购或 Java 迁移，未核查账单，不代表已发生费用或正式报价。

组件采用状态依据 [19 资源清单](../docs/19-production-resources-and-configuration.md) 及本轮主会话的直接依赖/包元数据核对；重点许可与付费项目另从下列官方公开来源核实。许可证升级或引入插件时，应核对实际发行物随附的 LICENSE/NOTICE 和第三方组件条款，不能把主项目许可证套给全部依赖。

## 1. 软件许可与费用边界

“授权费 0”指遵守相应许可使用社区发行物时，无需购买该软件的使用许可证；服务器、托管、商业支持、维护与数据使用权另外计费。保留必要的版权、许可、NOTICE 和修改说明；特殊许可按具体条款履行。开源 SDK 的许可不授予其取得数据的商业使用、远程保存或再分发权利。

| 组件/适用范围 | 当前采用状态 | 许可依据 | 授权费与条件 |
|---|---|---|---|
| Python 3.12 | 现有后端运行线 | [Python 许可页](https://docs.python.org/3/license.html)：PSF License Agreement 及随附历史/第三方条款 | 使用授权费 0；不等于支持服务免费 |
| FastAPI、Pydantic、pydantic-settings、SQLAlchemy、Alembic | 现有直接后端依赖 | 本轮主会话本地包元数据：MIT；采用版本见 backend/uv.lock 和 19 | 授权费 0；保留许可/版权 |
| Uvicorn、pypdf、httpx | 现有直接后端依赖 | 本轮主会话本地包元数据：BSD-3-Clause | 授权费 0；保留声明、不以作者名背书 |
| psycopg2-binary / psycopg2 2.9.x | 现有 PostgreSQL 驱动 | [Psycopg 官方许可](https://www.psycopg.org/docs/license.html)：LGPLv3 或以后版本，含 OpenSSL 链接例外；部分 adapter/microprotocol 文件另有可选许可 | 授权费 0；**不是 MIT**，分发/修改时遵循 LGPL 与例外，不能将局部文件许可当作整体许可 |
| BaoStock、PySocks | 现有资料/网络依赖 | 本轮主会话本地包元数据只标 **BSD** | 不猜 BSD 子类；准确子类与随附条款待发行物核对。BaoStock 软件许可不等于企业数据许可 |
| pytest、jsonschema | 现有开发/验证依赖 | 本轮主会话本地包元数据：MIT | 授权费 0；测试通过情况另看验证证据 |
| React / React DOM、esbuild、@types 直接依赖、openapi-typescript | 现有前端/构建依赖 | 本轮主会话 frontend manifest/lock 元数据：MIT | 授权费 0；不包含所有传递依赖的统一结论 |
| TypeScript | 现有前端构建依赖 | 本轮主会话 frontend 元数据：Apache-2.0 | 授权费 0；保留许可及适用 NOTICE |
| uv；npm CLI | 现有依赖交付工具 | [uv 官方 README](https://github.com/astral-sh/uv/blob/main/README.md)：MIT 或 Apache-2.0 二选一；[npm CLI 官方 LICENSE](https://github.com/npm/cli/blob/latest/LICENSE)：Artistic-2.0 | 工具授权费 0；npm registry/网站服务条款与包依赖许可另算 |
| PostgreSQL；pgvector | PostgreSQL 已采用；pgvector 是待接入项 | [PostgreSQL License](https://www.postgresql.org/about/licence/)；[pgvector 官方 LICENSE](https://github.com/pgvector/pgvector/blob/master/LICENSE) 同为 PostgreSQL License | 自托管软件授权费 0；托管数据库、磁盘与备份另收费 |
| NGINX Open Source；Caddy | 反向代理候选，未部署 | [NGINX 官方许可](https://nginx.org/LICENSE)：2-Clause BSD；[Caddy 官方 LICENSE](https://github.com/caddyserver/caddy/blob/master/LICENSE)：Apache-2.0 | 社区发行物授权费 0；[NGINX Plus](https://docs.nginx.com/nginx/admin-guide/installing-nginx/installing-nginx-plus/) 需有效付费/试用订阅，正式费用待报价 |
| Redis | 设计候选，当前 Worker 不依赖它 | [Redis 官方许可](https://redis.io/legal/licenses/)：≤7.2 BSD-3-Clause；7.4.x–7.8.x RSALv2 或 SSPLv1；8+ RSALv2 / SSPLv1 / AGPLv3 三选一 | **不能笼统写“Redis 均为 BSD 免费开源”**。7.4+ 需按所选条款核对用途；RSALv2/SSPLv1 不属于 OSI 开源许可；商业/托管产品另收费，不以旧版许可代替新版评估 |
| Celery；Keycloak | 目标/候选，未作为现有服务部署 | [Celery LICENSE](https://github.com/celery/celery/blob/main/LICENSE)：BSD-3-Clause；[Keycloak LICENSE](https://github.com/keycloak/keycloak/blob/main/LICENSE.txt)：Apache-2.0 | 社区软件授权费0，节点、托管、支持另计；身份接入仍须验收 |
| Elasticsearch | 2026-10-07已确定后续全文方案、未接入 | [官方许可FAQ](https://www.elastic.co/pricing/faq/licensing)：默认发行物ELv2；部分免费源码可选AGPLv3/SSPL/ELv2 | [自托管订阅](https://www.elastic.co/subscriptions)有免费Basic，进阶能力/支持需按功能询价；云托管与运行资源另计 |
| Eclipse Temurin JDK；Spring Boot / Spring Security | Java 比较候选，未迁移 | [Temurin 官方 FAQ](https://adoptium.net/docs/faq)：GPLv2 with Classpath Exception；[Boot LICENSE](https://github.com/spring-projects/spring-boot/blob/main/LICENSE.txt)、[Security LICENSE](https://github.com/spring-projects/spring-security/blob/main/LICENSE.txt)：Apache-2.0 | Temurin 二进制免费使用；社区支持不承诺服务等级，商业支持另询价。选定兼容 JDK/框架版本后核对发行物，不把所有 JDK 厂商写成免费 |

## 2. 官方公开价目参考

以下为美元（USD），按月参考，查询于 2026-10-06；税费、支付/汇兑费、地区供应与正式合同条件以采购时为准。主机规格是资源量级示例，未做生产容量验收。

| 项目 | 官方价目/含量 | 计费条件与报告用途 | 官方来源 |
|---|---|---|---|
| DigitalOcean Basic / Regular 主机 | 8 vCPU / 16 GiB / 320 GiB SSD，6,000 GiB transfer，**$96/月** | Basic 共享 CPU，适合可接受 CPU 波动的负载；套餐按秒计费、有月上限，非专用核保证 | [Droplets 价格](https://www.digitalocean.com/pricing/droplets) |
| 较小 Basic / Regular 主机 | 4 vCPU / 8 GiB / 160 GiB SSD，5,000 GiB transfer，**$48/月** | 只作另一规格示例；不能仅凭 CPU 数推断应用/PG 分离后可满足性能 | 同上 |
| Droplet 主机备份，Basic 百分比方案 | Weekly 为主机费 **20%**；Daily 为 **30%** | $96 主机分别约 $19.20/$28.80 每月；这是主机磁盘镜像，不是数据库连续备份 | [备份价格](https://docs.digitalocean.com/products/backups/details/pricing/) |
| 备份按用量方案（另选） | 每周/每日/12小时/6小时/4小时：分别 **$0.04 / 0.03 / 0.02 / 0.015 / 0.01 每可恢复 GiB/月** | 按可恢复文件量和所选方案计费，须结合保留期计算；不能把 $0.01 当作整台主机月价。最短列示周期为4小时 | 同上 |
| Spaces Standard Storage | **$5/月**，全部 buckets 合计250 GiB存储、1,024 GiB互联网出站；超量存储 $0.02/GiB/月，出站 $0.01/GiB | 起建首 bucket 计费；同订阅共用额度，不是每 bucket 单独赠送；CDN包含但共用流量额度。公网/私网路线影响流量计费 | [Spaces 价格](https://docs.digitalocean.com/products/spaces/details/pricing/) |
| EODHD 个人套餐 | Free **$0**；EOD Historical **$19.99/月**；Fundamentals **$59.99/月**；ALL-IN-ONE **$99.99/月** | 仅个人价目量级，不是团队/商业服务报价。官网另列年付价格，不能把年付折算月价与月付价混用；调用额度按不同 API 消耗不同 calls | [EODHD 个人价格](https://eodhd.com/pricing) |
| 企业行情/财务许可、港股来源 | **待取得具体覆盖及用途报价** | 当前项目记录中 EODHD 令牌有效，但实际 market API 未包含 HK；“Global/All-World”文字不证明港交所覆盖，不能据此建议升级即可解决 | [项目已验证状态](../review/REAL-FINANCIAL-CONTINUATION.md)；[EODHD 商业入口](https://eodhd.com/pricing) |
| 域名、身份托管、额外卷/WAL、HA、外部模型、商业支持及人工 | **未选型/待报价** | 自建身份组件授权费可为0，部署和维护仍有成本；模型未选定，不编造 token 单价。无账单核查，实际已支出未知 | [19 资源准备](../docs/19-production-resources-and-configuration.md) |

以上 DigitalOcean 是可核对价目的供应商示例，**不构成厂商或托管地域选择**；资料存储/使用许可和企业托管要求仍需在真实部署时落实。

## 3. 可复算的基础设施小计

假设持续使用一台 $96/月主机、Daily 百分比备份和未超量 Spaces：

| 计算 | USD |
|---|---:|
| 主机 | 96.00/月 |
| Daily 主机备份：96 × 30% | 28.80/月 |
| Spaces 基础订阅 | 5.00/月 |
| **基础设施示例小计** | **129.80/月** |
| 按相同月费维持12个月：129.80 × 12 | **1,557.60/年** |

年度数字是**月租连续12个月的等价合计，不是包年报价**。若仅作预算换算，假设 1 USD = 7.2 CNY，则约 **934.56 元/月、11,214.72 元/年**；7.2 是预算假设，**不是实时汇率或人民币正式报价**。

小计不含域名、额外磁盘/存储/流量、数据库全备与 WAL 增量、HA、身份服务增量资源、数据许可、模型调用、商业支持、税费和人工。已包含的 Spaces 额度可用于获准对象，但不能假定所有原件、WAL 和历史备份都能放入250 GiB。任何待报价项都不能用0填补，因此 **129.80 不是系统完整运行总价**。

## 4. 备份不等于恢复目标已达成

项目目标 RPO ≤15分钟、RTO ≤4小时仍以 [19](../docs/19-production-resources-and-configuration.md) / 运维合同为准。Daily 主机镜像周期约一天；即使选择公开价目最短4小时方案，仅靠该周期也不能支持15分钟 RPO。

[DigitalOcean 官方限制](https://docs.digitalocean.com/products/backups/details/limits/)说明自动备份不含附加 Volumes，属于磁盘崩溃一致性快照，并建议活跃数据库使用应用级备份；该页同时注明备份静态未加密但不对外可访问。因此不能将订购主机备份等同于数据库一致性、数据保密配置或 PITR 已验收。

数据库需要设计并验证 **基础物理备份 + 连续 WAL 归档/PITR + 独立持久保存 + 隔离恢复**；物理基线与完整 WAL 链支持恢复到指定时点，普通 pg_dump 并不能作为 WAL 重放基线。[PostgreSQL 官方 PITR 文档](https://www.postgresql.org/docs/current/continuous-archiving.html)

15分钟目标应包含 WAL 归档/传输/持久化延迟与失败监测，RTO应包含原件、manifest、审计和撤权依据回读；须由恢复演练证据确认。此处只核对公开价目与恢复机制，未实施备份、部署或演练；满足该目标的增量资源/运维费用仍待实际方案估算。

## 5. 本次核查结果与待核实项

给定的 $48/$96 主机、$5 Spaces、20%/30% Basic 备份和 EODHD 个人月价均与本次官方页面一致。补充备份按用量分支及恢复边界；明确 Redis 的版本分界、psycopg2 的 LGPL 例外、Temurin 与商业支持差别；uv 双许可和 npm CLI Artistic-2.0 已从官方仓库核实。

待核实：BaoStock/PySocks实际发行物的BSD子类；最终采用版本及插件的完整条款；企业数据授权与真实港股覆盖；部署地域、完整恢复方案、容量、正式报价与账单。外部查询仅使用公开产品名/官方URL，未上传项目源码、需求、截图、业务资料或凭证；本次只新增本附件。

## 6. Elasticsearch 补充核查

2026-10-07使用官方网页核对：

- [许可FAQ](https://www.elastic.co/pricing/faq/licensing)：默认发行物采用ELv2，部分免费源码另有AGPLv3/SSPL/ELv2选项。源码选项不能替代默认发行物条款，也不能沿用旧候选Apache-2.0。
- [ELv2 FAQ](https://www.elastic.co/licensing/elastic-license/faq)：应用内部使用与向第三方提供搜索平台托管服务应区分，正式用途按条款核对。
- [自托管订阅](https://www.elastic.co/subscriptions)：Basic基础层免费，商业支持及进阶能力需按版本/功能询价。没有取得本项目完整订阅或云托管报价。
- [向量检索](https://www.elastic.co/docs/solutions/search/vector/dense-vector)：平台可存储向量并做相似搜索，因此pgvector保留为替代候选，不默认新增另一套向量索引。文本向量生成、融合排序/模型特性和资源成本仍分别核对。

采用依据是用户明确指定全文平台，并保留全文/语义统一平台的评估路径；未实测优于OpenSearch。搜索节点、SSD、重建及维护不包含在129.80美元/月三项参考小计。价格与许可仅依据公开产品资料，查询未发送源码、报告、截图或研究内容。当前未安装或部署Elasticsearch，中文分词、精确命中、ACL与时点过滤、搜索效果及容量按W-03实测。
