# 富途已有账号接入切片（2026-10-06）

基线 main `e2fad1a49d8475d650471c9c628eb8b05c5a60a8`。用户已授权本机真实资料获取/写入和私有主干提交，并确认已有牛牛账号。首次 OpenD 启动、登录与协议由本人完成；本项目只调用行情接口，不创建交易对象、不查询账户或持仓。

| ID | 预期与范围 | 验证与停点 |
|---|---|---|
| FT-01 | 可选官方 SDK，固定本机127.0.0.1:11111；限定 HK.01211 / HK.09969、30日内已结束日期、日K、显式不复权、不扩展分页 | 无监听明确返回；失败不输出供应商原始错误；调用参数与关闭上下文验证 |
| FT-02 | 身份回读拒绝未知/重复/错交易所，保留 SDK 解码行/hash/实际取得时点；不声称取得原始网络字节 | 身份、hash、时间/范围、重复、OHLC、NaN、不复权及分页边界 |
| FT-03 | 原值本机保存/确定性分析需已有API协议允许；导入另需独立挂牌币种原文及工作区可读修订 | 无权利记录不捕获；无币种证据不写库；跨工作区/撤权拒绝；追加效果与审计/outbox同事务、重放幂等 |
| FT-04 | 两公司独立参考价格、可读原文及研究摘要；与已有ECB同日FX匹配 | 隔离合成库贯通验证；真实回读仅在本人登录和证据就绪后执行 |

不修改schema/权限；不扩证券/时期、不采购/开户/改IP、不接受协议。价格保持REFERENCE，缺最终性和批准日历仍不能正式seal。SDK开源许可不是行情许可。实际写库前复核真实服务器/数据库与既有可恢复备份；回退代码不删除已追加真实资料。原值、协议记录、账号日志、备份不入Git。

## 实际执行与接续

可选SDK已固定为10.11.7108，实际Python导入与不复权常量检查通过。新增客户端/CLI支持原文、本机协议范围记录、独立币种原文修订、两公司参考输入、研究摘要、审计/outbox及重放；`hk_market`只将授权名单扩至09969.HK。未改UI或schema，已有market_summary展示直接复用。

`./tools/vip test`最终223 passed，1条已有Starlette/httpx弃用warning；只在受入口保护的本机隔离合成库运行。29项新增场景包含两证券捕获/导入/摘要/幂等、未复权、未知身份、分页停止、OHLC/hash/时间、权限错误脱敏及币种原文缺失/撤权/工作区隔离。首次测试的合成币种夹具漏填两项非空字段，补齐后通过；生产逻辑未为适应夹具弱化。

实际`./tools/vip futu-import --check`在获准本机socket检查环境返回listening=false，authenticated/quote_permissions仍not_checked；不能把沙盒禁止socket等同无监听。未连接账户、取得真实港股bar或写真实库。当前真实前置仍为本人OpenD登录、API权限、适用API协议的个人保存分析范围以及独立挂牌币种原文；不把既有编写身份备注或发行价当当前报价币种证据。源条件未齐，完整真实研究仍partial。

操作入口：`./tools/vip futu-import --check`。捕获示例（本人已完成OpenD登录/协议范围核对后，由操作者填写本机忽略的权利记录）：

```sh
./tools/vip futu-import --capture --start 2026-09-01 --end 2026-09-30 --rights /absolute/project/local-data/futu/rights.json
```

`rights`包含provider=futu、use=local_personal_research、实际reviewed_at、agreement名称/版本、clause_locator、permitted_scope，和已核对的reviewed/fetch/store/analyze=true；export/external_model=false。只是结构化本机复核记录，不是程序自动解释或颁发许可，不记录账户资料。模板默认false/空，不可直接作为授权输入。

捕获仅将SDK解码选定列保存在raw-data/futu，不声称原始wire bytes。入库须两份独立`currency-basis`对象（ticker、currency、reviewed、原文excerpt和已有可读evidence），CLI用`--snapshot`（最多两份）、`--workspace`、`--currency-basis`、`--write`在同事务追加。真实写入时复核实际本机库/备份，之后逐行复算、重放、旧hash、同日FX与真实API/UI回读；本次没有将这些待执行项写为通过。

官方设置/来源限制见[富途已有账号设置](../research/futu-readonly-setup.md)。用户不清楚设置操作，主会话从官方动态入口下载10.11.7108 Mac包，仅在本机忽略目录准备；macOS原生tar解压后完整签名和Gatekeeper检查通过（Notarized Developer ID），未代本人启动/登录/接受协议。Python通用tar解压会把AppleDouble元数据作为额外文件影响资源封签，第一次副本未交用户执行；原生解压副本正确恢复元数据，没有重签、去隔离或绕过系统保护。当前股数、FINAL/批准日历和正式seal的旧缺口见[财务与FX续建](./REAL-GAP-CLOSURE.md)。

## 本人登录后的实际验证

后续基线main `173a78c6badb79d827edba7048776e3a49f2a526`。用户明确“已经登录”，本机只读探测listening=true；仅创建行情对象，对两精确代码basicinfo成功并通过名称/STOCK/HK_MAINBOARD/未退市/有效stock_id校验。总额度接口成功；没有查询账户/持仓、调用交易或读取OpenD个人配置。SDK额度响应是tuple，首次本机诊断脚本误按DataFrame解析，修正后真实回读成功；没有为此改产品合同。

FT-03的报价币种证据已经落地：诺诚健华既有中报补入PDF物理第5/11页，82项原始财务事实不变；比亚迪唯一新增H股中报只摘录第2/5页，物理第5页对应印刷第4页，精确区分01211港币柜台与81211人民币柜台，不新增81211证券，不将该报告解析为新的财务事实。出处、原件hash及视觉核对见[本次来源核查](../research/futu-data-rights-and-currency.md)。在已授权本机真实库追加原文修订/效果与审计/outbox，未改schema或来源政策；写前复核实际PG/schema并创建可恢复备份。

实际回读：两股币种依据均可通过现有API读取固定原文修订，独立工作区返回404；11个旧研究、41个旧原文修订、30个旧输入的ID/hash全部保持。比亚迪脚本在提交成功后输出时访问失效ORM对象，打印失败；没有把exit=1误判为未提交而盲重写，先只读回读确认效果存在，修正本机脚本输出变量。原件、原值、协议全文、账户额度、备份及私人日志保存在Git忽略目录。只涉及元数据/原件入库，未改产品代码，223项产品回归仍为前节已验证基线，不称本轮另跑。

当前仍未请求、保存或导入富途日线。官方API协议入口本轮两次504且网页限频，停止重试，未取得本人实际适用协议全文；账户登录/免费额度不足以自动确认存储分析范围。已向本人请求核实“仅本机保存、个人研究、不对外分享”是否在所接受API协议范围内，这是上游权利事实核对，不是重新申请已有本机写库授权。没有生成通过的rights记录或用占位值绕过捕获门。币种依据文件已经准备，收到明确范围事实后才运行有限日线捕获与原值/FX/幂等/真实研究/UI验证。

本机证据：`local-data/verification/futu-identity-probe.json`、`futu-before-import.json`、`futu-currency-readback.json`、`futu-evidence-api-readback.json`。备份经pg_restore --list校验；回退代码不删除追加证据，恢复真实库仍需明确恢复范围授权。诺诚健华当前普通股覆盖、两证券FINAL、批准日历/正式seal及pending经营建议保持既有未完成状态，没有虚构股份数量、最终价或确认判断。
