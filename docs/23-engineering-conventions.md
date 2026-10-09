# 23 工程规范：接口、账号权限、菜单、前端结构

> 2026-10-09 起所有新代码遵守本文；旧接口的响应体不改，以免打断已有页面和测试。状态：**已实现、测试通过（CI），尚未在真实服务器使用**。

## 1. 账号、角色、权限

- 账号属于工作区（`membership`）。一个人在一个工作区可以有**多个角色**，权限取并集。
- 角色固定五种，定义在 `config/roles-standard-v1.json`（含中文名、说明、每个权限的中文名）。暂不支持在页面上新建角色；需要时改配置并发版。

| 角色 | 中文名 | 能做什么 |
|---|---|---|
| `viewer` | 只读访客 | 阅读研究资料，管理自己的自选与笔记 |
| `researcher` | 研究员 | 研判资讯、修订研究判断与模板 |
| `strategy_manager` | 策略负责人 | 编辑、模拟、发布与回滚策略 |
| `data_admin` | 数据管理员 | 管理数据源、采集与资讯源，处理数据质量 |
| `system_admin` | 系统管理员 | 管理账号与角色、模型与系统配置，查看审计 |

- 管理入口：**后台设置 › 账号与角色**（需要 `user.manage` 或 `role.assign`）。可以开通账号（生成一次性初始密码，只显示一次）、改姓名、分配角色、重置密码、强制退出、停用/启用。
- 防锁死：不能停用自己、不能取消自己的系统管理员角色；工作区最后一个可用的系统管理员不能被取消或停用。
- 停用、重置密码会立即让该账号在所有浏览器退出；停用的账号所有接口返回 401。
- 每个变更写审计日志（`identity.user.*`），在 **后台设置 › 审计日志** 查看（需要 `audit.read`）。一次性密码从不写入日志。
- 服务器上仍可用 `python -m app.admin_cli` 开通第一个管理员（见 docs/22）。

## 2. 菜单

- 菜单与页签定义在 `config/menus-v1.json`：每个页签可写 `permissions`（满足任意一个即可见），不写则要求 `research.read`；菜单下没有可见页签时整组隐藏。
- 服务器在 `GET /api/me` 里按当前用户的权限返回 `menus`，前端只负责画。**隐藏菜单不是安全边界**，每个接口仍各自检查权限。
- 新增一个页签：① 在 `config/menus-v1.json` 加一项；② 在 `frontend/src/pages/index.tsx` 登记页面组件。测试 `test_every_menu_tab_has_a_page` 保证两边一致。

## 3. 接口

**路径**：全部在 `/api/` 下，资源名用小写复数、连字符（`/api/news-feeds` 风格；已有的 `/api/strike-zone`、`/api/llm-providers` 同理）。后台设置类接口在 `/api/admin/` 下；当前用户自己的东西在 `/api/me/` 下。

**方法**：`GET` 读；`POST` 新建或执行动作（动作用动词子路径，如 `/run`、`/sign-out`）；`PUT` 整体替换；`PATCH` 改部分字段；`DELETE` 删除。新建成功返回 `201`。

**错误**：所有非 2xx 响应同一个形状——

```json
{
  "error": {"code": "conflict", "message": "该账号已在本工作区", "details": []},
  "detail": "该账号已在本工作区",
  "request_id": "9f3c…"
}
```

| HTTP | code | 何时 |
|---|---|---|
| 400 | `bad_request` | 其他请求错误 |
| 401 | `unauthorized` | 未登录、会话过期、账号停用 |
| 403 | `forbidden` / `csrf` | 没有权限 / 缺少 `X-Requested-With: vip` |
| 404 | `not_found` | 对象不存在或不在当前工作区 |
| 409 | `conflict` | 状态冲突、重复 |
| 422 | `invalid` | 参数不合法；`details` 逐项给出 `field` 和 `message` |
| 429 | `rate_limited` | 登录尝试过多 |
| 500 | `internal` | 未预期错误；只返回请求编号，细节写服务器日志 |

`detail` 为兼容旧前端保留，新代码读 `error.message`。领域服务抛 `app.core.errors` 里的 `NotFound / Conflict / Invalid / Forbidden`，不要自己拼响应。

**请求编号**：每个响应带 `X-Request-Id`（客户端传入合法的就沿用），同时写进错误体和访问日志（`app.access`）。用户报错时让他提供这个编号。

**分页**：列表接口用 `?limit=&offset=`（`limit` 1–200，默认 50），返回 `{"items": [...], "total": N, "limit": L, "offset": O}`。用 `app.core.paging` 的 `page_params` 和 `page()`。新接口必须分页；旧的列表接口（直接返回数组）在下次改动时迁移。

**OpenAPI**：接口按中文模块分组（资讯雷达 / 公司档案 / 策略 / 监控告警 / 后台设置 / 账号与角色…）。改了接口运行 `make generate-client`，更新 `contracts/openapi-v0001.json` 和 `frontend/src/api-schema.ts`。

## 4. 后端目录

见 [21 后端分层地图](./21-backend-layers.md)。一句话：`api/` 只管 HTTP，`domains/` 放业务，`models/` 放表，`core/` 放基础设施。

## 5. 前端目录

```
frontend/src/
  main.tsx            入口：判断登录方式，进入工作台
  core/client.ts      请求封装：会话 cookie、CSRF 头、统一错误（ApiError 带 code 和请求编号）
  shell/              外壳：workspace.tsx（菜单、页签、读取与提示状态）、account.tsx（登录、账号面板、主题切换）、style.css
  pages/              一个菜单一个文件：radar / company / strategy / monitor / settings / accounts；index.tsx 是页签→页面登记表
  components/         通用组件：common（格式化、useLoad、Kpi…）、ui、judgments、template
  api-schema.ts       由 OpenAPI 生成，不要手改
```

页面拿到的上下文统一为 `{ allow, busy, execute }`；`execute(fn, 成功提示, 是否回读)` 负责忙碌状态、错误提示和权限不足提示。自己读数据的页面用 `useLoad(path)`。

`backend/static/app.js` 由 `npm run build` 生成并入库，CI 会检查它与源码一致。
