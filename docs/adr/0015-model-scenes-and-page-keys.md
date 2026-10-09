# ADR 0015：按场景配置模型；API Key 可在页面填写并加密入库

- 状态：已采纳（用户 2026-10-09 决定，两项同时要求）
- 取代：ADR 0013 第 3 条中“模型密钥只能由后台按环境变量名引用、不进数据库”的部分（出站域名白名单不变，继续强制）
- 相关：ADR 0012（采集定时器）、ADR 0013（部署与登录）、docs/22 §4、docs/23 §7

## 背景

1. 系统里有两处调用大模型：采集定时器（联网搜索，需要能联网的模型）和资讯研判打分（关联公司、关联度、影响分）。此前两处都只能用“工作区默认模型”或每个定时器各自选模型，无法分别指定，例如采集用通义联网、打分用 DeepSeek。
2. 模型 Key 只能写在服务器 `deploy/secrets/app.env` 里，每换一个 Key 都要登录服务器改文件并重启。用户希望在页面上直接填写。

## 决定

### A. 按场景配置模型

1. 场景定义在 `config/model-scenes-v1.json`（key、中文名、说明、`requires_search`、对应代码位置）。**只登记今天确有调用代码的场景**：

   | key | 中文名 | 需联网 | 代码 |
   |---|---|---|---|
   | `news_collect` | 资讯采集 | 是 | `domains/news/collector.py` `run_task` → `agent.chat` |
   | `news_analysis` | 资讯研判打分 | 否 | `domains/news/service.py` `score_events` → `llm.propose_links`（导入后、采集后、“AI 打分”、`app.jobs news`） |

   “公司分析 / 研究判断起草”目前没有调用模型的代码（`judgment_authoring` 等是规则与人工流程），**不登记**；以后有代码时再加一行配置。
2. 新表 `llm_scene_binding`（迁移 `0015_model_scenes_keys`）：每个工作区每个场景至多一行，指向一个 `llm_provider`。没有行 = 使用默认模型。
3. 取用顺序：**场景绑定的模型（启用中）→ 工作区默认模型（is_default 优先，再按添加先后）→ 内置默认（config 的 default_llm_provider，环境变量密钥）**。绑定的模型被停用时自动退回默认，页面显示原因。
4. 采集定时器：定时器自己选的模型仍是覆盖；**不选则跟随 `news_collect` 场景**。保存不选模型的定时器、导入预置包时，要求场景当前生效的模型能联网，否则 422 并提示去设置场景。执行时若跟随的模型不能联网，记一次失败（不抛出）。
5. `requires_search` 的场景只能绑定 `search_mode != none` 的模型；正在被场景使用的模型不能在表单里停用，也不能把需联网场景用着的模型改成不联网。
6. 接口：`GET / PUT /api/admin/model-scenes`（权限 `model.configure`；PUT 整体替换，未列出的场景改回默认），写审计 `admin.model_scene.saved`（含变更前后）。页面：后台设置 › 模型配置 顶部“按场景配置模型”，每个场景一行：选模型（含“使用默认模型”）、当前生效的模型与来源、Key 是否可用。
7. 预置采集任务导入（页面面板、`POST /api/admin/collectors/presets/install`、`admin_cli install-collector-presets`）的模型改为可选：不填则新建的定时器不单独选模型、跟随场景；`--provider` 仍可单独指定。

### B. API Key 在页面填写，加密入库

1. `llm_provider` 加 `api_key_ciphertext`（可空，密文）与 `api_key_hint`（末 4 位），`api_key_env` 改为可空（同一迁移）。
2. 加密：AES-256-GCM（`cryptography`，已作为后端直接依赖写入 pyproject/uv.lock），每次随机 12 字节 nonce，关联数据 `llm_provider:<行 id>`（密文复制到别的行解不开）。服务器主密钥 `VIP_SECRET_KEY`（32 字节随机数 base64，`openssl rand -base64 32`）只在环境变量。代码：`app/core/secret_box.py`。
3. 只写不读：接口永不返回 Key，只返回 `key_source`（`page` / `env` / `none`）、`key_saved`、`key_hint`（`••••` + 末 4 位）、`key_problem`。OpenAPI 中 `api_key` 为 `format: password`、`writeOnly`，无示例。审计只记 `api_key_replaced: true/false`；执行记录、错误信息、日志不含 Key。
4. 优先级：**页面保存的 Key > 环境变量 `api_key_env`**；环境变量路径保留。保存的 Key 解不开（主密钥缺失或被换）时退回环境变量，页面显示原因。
5. 未设置 `VIP_SECRET_KEY`：在页面保存 Key 返回 422“系统未配置 VIP_SECRET_KEY（服务器主密钥），不能在页面保存 API Key……”，环境变量 Key 照常可用。
6. 出站白名单（ADR 0013 第 3 条）对页面 Key 同样生效：接口地址必须 https 且域名在白名单，每次取 Key 时再校验；**已保存 Key 的模型更换接口域名必须重新填写 Key**。`VIP_SECRET*` 加入禁止作为模型密钥变量名的前缀，防止把主密钥发给厂商。
7. 页面：表单“API Key（保存后不再显示）”密码框（留空 = 不修改）、“密钥环境变量（可选）”；列表行“清除已保存的 Key”（危险按钮，二次确认，`DELETE /api/admin/llm-providers/{id}/api-key`，审计 `admin.llm_provider.key_cleared`）。
8. 主密钥轮换：旧值移到 `VIP_SECRET_KEY_PREVIOUS`、设置新 `VIP_SECRET_KEY`、重启，执行 `python -m app.admin_cli rotate-secret-key`（任何一个 Key 解不开则整体不改），确认后删除 `_PREVIOUS`。

## 后果

- 数据库备份单独泄露解不开模型 Key；但**恢复数据库时必须同时保有 `VIP_SECRET_KEY`**，否则页面保存的 Key 需要重新填写（docs/22 §4、§5）。
- 能拿到运行中服务器环境变量的人仍可解密全部 Key——与此前环境变量方案的暴露面相同。
- 迁移回退（downgrade 到 0014）会丢弃页面保存的 Key 与场景绑定；只有页面 Key 的模型被写上占位变量名 `VIP_UNSET_API_KEY`，之后报“未配置模型密钥”。

## 记录

- designed：本 ADR（2026-10-09）。
- implemented：`config/model-scenes-v1.json`、`backend/app/core/secret_box.py`、`backend/app/domains/news/model_scenes.py`、`llm.py`（ProviderConfig 的 Key 来源与优先级）、`service.py` / `collector.py` / `collector_presets.py`（按场景取模型）、`backend/app/api/admin.py`（模型 Key 只写、清除 Key、场景接口）、`backend/app/api/collectors.py`（模型可选、options 带场景）、`backend/app/admin_cli.py`（`--provider` 可选、`rotate-secret-key`）、迁移 `0015_model_scenes_and_page_keys.py`、前端 `pages/settings.tsx`（按场景配置模型、Key 输入与清除、定时器/预置导入“跟随场景”）；OpenAPI 与 `api-schema.ts` 重新生成，`backend/static` 重新构建；`deploy/secrets-example/app.env` 增加 `VIP_SECRET_KEY`。
- verified：`tests/test_r8_model_scenes.py`（场景配置与代码位置、加解密往返/行绑定/换主密钥/轮换、缺主密钥 422 且不落库而环境变量 Key 可用、主密钥不能当模型变量名、Key 不出现在任何接口响应/审计/outbox/OpenAPI、实际请求用页面 Key、短 Key 与换域名、场景校验与 requires_search、取用顺序与停用回退、权限 403、定时器不选模型时跟随场景并在场景不可联网时记失败、预置包页面/命令行不带模型导入、清除 Key、`rotate-secret-key`）；`tests/test_migrations.py::test_0015_model_scenes_up_and_down`（升级/回退/再升级，模型与迁移无漂移）。本机隔离 PostgreSQL 16 全量后端测试通过，前端类型检查与构建通过，CI 结果见对应 PR。模型配置页白天/黑夜用 jsdom + WeasyPrint 静态渲染检查过版式（假数据）。**未用真实厂商 Key 联调**；上线前须在服务器设置 `VIP_SECRET_KEY` 并在页面保存一次 Key、对一个定时器点“立即执行”确认。
