# 开源框架初步候选与复用方向

核查日期：2026-09-30。此页为本次只读调研的派生判断与导航，不保存第三方原文／代码；各来源以官方链接回查。已读官方GitHub仓库元数据和README；RQAlpha另外读取当前LICENSE。不是生产选型、兼容测试或法律结论，没有安装或运行候选项目。

用户新增偏好：尽量寻找并复用成熟开源系统框架与策略框架。首期仍以完整研究流程、管理／业务两端、可维护规则和工程质量为目标，维持A股与港股范围，不新增交易执行需求。

## 1. 系统侧

| 候选与官方来源 | 初查许可证* | 观察到的能力 | 本项目可评估的复用与边界 |
|---|---|---|---|
| [FastAPI Full Stack Template](https://github.com/fastapi/full-stack-fastapi-template) · [README](https://github.com/fastapi/full-stack-fastapi-template/blob/master/README.md) | MIT | FastAPI、React、PostgreSQL、生成客户端、Playwright、pytest、Compose与CI脚手架 | 优先评估工程起点；SQLModel vs 现有SQLAlchemy、JWT vs OIDC、部署与同域结构须作显式取舍，不直接继承未经审查的权限模型 |
| [Refine Core](https://github.com/refinedev/refine) · [README](https://github.com/refinedev/refine/blob/main/README.md) | MIT（核心） | headless React CRUD、认证／权限provider、路由、网络与状态接口 | 优先评估管理端能力与复用hooks；研究业务端保持自己的任务流程与设计系统，避免和模板已有路由／数据状态体系重复 |
| [Scrapy](https://github.com/scrapy/scrapy) · [README](https://github.com/scrapy/scrapy/blob/master/README.rst) | BSD-3-Clause | 网站结构化数据提取框架 | 有采集许可时作为SourceAdapter；API源不强行走网页爬虫；系统ledger、快照与outbox仍由应用维护 |
| [Prefect](https://github.com/PrefectHQ/prefect) · [README](https://github.com/PrefectHQ/prefect/blob/main/README.md) | Apache-2.0（核心） | Python数据pipeline与工作流编排；另有Cloud服务 | 和Celery基线对照，按实际长流程/恢复需求择一；评估自托管与付费能力边界，不以编排替代领域事务和通知幂等 |

## 2. 策略、研究与数据侧

| 候选与官方来源 | 初查许可证* | 观察到的能力 | 本项目可评估的复用与边界 |
|---|---|---|---|
| [Qlib](https://github.com/microsoft/qlib) · [README](https://github.com/microsoft/qlib/blob/main/README.md) | MIT | 数据处理、研究workflow、模型、回测与评价工具 | 比较基础因子/研究接口与离线评估；机器学习、RL、自动研发不是本项目首期要求；A/H及point-in-time财务口径尚未核实 |
| [LEAN](https://github.com/QuantConnect/Lean) · [README](https://github.com/QuantConnect/Lean/blob/master/readme.md) | Apache-2.0 | 事件驱动算法研究／交易引擎 | 比较证券/基本面/筛选与回放接口，不启用实盘交易；C#核心与Python服务集成、数据成本和A/H适配待验证 |
| [RQAlpha](https://github.com/ricequant/rqalpha) · [LICENSE](https://github.com/ricequant/rqalpha/blob/master/LICENSE) · [README](https://github.com/ricequant/rqalpha/blob/master/README.rst) | 自定义限制，API为NOASSERTION | 可扩展Python回测／算法交易框架；README明确限非商业使用 | **许可未解决前不列为生产可直接复用候选**。当前LICENSE对非商业使用采用Apache2.0条件，商业使用须授权，法人／组织使用定义也受限制；不能简写为Apache2.0无限制。不会替用户联系授权方 |
| [AKShare](https://github.com/akfamily/akshare) · [README/Statement](https://github.com/akfamily/akshare/blob/main/README.md) | MIT（代码） | 财经数据接口库，README说明接口可能撤销 | 作为接口与数据结构调研候选；README声明数据仅用于学术研究，代码许可不代表上游数据商用/存储/再分发权。生产先核实具体数据来源和权利，不能承诺数据可用性 |

\*除RQAlpha读取LICENSE全文外，其余此处为GitHubAPI识别许可证及已读README，未审查完整依赖、插件、数据许可或商标；GPT Pro需回查精确tag/commit的许可文件，实施前做SBOM和许可核查。

## 3. 维护观察及证据限度

| 仓库 | 查询时默认分支 | 查询时pushed_at（UTC） | archived |
|---|---|---|---|
| fastapi/full-stack-fastapi-template | master | 2026-09-18T17:40:40Z | false |
| refinedev/refine | main | 2026-09-10T12:56:35Z | false |
| scrapy/scrapy | master | 2026-09-28T15:30:00Z | false |
| PrefectHQ/prefect | main | 2026-09-30T03:12:13Z | false |
| microsoft/qlib | main | 2026-09-22T05:57:23Z | false |
| QuantConnect/Lean | master | 2026-09-29T21:10:46Z | false |
| ricequant/rqalpha | master | 2026-09-28T03:17:24Z | false |
| akfamily/akshare | main | 2026-09-30T06:31:13Z | false |

以上仅证明当时未归档和有push记录，不能证明发布稳定、问题响应及时、安全或符合本项目SLO。未审查完整release/issue/security历史、代码接口、真实市场数据、point-in-time输入或端到端集成。候选发现不是PoC通过。

## 4. 下一步选型合同

先以v0.1最少依赖方案为对照，比较“直接复用/适配器复用/只参考/不采用”。系统优先评估全栈模板与管理端hooks，策略框架优先评估离线研究或基础指标适配，不成为实时状态第二真源。核心公司身份、双时间、事件去重、证据、人工版本、质量门、策略状态和通知事务仍需明确领域设计；框架不能自动提供这些正确性。

最终矩阵必须记录revision、来源、许可证、维护证据、自托管/收费边界、A/H与单位/币种/股本/TTM/修订语义、集成与替换成本、最小验证以及R/W/T影响。推荐后由用户确定实施范围；本次不fork、安装、导入第三方代码或切换运行架构。
