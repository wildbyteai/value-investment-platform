# 港股与官方汇率最小复核

核查日期：2026-10-06；开始时源码 revision `6f231481128330576219b3919fd453fafba963f1`，存在其他任务未提交修改，未改动它们。本次仅写本文件，不注册、采购、读取凭证、接受账户协议、执行交易或写数据库。请求仅包含公开资料网址、币种和日期；没有向网络发送项目源码、公司原件、本机真实原始数据或密钥。research 技能要求的主来源研究由本研究子 Agent 执行。

范围固定：01211.HK 与 09969.HK，2026-09-01 至 2026-09-30（包含两端、30个日历日）；汇率独立核查。这里只记录来源、权限与最小响应元数据，不保存真实原始响应或证券价格进 Git。先前结果见 [港股续查](./hk-free-source-followup.md) 与 [原来源核查](./real-completion-sources.md)。

## 实际结论

- **HKMA 公开日汇率接口本次 GET 可达**，HTTP 200、业务成功；取最新40行仍只到2026-08-31，未解决9月同日FX。不能把此前405解释为接口本身永久不支持GET，也没有充分证据断定此前错误一定来自代理。
- **ECB 官方无账户API真实取得9月两币种参考汇率**：CNY/EUR与HKD/EUR各22行，覆盖9月1日至30日，包括9月30日；这是可执行的免费交叉汇率来源。需独立标注ECB来源、加工方法、参考汇率时点与实际知识截止，不能称HKMA/香港收盘汇率。
- **没有验证到本次可直接免账号取得、且允许本系统保存分析的两只港股30日日线源。** 这不是“所有港股都收费”的结论。已核实富途可不开户使用API，但仍需要登录账号、首次合规确认及实际行情权限；若用户已有账号，它是无需新账号的条件路线。本次没有使用账户或取得证券bars。
- EODHD既有令牌成功但官方70个市场无HK的已验证停点保持；本次未读取令牌或调用其鉴权接口，不建议升级，更不以ADR/其他币种挂牌代替两只港股。

## HKMA：接口成功与覆盖不足分开记录

[官方英文字段页](https://apidocs.hkma.gov.hk/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/er-eeri-daily/)与[中文字段页](https://apidocs.hkma.gov.hk/gb_chi/documentation/market-data-and-statistics/monthly-statistical-bulletin/er-ir/er-eeri-daily/)本次HTTP 200。注意英文路径没有`/eng/`；加入该前缀的尝试本次404，是文档URL问题，不能据此判API失败。

官方接口：

```text
https://api.hkma.gov.hk/public/market-data-and-statistics/monthly-statistical-bulletin/er-ir/er-eeri-daily?pagesize=40&sortby=end_of_day&sortorder=desc
```

两次相同有界GET均HTTP 200；第二次请求加入`Cache-Control: no-cache`。响应`header.success=true`、`err_code=0000`、`err_msg=No error found`；40行日期最大2026-08-31、最小2026-07-16，9月行数0。响应HTTP Date为`Tue, 06 Oct 2026 03:59:12 GMT`，没有Age头。此证据说明本次请求拿到的数据旧，不能证明所有其他HKMA数据源都没有9月数据，也不能把无Age头当作绝对排除缓存。

[官方通用参数文档](https://apidocs.hkma.gov.hk/documentation/)本次HTTP 200，明确支持`sortby/sortorder`和`choose/from/to`日期范围；9月筛选请求采用`choose=end_of_day&from=2026-09-01&to=2026-09-30&fields=end_of_day,cny&pagesize=40`并保留日期降序，首次25秒读超时，第二次15秒有界重试取得HTTP 405 `Not Allowed`。未取得此筛选的业务响应，不能断言零行或定位405来自HKMA/网关/代理哪一层；与不带范围/fields请求200的差异已确认。不做变换代理/IP、隐藏接口或扩大重试来绕过限制。

字段`cny`单位为**每单位人民币兑换的港元**，即HKD per CNY；不是CNY per HKD。需要人民币折算港元价格时使用倒数，保留原值与变换，不把缺日设置为1或沿用8月值。

[HKMA现行条款](https://www.hkma.gov.hk/eng/other-information/terms-and-conditions-of-use/)本次HTTP 200；旧`.shtml`链接重定向到此页。一般网站用途段12只准非商业显示/下载/准确复制；API附加条款另明确允许为商业或非商业软件、应用、系统搜索、显示、分析、检索信息，仍引用12(a)–(e)条件：依法使用、准确复制、注明HKMA及其知识产权、应要求销毁/停止，并要求终端用户遵守条款。第三方材料权利不自动授予、资料按AS IS提供。此次本机个人准确署名研究可据API条款推进；不能泛化为所有HKMA网页、第三方内容或对外再分发均获许可。

## ECB：已真实返回的替代官方FX路线

[官方API概览](https://data.ecb.europa.eu/help/api/overview)与[官方示例](https://data.ecb.europa.eu/help/api/data-examples)本次均HTTP 200，列明SDMX程序访问、币种`+`合并、`startPeriod/endPeriod`和CSV输出。此次只发一个数据GET，不需要账号、API key或cookie：

```text
https://data-api.ecb.europa.eu/service/data/EXR/D.HKD+CNY.EUR.SP00.A?startPeriod=2026-09-01&endPeriod=2026-09-30&format=csvdata
```

实际HTTP 200，`Content-Type: text/csv`，HTTP Date `Tue, 06 Oct 2026 04:00:28 GMT`。原始响应SHA-256为`8098f299c570e8bf40f4a565b6b4aa7907eeafc08484d667f9a40070fcdec521`。共44个观察值：`EXR.D.CNY.EUR.SP00.A`与`EXR.D.HKD.EUR.SP00.A`各22行，各自最小2026-09-01、最大2026-09-30；两组9月30日均有实际值、`OBS_STATUS=A`、`UNIT_MULT=0`、`DECIMALS=4`，币种单位分别CNY与HKD。完整逐日配对/港股交易日覆盖、历史修订及入库仍待执行，不能把行数等同最终估值验收。

公式必须使用**同一个ECB观察日期、同一EUR基准**：

```text
HKD per CNY = (HKD per EUR) / (CNY per EUR)
CNY per HKD = (CNY per EUR) / (HKD per EUR)
人民币参考价格 = 港元价格 × CNY per HKD
```

[官方参考汇率说明](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)本次HTTP 200，明确所有货币以EUR为基准，通常工作日约16:00 CET更新、约14:10 CET进行中央银行协商，TARGET休市日例外；仅供信息参考，强烈不建议用于交易。它不是香港CAS收盘同瞬时报价；欧洲发布时点通常晚于香港收盘，历史研究必须核对当时实际可知时间，不能只按日期倒填到香港收盘前的知识截止。官方当前页面也提供CNY、HKD及历史下载入口。

[ECB版权及免责声明](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html)本次HTTP 200，允许免费使用直接取得的信息；分发/复现须准确并注明ECB，修改或计算须明确说明；收费文档须告知可在ECB免费取得。具名论文等另有例外，不能借此泛化作者作品许可。ECB不保证资料适用于特定用途。本项目可采用“ECB官方两币种参考汇率交叉计算”的独立来源政策，原始两列与加工结果分开，保留观察日期、首次可知时间、原文hash及署名；本次未登记来源、未写库、未修改既定同日/FINAL政策。

## 港股：已核验的免费条件与停止点

| 主来源/请求 | 实际结果与权限 | 对本次两标的的处置 |
|---|---|---|
| [富途权限与额度](https://openapi.futunn.com/futu-api-doc/intro/authority.html) | HTTP 200、官方v10.11正文：无需开户限制，可牛牛号/已有手机号邮箱登录OpenD；首次使用仍需问卷与协议确认。API权限不等于APP；港股证券境内认证客户免费LV2、国际客户免费LV1，按OpenD登录IP区分；未开户且资产<1万HKD也有100标的历史K线额度、滚动7天每只占1。 | 若已有账号且实际权限/已完成合规与使用协议允许本机保存分析，可做仅行情最小取样；不为此新注册、开户、入金、改IP或购买。额度不等于保存/再分发许可，用户账号实际权限未验证。 |
| [富途历史K线](https://openapi.futunn.com/futu-api-doc/quote/request-history-kline.html) | HTTP 200；参数可固定start/end与日K，默认`AuType.QFQ`前复权，返回`close`及港股北京时间。 | 条件满足后分别`HK.01211`、`HK.09969`，2026-09-01…09-30，日K显式不复权，最大40行；逐条核对身份/日期/币种/原始close，失败停止。官方一般代码规则与接口存在不等于已实取两标的。close先作参考价，不自动升为CAS FINAL。 |
| [HKEX使用条款§5](https://www.hkex.com.hk/Global/Exchange/Terms-of-Use?sc_lang=en) | HTTP 200，页面标记2025-08-19更新；个人有限显示/存盘之外，明确禁止未经书面许可的程序访问、系统性建库、数据挖掘/抓取及相关AI用途。 | 未调用其网页报价、历史价格或隐藏行情接口；官方公开可浏览不等于本系统自动采集许可。 |
| [Yahoo现行条款](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) | HTTP 200；明确未经express prior permission不得用自动设备、程序、算法从服务取得/收集数据。 | 未发chart/download证券请求、未取cookie/crumb，未使用yfinance或其他客户端绕过来源权利判断。 |
| Stooq公开入口/条款候选 | `https://stooq.com/`、`https://stooq.com/t/`、`https://stooq.pl/t/`本次均404。 | 没有成功读到当前许可或取得两只港股覆盖证据；不能凭第三方库支持或旧URL承诺“免费无账户已可用”。 |

Twelve Data、Alpha Vantage、DataCedar、TabQuant等此前候选未在本次注册或调用Key接口，旧说明继续以[续查](./hk-free-source-followup.md)为准；不会把免费账户的营销覆盖或SDK开源许可证当成港股报价权利。

## 可执行收口路线

1. FX可推进独立ECB适配：取得上述一个44行公开响应，只在本机忽略目录保留原始证据；核对两组逐日交集、观察状态/单位、港股交易日与实际可知时间，交叉计算并显式标注ECB加工。先验证参考研究；原已发布政策是否准许这种欧洲时点参考FX用于正式估值须按当前政策确认，不能静默替换HKMA或降低FINAL门。
2. 港股若用户已持有富途登录账号，先由本人在本机确认已有API合规及实际港股行情权限、保存/分析协议，再用OpenD只读行情取两标的限定30日日K；无需证券开户或密钥发聊天。若没有已可用账号/合法来源，本次仍停在港股价格缺口，没有免账号可用源的实证；不把注册一把未经验证的Key作为已完成方案。
3. 对任何真实bar先验证券身份、币种、日期、复权类型、合法留存与错误返回；同日FX必须实际配上，先保持REFERENCE。CAS FINAL政策、市场批准日历、seal均未由本次文档研究完成。

本文是来源研究证据，不是产品接入、真实入库或完整必选验收。没有改代码、schema、访问权限、生产配置、正式政策或历史原文。
