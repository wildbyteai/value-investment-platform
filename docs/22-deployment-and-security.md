# 22 部署与安全（上线前必读）

2026-10-09。本文是部署操作手册与安全说明；代码已实现、CI 已验证（测试 + 镜像构建），**尚未在真实服务器上部署或联调**。

## 1. 架构

```
浏览器 ──HTTPS 443──> Caddy（自动证书）──私网──> api（uvicorn ×2）
                                                   worker（outbox）
                                                   scheduler（采集/告警/资讯定时）
                                    仅内部网络 ──> PostgreSQL 16（不对宿主机/公网开端口）
```

全部由 `deploy/docker-compose.yml` 启动，同一个镜像（仓库根目录 `Dockerfile`）。

## 2. 服务器

- 试运行：1 台 4 vCPU / 8 GB / 100 GB SSD，Ubuntu 24.04，装 Docker Engine + compose 插件。
- 用 OpenAI 联网采集：选香港/新加坡区（大陆访问不了 OpenAI，且大陆区公网网站需 ICP 备案）。
- 安全组：入站只开 443、80（证书签发与跳转）、SSH（限制来源 IP，最好只用密钥登录）。5432、8766 不开。

## 3. 第一次部署

```bash
git clone <仓库> /opt/vip && cd /opt/vip/deploy
cp .env.example .env && chmod 600 .env            # 填域名、两个数据库密码（openssl rand -base64 32）
mkdir -p secrets && cp secrets-example/app.env secrets/app.env && chmod 600 secrets/app.env
#   ↑ 填 VIP_SECRET_KEY（openssl rand -base64 32）、SMTP；模型密钥可以填这里，也可以之后在页面 模型配置 填写
# DNS：把域名 A 记录指向服务器公网 IP
docker compose up -d --build                     # 自动执行 alembic upgrade head，再起 api/worker/scheduler/caddy
docker compose ps && curl -I https://<你的域名>/api/health
```

开通账号（没有自助注册）：

```bash
docker compose run --rm api python -m app.admin_cli create-workspace "价值投资研究"
docker compose run --rm api python -m app.admin_cli create-user you@example.com "你的名字" --workspace "价值投资研究" --role system_admin
docker compose run --rm -it api python -m app.admin_cli set-password you@example.com     # 交互输入，不进 shell 历史
```

第一个系统管理员登录后，其他人的账号在网页 **后台设置 › 账号与角色** 开通、分配角色、重置密码和停用，不必再上服务器（见 docs/23）。

角色：viewer / researcher / strategy_manager / data_admin / system_admin，可多次 `--role`。停用账号：`disable-user`（同时踢下线）。

模型：在 **后台设置 › 模型配置** 添加模型并直接填写 API Key（加密入库，见 ADR 0015），再在“按场景配置模型”里给 **资讯采集**（必须能联网）和 **资讯研判打分** 各选一个模型；不选的场景用默认模型。

预置每日资讯采集任务（6 个定时器 + 共用 Skill，见 ADR 0012 补充）：在 **后台设置 › 采集定时器** 点“导入预置采集任务”（默认跟随场景“资讯采集”的模型），或在服务器上：

```bash
docker compose run --rm api python -m app.admin_cli install-collector-presets --workspace "价值投资研究"                 # 跟随场景“资讯采集”；可重复执行，已有的跳过
docker compose run --rm api python -m app.admin_cli install-collector-presets --workspace "价值投资研究" --provider qwen  # 或给这些定时器单独指定模型
```

升级：`git pull && docker compose up -d --build`（迁移自动先跑）。

备份：`crontab -e` 加 `0 3 * * * /opt/vip/deploy/backup.sh >> /var/log/vip-backup.log 2>&1`，并把 `/var/backups/vip` 同步到另一台机器或对象存储。

## 4. 密钥不被拿走：做了什么

| 风险 | 措施 |
|---|---|
| 密钥进 Git / 镜像 | 主密钥 `VIP_SECRET_KEY`、SMTP 密码和（可选的）环境变量模型密钥只在服务器 `deploy/secrets/app.env`（600 权限，`.gitignore` 与 `.dockerignore` 都排除）；镜像里没有任何密钥 |
| 模型密钥存在哪里（2026-10-09 用户决定改为可在页面填写，ADR 0015，取代此前“只用环境变量”） | 管理员可在 **模型配置** 页面填写 API Key：用服务器主密钥 `VIP_SECRET_KEY`（环境变量，不进数据库）做 **AES-256-GCM 加密**后存入 `llm_provider.api_key_ciphertext`，密文绑定所在行（复制到别的行无法解密）。页面保存的 Key 优先，其次环境变量 `api_key_env`。未设置 `VIP_SECRET_KEY` 时页面保存 Key 会被拒绝（提示“系统未配置 VIP_SECRET_KEY…”），环境变量密钥照常可用 |
| 页面或接口返回密钥 | Key 只写不读：接口只返回来源（`key_source`：page / env / none）和末 4 位提示；审计、执行记录、错误信息、日志和 OpenAPI 示例都不含 Key（测试保证） |
| 数据库备份泄露 | **只有数据库备份解不开模型 Key**：主密钥不在库里。反过来，**恢复时必须同时有 `VIP_SECRET_KEY`**，否则页面保存的 Key 无法解密（页面会提示，需要重新填写；环境变量密钥不受影响）。主密钥与数据库备份分开保存 |
| 主密钥轮换 | 旧值移到 `VIP_SECRET_KEY_PREVIOUS`、设置新的 `VIP_SECRET_KEY`、重启，执行 `python -m app.admin_cli rotate-secret-key` 用新主密钥重新加密全部 Key，确认后删掉 `_PREVIOUS`。怀疑主密钥泄露时：轮换主密钥**并**在厂商控制台重建各模型 Key |
| **后台把密钥发到别处**（最大的口子） | 管理员可改模型的接口地址和密钥变量名。现在：变量名必须形如 `VIP_*_KEY`，且不能是数据库/SMTP/会话类变量；接口必须 https，域名必须在白名单（`config/model-presets-v1.json` 各预设的官方域名 + `news-radar-v1.json` 内置默认模型的域名 + 服务器环境变量 `VIP_LLM_ALLOWED_HOSTS`；2026-10-09 起为 api.openai.com、api.anthropic.com、generativelanguage.googleapis.com、api.deepseek.com、dashscope.aliyuncs.com、open.bigmodel.cn、api.moonshot.cn、ark.cn-beijing.volces.com、api.minimax.cn）。保存时校验，**每次取密钥时再校验**（页面保存的 Key 同样受限），旧数据也无法绕过。已保存 Key 的模型更换接口域名时必须重新填写 Key。只有能登录服务器的人才能扩大白名单 |
| 冒充身份 | 删除了"请求头即身份"的 mock 登录（仅本机开发 `VIP_AUTH_MODE=dev` 保留）；匿名身份列表接口在生产返回 404 |
| 会话被偷 | 会话 cookie：HttpOnly（脚本读不到）、Secure（只走 HTTPS）、SameSite=Strict；数据库只存 token 的 SHA-256，备份泄露也无法登录；空闲 12 小时 / 最长 7 天过期；改密码会踢掉其他浏览器 |
| 暴力猜密码 | scrypt 哈希；同一账号 15 分钟内失败 5 次、同一 IP 失败 20 次即锁定 15 分钟 |
| 跨站请求伪造 | 所有写操作要求同源自定义头 `X-Requested-With: vip` + SameSite=Strict |
| XSS / 点击劫持 | CSP（只允许本站脚本）、X-Frame-Options DENY、nosniff、Referrer-Policy no-referrer、HSTS；接口响应 `Cache-Control: no-store` |
| RSS 地址探测内网 | 抓取前解析域名，拒绝回环/内网/链路本地/云元数据地址（含跳转后） |
| 容器被攻破后的影响面 | 非 root（uid 10001）、只读根文件系统、去掉所有 capabilities、no-new-privileges；数据库在无外网的内部网络，应用用非超级用户 `vip_app` |
| 接口文档暴露 | 生产关闭 /docs、/redoc、/openapi.json |

## 5. 仍需你来做

1. **每台服务器单独申请一套模型密钥**，在各厂商控制台设**月度消费上限**；OpenAI 推理 max 很贵。
2. 发现泄露立刻在厂商控制台**作废并重建**密钥，再在 模型配置 页面重新填写（或改 `secrets/app.env` 后 `docker compose up -d`）。
3. 仓库保持私有；不要把 `deploy/.env`、`deploy/secrets/` 发给任何人或贴到聊天里。
4. SSH 只用密钥登录、关闭密码登录；服务器开自动安全更新。
5. 发件域 bytewatcher.xyz 配 SPF/DKIM，否则告警邮件易进垃圾箱。
6. 备份异机保存并做一次恢复演练（恢复演练要包括 `VIP_SECRET_KEY`，确认页面保存的模型 Key 能解密）。
7. `VIP_SECRET_KEY` 单独离线保存一份（如密码管理器），不要和数据库备份放在一起。

## 6. 本机开发

```bash
VIP_AUTH_MODE=dev VIP_COOKIE_SECURE=false uvicorn app.main:app --port 8766
```

dev 模式下登录页显示合成身份选择器，接口文档开放。**生产绝不能设 dev。**

## 7. 不在本次范围

行情采集脚本（baostock/futu/EODHD）仍按原设计只允许连本机数据库，不随容器自动运行；OIDC 单点登录、数据库高可用、WAL 归档（15 分钟 RPO）留待后续。
