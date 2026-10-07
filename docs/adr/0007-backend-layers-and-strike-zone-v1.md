# 后端四层骨架与击球区 v1（R3）

状态：proposed（PR 评审中），2026-10-07。

## 背景

- 后端按技术类型平铺在 `services/`（28 个模块），读代码看不出“资讯 → 公司 → 策略 → 告警”的业务主线。
- 服务层直接 `raise HTTPException`（48 处），业务逻辑依赖 Web 框架；部分 API 捕获服务异常时也绑在 HTTPException 上。
- 数据源散落在各 provider 模块，只能读代码才知道有哪些源、喂哪一层、需要什么密钥。
- ADR 0005 已确认击球区三条件，但“安全边际”阈值待定，能力圈与区域划分未实现。

## 决定

1. 新增 `app/domains/{news,companies,strategy,monitoring}` 四个业务层包，每个包的 docstring 写明它负责什么、哪些旧模块归它。依赖只能“下游用上游”：告警 → 策略 → 公司 → 资讯。旧模块本次**不搬家**（避免改动测试 monkeypatch 路径与已封存算法的来源位置），随各层改造逐步迁入。
2. 新增 `app/core/errors.py`：`Forbidden/NotFound/Conflict/Invalid` 领域异常，HTTP 层统一转换为原状态码与 `{"detail": ...}` 原响应体；4 个服务模块全部改用领域异常，`services/` 与 `domains/` 不再 import FastAPI（测试锁定）。
3. 新增 `app/core/uow.py`：新代码的服务只 `add/flush`，由请求或任务入口用 `unit_of_work(db)` 统一提交或回滚。旧路由的 `db.commit()` 随层迁移替换。
4. 新增 `app/sources/registry.py`：登记全部外部数据源（名称、所属层、类型、代码位置、触发方式、市场、所需密钥）；后台设置 › 数据源读取此表（`GET /api/admin/sources`）。新资讯源实现 `FeedAdapter`。
5. **击球区 v1**（`app/domains/strategy/strike_zone.py`，数字全部在 `config/strike-zone-v1.json`）：
   - 能力圈：行业/公司白名单（空 = 策略适用范围内全部行业）且评分覆盖度 ≥ 0.80。
   - 好生意：已发布策略的入池门槛中，除估值与覆盖度外全部达标；已确认硬风险一票否决。
   - 安全边际：`1 − 市盈率TTM / 合理市盈率`，合理市盈率 15，**甜区要求 ≥ 30%**，10%–30% 为边角球，<10% 区外；无市盈率时以估值分 ≥ 60 代理。用户 2026-10-07 同意“按标准逻辑定 30%，后续调整”。
   - 三项全过 = 甜区；任何一项明确不过 = 区外；其余（差一点或依据不全）= 边角球。A股、H股按证券分别判断。
   - `GET /api/strike-zone`（看板）、`/api/strike-zone/companies/{id}`、`/api/strike-zone/policy`。

## 不做

不改 docs/02、docs/11、docs/12 的公式与合同；不改评分、估值、状态机与封存的计算；不改任何历史 hash；击球区是在既有评分之上的只读分类，不写库。合理市盈率 15 是通用起点，后续可按行业细化。

## 验证

新增 `tests/test_r3_layers.py`（13 项）：服务层不依赖 FastAPI、异常状态码、事务提交/回滚、数据源注册表、击球区各分支（甜区/边角球/区外、硬风险否决、白名单、覆盖度、估值分代理）、看板 A/H 分开、404 走领域异常、后台权限。全量 280 项通过。
