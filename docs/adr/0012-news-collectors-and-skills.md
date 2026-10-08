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
   - `openai_web_search`：OpenAI Responses 接口 `POST /v1/responses` 的托管 `web_search` 工具（`tool_choice: required`，确保每次都搜），默认模型 `gpt-5.5`。国内服务器需能访问 api.openai.com，或在“接口地址”填可用的代理地址。
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
