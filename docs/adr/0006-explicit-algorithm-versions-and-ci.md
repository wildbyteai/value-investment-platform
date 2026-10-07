# 显式算法版本、迁移冻结与 CI 护栏（R1）

状态：proposed（PR 评审中），2026-10-07。

## 背景

- 算法身份原为 `scoring_service.py` 等源文件的**实时字节 sha256**。任何改动（含格式化、注释）都会改变 installed artifact、冻结 manifest 与参考研究 basis 的 hash，导致封存 409、无法安全重构。
- 迁移 `0010_formal_sealing` 直接用**当前 ORM 模型**建表、用**当前** `knowledge_clock` 装触发器：之后改模型，新库会静默得到不同结构，旧库却不变。
- 测试用 `create_all` 建库，发现不了模型与迁移漂移；仓库没有 CI，97 项数据库测试只在个人电脑跑。
- `test_sealing.py` 把收盘时间写死为 2026-10-07 08:00 UTC，而种子数据用真实时钟入库；该时刻一过，22 项封存测试全部失败（2026-10-07 当天触发）。

## 决定

1. 新增 `backend/app/services/algorithm_versions.py`：每个算法登记版本号（如 `scoring-v1`）与**发布时记录的指纹**（985fcd9 的源文件 sha256）。artifact 与 basis 只读登记值，不再读文件。payload 结构不变，所以**所有历史 hash 不变**（测试锁定）。
2. 行为变化必须显式发布：新增版本条目、保留旧条目、执行已批准的 `install_artifacts`。行为由固定输入回归测试保护，而非文件字节。
3. `0010_formal_sealing` 改为显式 DDL，并冻结当时的触发器 SQL；`pg_dump -s` 比对与原迁移结果逐字一致。已执行过的数据库不受影响。
4. 新增测试：迁移链与模型零漂移、迁移安装知识时钟、0010 冻结副本与 `knowledge_clock` 一致、历史 artifact/basis hash 不变、两套 PE 在固定输入下结果钉死且一致（A股、H股含汇率、满分封顶、非正利润）。
5. 修复封存测试的日期炸弹：种子阶段使用测试时钟，夹具修订时间固定在截止前。
6. 新增 GitHub Actions `backend-tests`：每个 PR 在 runner 本机起一次性 PostgreSQL，先跑真实迁移，再跑全部后端测试。不连接任何真实库。

## 不做

不改 docs/02、docs/11、docs/12 的业务合同与公式；不改任何计算逻辑；两套 PE 的合并留到 R3，届时以本回归为准。

## 验证

本地一次性 PostgreSQL 16：迁移后全量 267 项通过（原 257 项 + 新增 10 项；修复前 22 项封存测试失败）。
