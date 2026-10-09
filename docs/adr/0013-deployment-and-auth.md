# ADR 0013 部署形态与正式登录

- 状态：已采纳（2026-10-09）；第 3 条中“密钥只按环境变量名引用”部分由 ADR 0015 取代（页面可填写 Key，加密入库），出站白名单不变
- 背景：公网部署前必须替换 mock 身份；模型密钥由后台按"环境变量名 + 接口地址"引用，管理员可借此把密钥发往任意地址。
- 决定：
  1. 账号密码 + 服务端会话（scrypt、HttpOnly/Secure/SameSite=Strict cookie、库内只存 token 哈希、登录限流）。无自助注册，账号由 `python -m app.admin_cli` 开通。OIDC 以后可替换登录入口，会话与权限校验不变。
  2. `VIP_AUTH_MODE` 默认 `session`（失败即关闭）；`dev` 仅本机与测试。
  3. 模型密钥出站白名单：变量名 `VIP_*_KEY` 且非 DB/SMTP/会话类；https；域名 ∈ config 厂商域名 ∪ `VIP_LLM_ALLOWED_HOSTS`。保存与取用双重校验。
  4. 单镜像 + docker compose（db/migrate/api/worker/scheduler/caddy），scheduler 进程替代宿主 cron。
  5. psycopg2-binary 换为源码构建的 psycopg2。
- 后果：本机开发需显式 `VIP_AUTH_MODE=dev`；用代理接口访问 OpenAI 时必须由运维把代理域名写入服务器环境变量。
