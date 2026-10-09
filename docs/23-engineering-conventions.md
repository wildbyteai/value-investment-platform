# 23 工程规范：接口、账号权限、菜单、前端结构、界面规范

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
| `system_admin` | 系统管理员 | **全权限**：拥有全部权限（账号与角色、模型与系统配置、审计，以及全部业务读写与发布），五个菜单都可见 |

- 系统管理员为全权限是用户 2026-10-09 的决定（见 ADR 0014 第 7 条），取代此前“系统管理员不隐式拥有业务权限”的职责分离设定。新增权限时须同时加进 `system_admin`（测试 `test_system_admin_holds_every_permission` 保证）。其余四种角色的边界不变。

- 管理入口：**后台设置 › 账号与角色**（需要 `user.manage` 或 `role.assign`）。可以开通账号（生成一次性初始密码，只显示一次）、改姓名、分配角色、重置密码、强制退出、停用/启用。
- 防锁死：不能停用自己、不能取消自己的系统管理员角色；工作区最后一个可用的系统管理员不能被取消或停用。
- 停用、重置密码会立即让该账号在所有浏览器退出；停用的账号所有接口返回 401。
- 每个变更写审计日志（`identity.user.*`），在 **后台设置 › 审计日志** 查看（需要 `audit.read`）。一次性密码从不写入日志。
- 服务器上仍可用 `python -m app.admin_cli` 开通第一个管理员（见 docs/22）。

## 2. 菜单

- 菜单与页签定义在 `config/menus-v1.json`：每个页签可写 `permissions`（满足任意一个即可见），不写则要求 `research.read`；菜单下没有可见页签时整组隐藏。
- 服务器在 `GET /api/me` 里按当前用户的权限返回 `menus`，前端只负责画。**隐藏菜单不是安全边界**，每个接口仍各自检查权限。
- 新增一个页签：① 在 `config/menus-v1.json` 加一项；② 在 `frontend/src/pages/index.tsx` 登记页面组件。测试 `test_every_menu_tab_has_a_page` 保证两边一致。

### 2.1 导航布局：左侧两级导航，没有顶部页签（2026-10-09 起）

- 纯左右布局：**所有页面切换都在左侧导航**，右侧是内容区。不再有顶部页签条（旧的 `.subtabs` 已删除），页面里也不要再做“切换到另一个页面”的页签。
- 左侧导航由 `menus` 画成两级（`frontend/src/shell/sidenav.tsx`）：每个菜单是一个分组标题（图标 + 名称，可折叠），它的页签是缩进在下面的页面项；点页面项即切换，当前页面高亮并带 `aria-current="page"`。只有一个可见页面的菜单直接显示为一项。
- 宽屏可把导航栏收起成 64px 图标栏（底部“« 收起 / »”，记在 `localStorage["vip-nav-mini"]`），图标栏里点分组图标进入该组当前（或第一个）页面。
- 分组折叠状态记在本机 `localStorage["vip-nav-collapsed"]`；当前页面所在的分组总是展开。导航栏单独滚动，账号区固定在底部；未读告警数显示在“我的通知”项上（分组折叠时显示在分组标题上）。忙碌时页面项禁用，分组折叠不受影响。
- 内容区顶部是页头：上一行面包屑（“后台设置 / 采集定时器”，14px，次要色，不可点击；看原文时追加“/ 固定原文”），下一行页面标题（20/28）；右侧放刷新与白天/黑夜切换。
- 窄屏（< 900px）导航收成左侧抽屉：顶栏“☰ 菜单”打开，点遮罩、✕ 或 Esc 关闭，选中页面后自动关闭。
- 页面内部可以有**内容筛选/分段控件**（如资讯雷达“全部事件 / 待确认”、击球区“按区域筛选”、公司详情里的“经营质量 / 财务…”内容页签），它们只切换同一页面里的内容，不算导航。

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
  shell/              外壳：workspace.tsx（读取与提示状态、内容区标题）、sidenav.tsx（左侧两级导航）、account.tsx（登录、账号面板、主题切换）、style.css
  pages/              一个菜单一个文件：radar / company / strategy / monitor / settings / accounts；index.tsx 是页签→页面登记表
  components/         通用组件：common（格式化、useLoad、Kpi…）、ui、judgments、template
  api-schema.ts       由 OpenAPI 生成，不要手改
```

页面拿到的上下文统一为 `{ allow, busy, execute }`；`execute(fn, 成功提示, 是否回读)` 负责忙碌状态、错误提示和权限不足提示。自己读数据的页面用 `useLoad(path)`。

`backend/static/app.js` 由 `npm run build` 生成并入库，CI 会检查它与源码一致。

## 6. 界面规范（基于 Ant Design 设计规范）

依据 [Ant Design 字体](https://ant.design/docs/spec/font-cn) 与 [布局](https://ant.design/docs/spec/layout-cn) 规范；**不引入 antd 组件库**，仍用自有组件，只在 `frontend/src/shell/style.css` 用一套 CSS 设计令牌实现。文件顶部一个 `:root` 令牌块（白天）+ 一个 `:root[data-theme="dark"]` 块（黑夜），其后所有规则只引用令牌，不写零散的颜色、字号、圆角、间距（布局尺寸如栏宽、最大宽度除外）。主题切换按钮在页头右侧，记在 `localStorage["vip-theme"]`。

### 6.1 字体

- 字体族 `--font`：`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif`。
- 数字（表格、评分、价格、指标）一律 `font-variant-numeric: tabular-nums`。
- 字号只用 5 级，字重只用 400 / 500（大数字可用 600）：

| 令牌 | 字号 / 行高 | 用途 |
|---|---|---|
| `--fs-sm` / `--lh-sm` | 12 / 20 | 辅助文字、说明、徽章 |
| `--fs` / `--lh` | 14 / 22 | 正文（基准） |
| `--fs-lg` / `--lh-lg` | 16 / 24 | 区块标题（卡片标题、h3） |
| `--fs-xl` / `--lh-xl` | 20 / 28 | 页面标题 |
| `--fs-xxl` / `--lh-xxl` | 24 / 32 | 大数字（指标、报价） |
| `--fw` / `--fw-strong` / `--fw-num` | 400 / 500 / 600 | 正文 / 标题与强调 / 仅数字 |

### 6.2 颜色

| 令牌 | 白天 | 黑夜 | 用途 |
|---|---|---|---|
| `--text` | `#000000E0` | `#FFFFFFD9` | 主文字 |
| `--text-2` | `#000000A6` | `#FFFFFFA6` | 次要文字 |
| `--text-3` | `#00000040` | `#FFFFFF40` | 禁用文字 |
| `--border` | `#D9D9D9` | `#424242` | 控件描边 |
| `--divider` | `#0505050F` | `#FDFDFD1F` | 分割线、卡片边 |
| `--bg-layout` | `#F5F5F5` | `#000000` | 页面底色 |
| `--bg-container` | `#FFFFFF` | `#141414` | 卡片、导航、表格 |
| `--bg-fill` | `#FAFAFA` | `#1D1D1D` | 表头、次级底色 |
| `--bg-hover` | `#0000000A` | `#FFFFFF14` | 行/菜单悬停 |
| `--primary` / `-hover` / `-active` | `#1677FF` / `#4096FF` / `#0958D9` | `#1668DC` / `#3C89E8` / `#1554AD` | 主色 |
| `--primary-bg` | `#E6F4FF` | `#111A2C` | 选中项底色 |
| `--success` | `#52C41A` | `#49AA19` | 成功 |
| `--warning` | `#FAAD14` | `#D89614` | 警告 |
| `--error` | `#FF4D4F` | `#DC4446` | 错误、危险操作 |
| `--up` / `--down` | = `--error` / `--success` | 同左 | **A 股/港股习惯：上涨/利好红、下跌/利空绿**，只用于会涨跌的数字（影响分、利好利空、价格变化） |

每个语义色另有 `-bg`、`-border` 浅底与描边令牌，用于提示条与徽章。

### 6.3 间距、圆角、控件、阴影

- 间距走 8px 栅格：`--sp-1..--sp-12` = 4 / 8 / 12 / 16 / 24 / 32 / 48。卡片、区块内边距 24；表单项纵向间距 24；行内元素间距 8。
- 圆角 `--radius` 6（`--radius-sm` 4、`--radius-lg` 8，卡片用 8）。
- 控件高度 `--ctl-h` 32（`--ctl-h-sm` 24、`--ctl-h-lg` 40）。
- 阴影 `--shadow` = `0 6px 16px 0 rgba(0,0,0,.08), 0 3px 6px -4px rgba(0,0,0,.12), 0 9px 28px 8px rgba(0,0,0,.05)`，只用于浮层（对话框、抽屉、登录卡）；卡片用描边，不加阴影。

### 6.4 按钮

| 类型 | 写法 | 用途 |
|---|---|---|
| 默认（描边） | `<button>`（不写类） | 大多数操作 |
| 主按钮 | `className="primary"` | 该区域最主要的一个操作 |
| 危险 | `className="danger"` | 删除、停用、重置密码、强制退出等破坏性操作；**必须先 `confirm()` 二次确认** |
| 文字 | `className="text"` | 弱操作（如“技术诊断”） |
| 链接 | `className="link"` | 像链接一样跳转（如“返回…”、时间线条目） |
| 尺寸 | 加 `small`（24）或 `large`（40） | 表格行内操作用 `small` |

- **一个区域（卡片、表单、工具栏、对话框）只放一个主按钮**；同一区域出现第二步（如“预览”之后的“发布”）时，前一步降为默认按钮。
- **按钮顺序：主按钮放在按钮组最左侧**，页面工具栏、表单底部、确认条都一样左对齐（“保存 → 取消”、“确认发布 → 取消”、“批量确认 → 批量驳回 → AI 打分”）。
- 页面内的分段控件（`.seg`）与公司详情的内容页签（`.tabs`）是同一页面内的筛选/切换，不是按钮组，也不是导航。

### 6.5 布局

- 左侧导航固定宽 `--sider-w` 208（收起 `--sider-w-mini` 64），右侧内容区自适应；窄屏（< 900px）导航为抽屉。
- 页头高约 64：面包屑（14）+ 页面标题（20/28）在内容之上；内容区内边距 24，最大宽 1480。
- 表格：表头 `--bg-fill`、字重 500；单元格内边距 12 / 16（行高约 47）；行悬停 `--bg-hover`；表格底色 `--bg-container`。
- 卡片（`article`、`.panel`、`.kpi`）：`--bg-container` 底、`--divider` 描边、圆角 8、内边距 24；卡片头高 56、标题 16/24。
- 测试 `test_style_uses_design_tokens` 检查样式文件只用令牌字号与颜色。

## 7. 模型调用与密钥（2026-10-09 起，ADR 0015）

- **新增调用大模型的代码，先在 `config/model-scenes-v1.json` 登记一个场景**（key、中文名、说明、`requires_search`、代码位置、`recommended` 推荐模型与推理强度、`cost_note`），代码里用 `model_scenes.resolve(db, workspace_id, '<scene>')` 取模型（已带场景的推理强度），不要自己查默认模型、不要写死模型名或强度。接口已定、调用代码在后续 PR 的场景标 `status: planned` + `planned_in`（ADR 0016）。测试 `test_scene_config_maps_real_code_paths` 检查每个 active 场景的代码位置存在。
- 推理强度只经 `domains/news/reasoning.py` 写进请求（各厂商取值与映射不同）；新厂商要支持强度，在 `config/model-presets-v1.json` 给预设加 `reasoning_efforts` / `reasoning_style`。
- 契约先行、实现未合入的接口抛 `app.core.errors.NotImplementedYet`（501，`code: not_implemented`），权限依赖照常生效。
- 模型的 Key 只通过 `ProviderConfig.api_key` 取得（页面加密 Key 优先，其次环境变量，都经过出站白名单）；不得把 Key 写进日志、审计、执行记录、错误信息或接口响应。接口只返回 `key_source` / `key_hint`。
- 需要加密保存的其他机密以后也用 `app/core/secret_box.py`（AES-GCM，主密钥 `VIP_SECRET_KEY`，关联数据绑定所在行），不要另起一套。
