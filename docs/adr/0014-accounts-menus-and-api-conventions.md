# ADR 0014：账号与角色管理、服务器下发菜单、统一接口规范

- 状态：已接受（2026-10-09）
- 相关：ADR 0013（部署与登录）、docs/21、docs/23

## 背景

PR #11 有了正式登录，但开账号、改角色只能在服务器命令行做；前端菜单和权限表写死在页面代码里，与后端权限各管各的；一个人有多个角色时后端只取第一个；错误响应、列表分页没有统一格式；后端 `services/` 与 `domains/` 并存，新旧代码两套放法。

## 决定

1. **角色保持五种固定角色**（用户 2026-10-09 确认“暂时没有那么复杂，后续再处理”），不做可自定义角色。一个人可在同一工作区持有多个角色，权限取并集。
2. **后台设置 › 账号与角色**：开通账号（一次性初始密码）、改姓名、分配角色、重置密码、强制退出、停用/启用；防止工作区失去最后一个系统管理员。全部写审计，新增 **审计日志** 页。
3. **菜单由服务器下发**：`config/menus-v1.json` 定义菜单、页签和所需权限，`GET /api/me` 返回当前用户可见的菜单；前端不再自带权限表。
4. **统一错误体** `{error:{code,message,details}, detail, request_id}`，保留 `detail` 兼容旧页面；每个请求带 `X-Request-Id`。
5. **统一分页** `?limit&offset` → `{items,total,limit,offset}`，新接口强制，旧接口改动时迁移（不一次性改，避免打断页面）。
6. **目录统一**：`app/services`、`app/sources` 全部并入 `app/domains/<层>`；表定义全部在 `app/models/`；仓库路径用 `app/core/paths.py`。前端按 `core / shell / pages / components` 拆分，`pages/index.tsx` 为页签登记表。
7. **系统管理员为全权限**（用户 2026-10-09 决定：“管理员是全权限”）。`system_admin` 持有 `config/roles-standard-v1.json` 中定义的全部权限（含 research.read、watchlist.own、notes.*、analysis.override、template.*、strategy.*、scoring.binding.publish、source.manage、job.retry、identity.manage、quality.correct 及原有的账号、配置、审计、运维权限），说明改为“全权限”，五个菜单全部可见。这取代 docs/11、docs/13、docs/14、docs/16 中“system_admin 不隐式拥有业务读取/发布/覆盖权限”的职责分离设定；其余四种角色边界不变。以后新增权限须同时授予 `system_admin`（测试保证）。
8. **导航为左侧两级导航**（用户 2026-10-09 要求纯左右布局）：菜单为分组、页签为分组下的页面项，内容区顶部只显示“菜单 › 页面”标题，取消顶部页签条。规范见 docs/23 §2.1。

## 后果

- 旧接口路径不变，前端与测试无须跟着改路径。
- 算法版本按文件名登记，搬目录不改指纹；历史研究与封存哈希不变（`test_algorithm_versions` 保证）。
- 历史文档（review/、versions/）中的 `services/...` 路径不改，对应关系见 docs/21。
- 系统管理员做的业务操作（研判、发布策略等）与其他角色一样写审计，以审计代替职责分离。
- 尚未做：自定义角色、跨工作区的超级管理员页面、旧列表接口的分页迁移。
