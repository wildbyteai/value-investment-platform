# ADR 0012：资讯采集定时器与 Skill

- 状态：已实现（designed / implemented / verified 分开记录见文末）
- 日期：2026-10-08

## 背景

资讯层（第 1 层）此前的输入是：人工跑定时器、把网页内容整理成每日 Excel 上传，或登记 RSS。用户希望系统自己接管这件事，形式类似各类 Agent 的定时任务：填写提示词、选择已配置的模型，到点执行。另外希望能维护可复用的 Skill（执行流程），定时器可以选择 Skill，让大模型按 Skill 的流程执行。

用户明确要求：**联网用模型厂商自带的搜索**，不另外接搜索服务，避免再维护一套搜索 Key 和费用。

## 决定

1. **模型配置增加“联网方式”**（`llm_provider.search_mode`），四种取值，均使用对话同一个 Key：
   - `qwen_enable_search`：通义千问 OpenAI 兼容接口 `enable_search: true` + `search_options`（默认 `forced_search: true`、`search_strategy: max`）。
   - `zhipu_web_search`：智谱 GLM 对话接口 `tools: [{"type":"web_search", ...}]`（默认 `search_pro`、近一天）。
   - `kimi_search`：Kimi 的 `$web_search` 内置工具官方预计 2026-10-20 下线，因此不用它；改为向模型声明一个 `web_search` 函数，模型发起调用时平台用同一个 Key 请求 Kimi 官方 `POST /v1/tools/search_pro`，把结果回传给模型，最多 `max_tool_rounds` 轮。
   - `openai_web_search`：OpenAI Responses 接口 `POST /v1/responses` 的托管 `web_search` 工具（`tool_choice: required`，确保每次都搜），默认模型 `gpt-6-luna`，推理等级 `max`（`reasoning.effort`，可在模型的 options.reasoning_effort 覆盖），单次请求超时 900 秒。国内服务器需能访问 api.openai.com，或在“接口地址”填可用的代理地址。
   - `none`：不联网（DeepSeek 等；DeepSeek 官方 API 目前没有联网搜索）。采集定时器不能选不联网的模型。
2. **Skill**（`agent_skill`）：名称、说明、执行流程（Markdown）、启用状态、版本号。修改流程正文版本 +1；每次执行记录用的是哪个 Skill 的哪一版。被定时器引用的 Skill 不能删除。
3. **采集定时器**（`collector_task`）：名称、提示词、模型、可选 Skill、周期（每天定时可多个时间并可选星期，或固定间隔，不少于 60 分钟），时区 Asia/Shanghai。每个定时器自动拥有一个 `kind=agent` 的资讯源，采到的条目可追溯到定时器。
4. **执行**：系统提示词 = 输出契约（只收真实、带原文链接的资讯，严格 JSON）+ 当前北京时间 + Skill 流程；用户消息 = 定时器提示词。结果解析为与 Excel/RSS 相同的记录，走现有的去重 → 事件 → AI/规则关联打分 → 人工确认流程，不新增旁路。失败（未配密钥、HTTP 错误、非 JSON）记在执行记录和定时器状态上，不抛出。
5. **调度**：服务器 cron 每 5 分钟执行 `python -m app.jobs collect`。到期的定时器用 `FOR UPDATE SKIP LOCKED` 领取，先把下次执行时间往后推再调用模型，重叠的调度不会重复执行。“立即执行”不改变计划时间。
6. **数字只在配置**：`config/news-collector-v1.json`（条数上限、工具轮数、超时、最小间隔、各厂商搜索参数、预设）。

## 不做

- 不接第三方搜索服务（Tavily、博查等）。
- 不在进程内常驻调度器（与现有 `app.jobs` cron 方式一致）。
- 采集结果不自动确认公司关联，仍需人工确认。

## 记录

- designed：本 ADR。
- implemented：`backend/app/domains/news/{agent,collector,collector_policy}.py`、`backend/app/api/collectors.py`、迁移 `0013_collectors_skills`、前端 后台设置 › 采集定时器 / Skill、模型配置的联网方式。
- verified：`tests/test_r7_collectors.py`（四种厂商联网请求格式、Kimi 工具循环与同 Key、调度时区与领取一次、执行入库与打分、失败记录、权限）；全量后端测试与前端构建在 CI 通过。**未用真实厂商 Key 做线上联调**，上线后先用“立即执行”试跑一次。

## 补充（2026-10-09）：预置采集任务包

用户原来在 workbubby（3 个）和豆包（5 个）里各跑一套每日资讯定时任务，产出是本机 Excel 文件和飞书消息。现在把它们收进本系统的采集定时器，作为一个可一键导入的预置包，结果直接进入资讯雷达。

**合并（8 → 6）**

| 新定时器 | 由哪些旧任务合并 | 条数 | 北京时间 |
|---|---|---|---|
| 全球政策要闻 | workbubby「全球政策与实政要闻」+ 豆包「全球要闻每日采集」（重复，取两者之长） | ≤5，按重要性；没有重要的就返回空 | 06:00 |
| AI·芯片·存储行业动态 | workbubby「AI行业动态」+ 豆包「AI科技行业每日动态推送」（重复；去掉飞书推送） | ≤5 | 06:10 |
| 创新药每日动态 | 豆包「创新药每日动态推送」（摘要须含 mOS/HR/P/ORR 等关键数据） | ≤5 | 06:20 |
| 重点创新药公司动态 | workbubby「重点创新药公司每日高价值公告监控」（保留收录/剔除规则；没有动态的公司不出条目） | 不限（受全局上限） | 06:30 |
| 新消费新娱乐趋势 | 豆包「新消费新娱乐趋势」 | 5–8 | 06:40 |
| 企业家访谈 | 豆包「企业家访谈」（价值评级写进 note，如“价值：★★★★ 理由”） | ≤8 | 06:50 |

**决定**

1. 内容全部在 `config/collector-presets-v1.json`：一个共用 Skill（`daily-news-common`「每日资讯采集通用规则」：只看过去 24 小时、一手权威来源优先、不收传闻、不编造、必须有可访问原文链接、中文自写摘要、同事去重、宁缺毋滥）+ 6 个定时器（名称、提示词、周期）。每个提示词只保留自己的范围、筛选、条数和字段说明（company / category / note 的用法）。
2. 旧提示词里的 Excel/openpyxl/pandas 生成、`D:\股票投资` 路径、文件命名、“执行完成后汇报”、lark-cli/飞书推送全部删除；存储、去重、公司关联和影响分由系统现有流程完成。
3. 重点公司名单写在提示词里，管理员可在页面上直接改。旧提示词写“四家”但列了 7 家，已改为 7 家；英矽智能港股代码改为 03696.HK（旧的 02585 是错的）；百济神州已更名 BeOne Medicines，美股代码 ONC（2025-01-02 起，原 BGNE）。劲方医药 02595.HK、信达生物 01801.HK、中国生物制药 01177.HK、翰森制药 03692.HK、诺诚健华 688428.SH / 09969.HK、百济神州 688235.SH / 06160.HK 核对无误。
4. 导入是幂等的：Skill 按 `skill_key`、定时器按名称在本工作区查，已存在就跳过，不覆盖管理员改过的内容；新建走现有 `save_skill` / `save_task`（同样校验周期、只接受能联网的模型、写审计），另记一条 `admin.collector.presets_installed` 审计。
5. 入口：后台设置 › 采集定时器 顶部“导入预置采集任务”（选能联网的模型、勾选、导入，显示 已导入 / 未导入）；接口 `GET /api/admin/collectors/presets`（分页）和 `POST /api/admin/collectors/presets/install {provider_id, keys?}`（权限 `source.manage` 或 `system.configure`）；服务器上 `python -m app.admin_cli install-collector-presets --workspace <工作区> --provider <模型 id 或标识>`。

**记录**

- designed：本节。
- implemented：`config/collector-presets-v1.json`、`backend/app/domains/news/collector_presets.py`、`backend/app/api/collectors.py`（两个预置接口）、`backend/app/admin_cli.py`（`install-collector-presets`）、前端 `pages/settings.tsx` 的导入面板；OpenAPI 与 `api-schema.ts` 重新生成，`backend/static` 重新构建。
- verified：`tests/test_r7_collector_presets.py`（配置合法、6 个周期都过 `validate_schedule` 且错开在 06:00–06:50、提示词不含本机路径/Excel/飞书/lark-cli、公司代码、权限 403、拒绝不联网或不存在的模型与未知 key 且不落库、分批导入与重复导入幂等、审计、Skill 进入系统提示词、命令行导入）；本机隔离 PostgreSQL 全量后端测试与前端构建通过，CI 结果见对应 PR。**未用真实厂商 Key 实际跑过这 6 个提示词**，导入后建议先对每个定时器点一次“立即执行”，看执行记录里的模型原始输出再调整提示词。页面未在浏览器里截图检查（本机无可用浏览器），只做了类型检查与构建。

## 补充（2026-10-09）：模型可按场景配置

见 ADR 0015：定时器的“模型”改为可选，不选则跟随场景“资讯采集”（后台设置 › 模型配置 › 按场景配置模型）；导入预置包也可以不指定模型。定时器单独选的模型仍优先。

## 补充（2026-10-09）：Claude 与豆包的联网方式

- `anthropic_web_search`：Claude 用 Anthropic 原生 Messages 接口 `POST {base_url}/messages`（预设 base_url `https://api.anthropic.com/v1`），请求头 `x-api-key` + `anthropic-version: 2023-06-01`，工具 `{"type": "web_search_20260318", "name": "web_search", "max_uses": 8, "allowed_callers": ["direct"]}`（搜索由 Anthropic 服务端执行；`allowed_callers: ["direct"]` 关闭“动态过滤”，输出只有文字/搜索块，更可预测，去掉即启用），`max_tokens` 16000，超时 600 秒。`stop_reason: pause_turn` 时把已返回内容作为 assistant 消息原样回传继续（最多 `max_tool_rounds` 轮）；答案取最后一个工具块之后的文字（之前的“我先搜一下”丢弃），搜索词记入执行记录。Key 只放在 `x-api-key` 头，不进 URL、日志或错误信息。
- `doubao_web_search`：火山方舟 Responses 接口 `POST {base_url}/responses`（`https://ark.cn-beijing.volces.com/api/v3`），工具 `{"type": "web_search", "sources": ["doubao"]}`（豆包搜索 Custom 版，需先在方舟控制台开通），`max_tool_calls` 10；请求与响应同 OpenAI Responses，复用 `openai_web_search` 的解析代码（系统提示放在 input 的 system 消息里，不用 instructions；不发 tool_choice / reasoning）。
- Gemini（OpenAI 兼容接口）、DeepSeek、MiniMax 的兼容接口不带联网搜索，预设为 `none`，只能用于“资讯研判打分”等不联网场景。
- 配置：`config/news-collector-v1.json` `search_modes`；预设见 ADR 0015 补充。

**记录**：designed 本节；implemented `backend/app/domains/news/agent.py`（`_anthropic_messages`、`_openai_responses` 按模式取配置）、`config/news-collector-v1.json`；verified `tests/test_r9_model_presets.py`（模拟传输：路径、请求头、工具定义、pause_turn 续传、答案截取、401 错误不含 Key、白名单外地址不发请求；豆包请求形状与解析）。**未用真实厂商 Key 联调。**
