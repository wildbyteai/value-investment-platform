# ADR 0016：资讯→公司两段式匹配（识别全部公司 + 按关注列表确定性匹配）

- 状态：已采纳（2026-10-09，用户要求“按推荐方案执行、不再逐项询问”；R10a 落地地基）
- 相关：ADR 0008（资讯雷达）、ADR 0012（采集定时器）、ADR 0015（按场景配置模型）、[docs/24](../24-news-company-matching.md)
- 部分取代：ADR 0015 A.1“只登记今天确有调用代码的场景”（见决定 6）；场景 `news_analysis` 改名 `news_extract`

## 背景

见 docs/24 §1：原打分把整份公司名单交给模型挑，关注列表一改历史资讯无法重配；名单外公司被丢弃；别名、港股前导零、`-B` 后缀靠模型；采集与研判的模型、推理强度不能分开配。

## 决定

1. **两段式**：第一段（场景 `news_extract`，LLM）抽取事件里**全部**公司 → `news_mention`；失败退回规则抽取 `rule:v1`。第二段（确定性，无 LLM）归一化后在 `company_alias` ∩ 本工作区 active `watch_company` 中查找：代码 → 别名全等 → 别名包含（≥3 字）；从不模糊；同一步多家命中视为歧义不关联。命中写 `news_event_company`（proposed + `mention_id/match_method/rule_version`）。**confirmed / rejected 永不覆盖。**
2. **关注列表按工作区**（`watch_company`），公司档案仍全局。迁移把现有全部公司设为每个用过资讯雷达的工作区的 active 关注（无则最早的工作区），行为不变。
3. **归一化规则只有一份**（`domains/news/matching/normalize.py`，`norm:v1`），迁移种子、别名维护、提及入库、匹配都用它；规则见 docs/24 §3。裸 4 位数字按港股、6 位 4/8/92 开头按北交所——规格只写了 5 位=HK 与 6/0/3 开头，这两条是补充（港股常写 4 位如 0700；北交所代码确定）。名称会去掉所有括号限定语（如“（苏州）”），中文旁不保留空格。
4. **重新匹配 / 重新研判**为 `match_job` 后台任务（R11）。rematch 只跑第二段、不调模型；不再命中的 proposed 关联保留不删（避免抹掉正在复核的项，下一次研判会刷新）。reassess 需新权限 `news.reassess`（数据管理员、系统管理员），执行前预估调用次数。
5. **新权限**：`watchlist.manage`（研究员、策略负责人、数据管理员、系统管理员）、`news.reassess`；系统管理员仍全权限。读接口沿用 `research.read`——规格中的 `news.read` 在本系统不存在，资讯雷达读接口一直用 `research.read`，不另造一个等价权限。
6. **场景配置扩展**：`config/model-scenes-v1.json` 每个场景增加 `recommended`（preset、model、reasoning_effort、why，第一项为首选）、`cost_note`、`status`（active | planned）与 `planned_in`、`aliases`。新增 `news_reassess`（R11）、`company_digest`（R12）、`zone_review`（R13）三个 **planned** 场景：接口与推荐先定，调用代码在对应 PR 落地；测试只要求 active 场景的代码位置存在、planned 场景写明 `planned_in`。这放宽了 ADR 0015 A.1，理由是 4 个并行 PR 需要稳定的场景键与绑定数据。
7. **场景改名**：`news_analysis` → `news_extract`（“资讯识别与研判”）。旧键作为别名：`model_scenes.canonical_key` / `scene()` / `resolve()` / PUT 都接受旧键并换成新键；迁移把已有绑定改名，回退改回。`model_scenes.NEWS_ANALYSIS` 常量保留并等于 `NEWS_EXTRACT`。
8. **推理强度**：`llm_scene_binding.reasoning_effort`（空 = 推荐）。取用顺序：场景绑定强度（只对绑定的那个模型；定时器单独选的模型不套用）→ 模型 `options.reasoning_effort`（旧配置兼容）→ 场景对该模型名的推荐，其次同厂商的第一条推荐 → 不发送。允许值按预设登记在 `model-presets-v1.json`（`reasoning_efforts`、`model_reasoning_efforts`、`reasoning_style`），模型按 `base_url` 主机对应预设；未登记的厂商一律不发送。映射在 `domains/news/reasoning.py`（OpenAI 原样；DeepSeek medium→high、xhigh→max、none→`thinking: disabled`）。不被允许的强度在请求时丢弃（换模型后旧绑定不会把调用弄坏）；PUT 时则严格校验，设置强度必须同时指定模型（`provider_id` 非空列，默认模型时用推荐）。
9. **采集默认强度**：`openai_web_search` 去掉配置里的 `reasoning_effort: max`，改为跟随 `news_collect`（推荐 high）。经代理地址（主机不对应任何预设）调用 OpenAI Responses 时，强度原样透传，与以前一致。
10. **预设**：DeepSeek 预设模型改为 `deepseek-flash`（官方名，即 DeepSeek-V4.1-Flash；Pro 为 `deepseek-v4-pro`）；内置默认模型（`news-radar-v1.json default_llm_provider`）同步从 `deepseek-chat` 改为 `deepseek-flash`——当前官方模型表已没有 `deepseek-chat`。OpenAI 预设仍为 gpt-6-luna。
11. **接口先行**：R10a 定义全部新路由与 Pydantic Schema；未实现的路由在权限检查之后返回 **501**，统一错误体 `code: not_implemented`（`app.core.errors.NotImplementedYet`，CODES 增加 501）。另加了规格未列、R11 需要的 `POST /api/news/match-jobs/{id}/cancel`。
12. **采集任务范围**：`collector_task.scope_kind/target_company_ids/industry`。R10a 已能保存与校验（targeted 至少一个存在的公司）；字段不传表示保持原值，旧页面编辑不会把定向任务改回 general。目标公司作为识别提示在 R11 生效。
13. 迁移数据步骤导入 `app.domains.news.matching.normalize`：以后改归一化规则时，旧迁移重放会得到新规则的结果——这是期望的（别名要与当前规则一致），改规则时另需重算别名 + rematch。
14. `score_events` 在 R10a 行为不变（仍是 `propose_links`），只是场景改为 `news_extract`（带推荐强度）并同步写 `extract_status`；R10b 用两段式管线替换其内部、保留函数名。

## 不做

- 不做模糊匹配（编辑距离、拼音、向量）；漏配靠别名与“建议关注”补。
- 第二段不调模型；不让模型直接给 company_id。
- 不自动确认关联；人工确认流程不变。

## 后果

- 关注列表/别名变化后，历史资讯可秒级重配；名单外公司可统计并一键关注。
- 多一份需要维护的别名表；种子只覆盖 7 家重点公司，其余公司起步只有正式名与代码。
- 场景表多了 3 个 planned 场景，模型配置页会显示它们（可以先绑定模型，调用代码上线后生效）。

## 记录

- designed：本 ADR、docs/24（2026-10-09）。
- implemented（R10a）：迁移 `0016_news_company_matching`；`app/models/news.py`（WatchCompany、CompanyAlias、NewsMention、MatchJob 与新列）；`config/company-aliases-v1.json`、`config/news-matching-v1.json`、`config/model-scenes-v1.json`（v2）、`config/model-presets-v1.json`、`config/news-collector-v1.json`、`config/news-radar-v1.json`、`config/roles-standard-v1.json`；`domains/news/matching/normalize.py`（实现）与 `extract/resolve/watchlist/suggest/stream/jobs.py`（签名占位）；`domains/news/reasoning.py`、`model_scenes.py`、`llm.py`、`agent.py`、`collector.py`、`service.py`；`api/matching.py`、`api/admin.py`、`api/collectors.py`、`core/errors.py`；OpenAPI 与 `frontend/src/api-schema.ts` 重新生成（前端源码未改，`backend/static` 构建无变化）。
- verified（R10a）：`tests/test_r10_matching_normalize.py`（名称/代码归一化、正文代码识别、别名种子配置自洽）、`tests/test_r10_foundation.py`（强度允许值与厂商映射、请求体、优先级、场景推荐合法性、场景接口的强度校验/别名键/审计/实际请求、16 条契约路由的 403/401/501、reassess 权限、OpenAPI Schema 与契约文件一致、采集范围字段、占位接口签名）、`tests/test_migrations.py::test_0016_news_company_matching_data_migration`（数据迁移、回退、再升级无漂移）；已有测试按改名/默认模型更新。本机隔离 PostgreSQL 16 全量后端测试通过，前端类型检查与构建通过；CI 结果见 PR。**未用真实厂商 Key 联调。**
