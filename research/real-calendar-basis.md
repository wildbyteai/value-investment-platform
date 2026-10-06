# 真实挂牌日历与收盘政策依据（有界核查）

核查日期：2026-10-06；源码起点 `6ca37557cead1aa576450ab34d06ffe14b72a6da`，工作树存在其他任务修改，未改动它们。范围仅为比亚迪 `HK.01211 / SZ.002594`、诺诚健华 `HK.09969`、格力电器 `SZ.000651`，2026-10-06 之后少量会话的准备依据。按 research 技能完成官方主来源研究；未委派、未调用 OpenD 网关、未查账户/持仓、未交易、未写库或修改代码/政策。原件和 SDK 源码捕获仅存 `raw-data/real-calendar-basis/`（Git 忽略），本文保存来源与结论。

**深市可以取得正式日期和精确竞价收盘 15:00 的规则依据；2026 新规则同时存在 15:05–15:30 的 A 股盘后固定价格交易，故不能把 15:00 直接称为所有交易终场。港股本次仅确认日历日期/全半日接口形状，仍不能取得逐日 CAS 精确终场和 FINAL 价格证明。** 不能为完成真实封存，静默把固定规则上界、供应商状态时段或 worker 当前时间写成 `final_market_at`。

## 1. 合同及当前字段

[docs/12 §2、§8](../docs/12-time-numerics-and-corrections.md)要求 primary Listing 的 exchange/currency/calendar_ref/close_policy；日历只确定 expected session 和市场时段，不证明价格 FINAL。`evaluation_as_of` 为批准会话的最终市场时点，固定知识截止为其后 60 分钟；日历/时点未知禁止封存，不能放宽截止。价格类型和输入冻结另行核对。

当前源码 `PrimaryListing.close_policy_json` 必须有 approved/price_kinds/evidence；`MarketSession.final_market_at` 必填，并保存 calendar_ref/session/ordinal/previous_session/evidence。`sealing_service.schedule` 按该时点生成截止，不把 future session 的存在当作已封存。字段存在不是批准日历或合法价格已通过。

## 2. 富途：接口形状已核实，真实会话响应未执行

已装官方 SDK 是 `futu_api==10.11.7108`，METADATA 指向 [官方源码](https://github.com/FutunnOpen/py-futu-api)，Apache-2.0 为 SDK 源码许可，不是市场数据许可。本次直接读源文件，未实例化行情上下文。SDK import 会初始化用户目录日志，本次一次 import 因沙箱阻止日志写入而失败，随后改为直接读源码，未解除限制或调用网关。

| 主来源 | 实际核对结果 | 能提供与不能提供 |
|---|---|---|
| [获取交易日历](https://openapi.futunn.com/futu-api-doc/quote/request-trading-days.html)及 `open_quote_context.py:139`、`quote_query.py` 的 `RequestTradeDayQuery.unpack_rsp` | 官方页 GET 成功；10.11 SDK 方法为 `request_trading_days(market=None,start=None,end=None,code=None)`，没有 `get_trading_days` 方法。成功返回 `(RET_OK,list[dict])`，每项仅 `time` 与 `trade_date_type`；失败为错误字符串。market/code 同时提供时忽略 market。 | 返回市场/标的日期及交易日类型；**没有 final_market_at、closing auction end、price_kind、is_final 或 source_revision**。本次没有请求 2026 实际日期，官方示例不是本次响应。 |
| [行情枚举：TradeDateType](https://openapi.futunn.com/futu-api-doc/quote/quote.html)及 SDK `constant.py:2098` | `WHOLE` 全天；`MORNING` 上午交易、下午休市；`AFTERNOON` 下午交易、上午休市。 | 没有 `HALF` 枚举；不能把半日硬编码成一个固定终场时刻。 |
| 同一交易日历页“介绍/接口限制” | 明确通过自然日剔除周末及节假日，**未剔除临时休市数据**；历史提供过去 10 年、未来仅到当年 12 月 31 日；每 30 秒最多 30 次。 | 可以提供 2026 剩余日期的候选计划；不覆盖临时休市，不保证未来实际开市/个股不停牌。 |
| [获取全局市场状态](https://openapi.futunn.com/futu-api-doc/quote/get-market-state.html)及 SDK `get_market_state` | 返回 DataFrame，只有 `code/stock_name/market_state`。`CLOSED` 枚举注释为收盘，`HK_CAS` 为港股盘后竞价。 | 当前供应商市场状态；不返回历史日期、状态切换的交易所精确时刻、最终价及修订水位。 |
| [行情 FAQ Q14](https://openapi.futunn.com/futu-api-doc/qa/quote.html) | 港股证券状态表实际写 `HK_CAS: CST16:00–16:08`、`CLOSED: CST16:08–次日08:55`；A 股表写竞价收盘后状态及盘后固定价格状态。 | 这是供应商枚举时段表，**不能把其16:08转换成每只证券每日CAS实际终场**；本文未自动访问 HKEX 验证随机终场或逐股 CAS 资格。 |
| [历史 K 线](https://openapi.futunn.com/futu-api-doc/quote/request-history-kline.html) | `close` 只定义为收盘价；返回 time_key、价格、量等。 | 官方返回字段未提供逐日 CAS 最终时点/最终价格类别标记或不再修订承诺。不能以过去日线存在、RET_OK、当前 CLOSED 或日历 WHOLE 自动升级 FINAL。 |

**港股最低停点**：两只证券的 HKD 柜台身份已由先前发行人原件核实，见[币种/权利研究](./futu-data-rights-and-currency.md)，但它不证明 CAS 适用名单及逐日终场。未来日期还未发生，无法仅按常规随机时段获得逐日实际终場；未来日期可捕获为候选计划，在补齐合法最终时点前不登记为可封存真实 `MarketSession`。本次没有新增 FINAL 证明，也未把常见 16:10 上界当作 docs/12 的最终市场时点。

## 3. 深交所：当前规则与 10 月最小日期范围

从官方公开规则页面实际显示的链接进入通知及 PDF，没有使用隐藏 API。通知[深证上〔2026〕551号](https://www.szse.cn/lawrules/rule/trade/current/t20260424_620190.html)发布于 2026-04-24，明确[《深圳证券交易所交易规则（2026年修订）》](https://docs.static.szse.cn/www/lawrules/rule/trade/current/W020260424690713155663.pdf)自 **2026-07-06** 起施行，并废止 2023 版。因此当前取样不能把 2023 规则称为现行依据。

| 条款、PDF页（与印刷页一致） | 正式规则 | 对 `final_market_at` 的含义 |
|---|---|---|
| §2.3.1，第6页 | 交易日为周一至周五，法定假日和本所公告休市日休市。 | 可与有界休市公告组成 expected session 日期依据，不能猜临时休市。 |
| §2.3.2–3，第7页 | 连续竞价9:30–11:30、13:00–14:57；收盘集合竞价14:57–15:00；可经批准调整时段；交易时间内因故停市不顺延。 | **精确竞价收盘政策可固定 Asia/Shanghai 15:00**，与港股随机 CAS 不同；仍需相应已批准收盘政策及异常市场检查。 |
| §4.2.3，第24页 | 收盘价原则上通过集合竞价产生；不能产生或未进行时取最后一笔前一分钟成交量加权价（含最后一笔），无成交取前收盘价。 | 能定义官方 `CLOSING` 类别和失败/无成交分支；不证明当前 Baostock/Futu 任一日 close 与该官方类别完全一致。停牌也不能仅用沿用值伪装正常有效 FINAL。 |
| §3.6.1–3，第20页；§3.6.8，第21页；§3.6.10，第22页 | 盘后固定价格交易覆盖 A 股与 ETF；15:05–15:30，以当日已形成收盘价撮合；交易结束后量额计入总量。 | **15:00 是竞价收盘价形成端点，15:30 是规则列明的盘后固定价格交易结束端点。** 若合同“最终市场时点”指全部市场交易结束，不能填15:00；若批准政策明确以官方竞价收盘价格形成端点为评估时点，才可据15:00。仅有本文不能代替该政策解释/批准。 |
| §10.3，第39页 | 规则时间以本所交易主机时间为准。 | 不能以客户端获取时间/第一条 CLOSED 观测替代官方端点。 |

[官方2026中秋节、国庆节休市通知](https://www.szse.cn/disclosure/notice/general/t20260917_622911.html)发布于2026-09-17，明确 **10月1日–7日休市，10月8日（星期四）起照常开市，10月10日（星期六）周末休市**。[深交所公开交易日历](https://www.szse.cn/aboutus/calendar/index.html)本次正常浏览显示2026年10月；它是辅助查看，不从颜色/class单独推断最终性。

可准备的最小日期范围为 **2026-10-08、10-09、10-12、10-13**，适用于已核验的 `SZ.002594` 与 `SZ.000651` 所属深市；是正式常规规则与本次节假日公告推得的 expected sessions，并非已发生市场终态。若只从10月9日起排两个相邻未来会话，可用10月9日与12日，且 previous_session 须包含已批准10月8日（9日前一个会话）、9日（12日前一个会话）；不能遗漏8日以伪造相邻关系。序号在固定 calendar_ref 中递增，周末不计漏评估。临时休市、时段调整和个股停牌在实际会话到期前单独核对。

时点准备必须二选一并记录合同依据：经已批准的竞价收盘政策，端点15:00+08:00（UTC07:00），cutoff16:00+08:00；若采用全部交易终场政策，规则端点15:30+08:00（UTC07:30），cutoff16:30+08:00。**本研究不自行选定或批准、不改 docs/12、不写真实库。** 若既有批准政策未解释此差异，暂停的是具体 `final_market_at` 登记，官方资料获取和候选日期准备已完成。

## 4. fetch / store / analyze 权利依据

- 富途公开文档与官方 SDK：仅获取接口说明/已装源码，未取得新行情。源码 Apache-2.0 不授市场数据权利。本轮仅本机保存研究原件和派生技术结论；实际四标的日历数据的 fetch/store/analyze 应复用用户本人确认的适用 API 范围，先确认其覆盖本次日历/深市，不能把已有“两只港股9月价格”范围自动扩成其他证券与资料用途。已有限定授权的主会话决定实际调用，本文未调用网关。
- 深交所[法律声明](https://www.szse.cn/application/laws/index.html)§3明确可基于非商业目的浏览、下载；未经书面许可不准以向他人出售牟利为目的使用内容。本文按已授权本机个人非商业研究有限取得公告/规则、保留原件并确定性提取日期/规则，不取得行情数据、不售卖或再分发原件，不外传模型。§1保留知识产权、§5不保证准确完整，不能据此扩大为商业/多人行情服务许可；来源元数据及本地研究结论可入Git，原件不入Git。
- 不自动访问 HKEX，沿用[前次核查](./official-fx-hk-recheck.md)的来源停点；未换IP、绕频率/身份、采集隐藏端点或读取账户协议。

## 5. 可执行最低方案与仍缺项

1. 主会话可复用本地深交所公告/现行规则原件：登记其 hash/具体页条款/真实取得时间与分析权利；给现有两只深市证券准备固定版本、2026年10月8–13日的有界 calendar_ref/expected dates。审批或数据写入另按已有授权执行，本文不是已入库证据。
2. 在现有合同内核定“最终市场时点”究竟是竞价收盘价端点还是全日交易结束端点，明确15:00/15:30及对应60分钟cutoff；避免借政策批准绕过docs12。只要已有批准政策清楚对应其中一个定义，不增加无谓审批；若不清楚则仅此解释是最低依赖。
3. 富途限定候选日历请求可用 `request_trading_days(start='2026-10-06',end='2026-10-13',code=...)`，恰四代码、每代码一次、保留 list 原响应/hash/actual observed_at。本次只验证官方形状，**没有2026实际响应**。拒绝非成功、错误类型/范围外/重复/未知枚举；不循环扩大范围。它不消除临时休市与HK逐日CAS停点。
4. 即使深市会话合法，未来未到 cutoff 仍只能 provisional；市场端点准确与价格 FINAL 分类各自校验。当前参考历史bars仍不升FINAL；可否正式生成缺价UNKNOWN，须在真实日历/时点/来源权利及其他安全合同均通过后由既有worker核验。
5. HK未来会话继续显式缺口：逐证券CAS适用/全半日对应规则、实际最终端点、合法FINAL价格类别及其修订/实际知识时间未齐。保持时点未知不可封存；本研究到此收口，不无限寻找替代来源。

## 6. 本地来源元数据

所有下列 GET 均由 `curl --fail` 成功落盘；HTML/PDF原件、文本提取、SDK源捕获和详细 `source-metadata.json` 均在忽略目录。下表时间是文件落盘UTC时间（不是网页首次发布时间，不回填 known_at）。

| 原件文件 | 落盘UTC | SHA-256 |
|---|---|---|
| futu-request-trading-days.html | 2026-10-06T08:00:26Z | `fcfbe09bb399830a87345f709ba76377b976277e65e6e30fd7ea1f97519d024a` |
| futu-quote-faq.html | 2026-10-06T08:00:27Z | `1f20c739c095bfdfa47667e9c46f4a3053c5cac1673a38757295342e1c3ba344` |
| futu-get-market-state.html | 2026-10-06T08:00:29Z | `12ea27bb2bf63dbc01b2d78114db64d2bc30d638217dd33463d6629b6b2dcfb0` |
| futu-request-history-kline.html | 2026-10-06T08:00:30Z | `7d391a160b076f84f7d1c85d5eee5fce486243cfc079b16dffd9e1501574dcb7` |
| futu-quote-enums.html | 2026-10-06T08:02:11Z | `0c0a7c8beea9348992230309bb30b6eb18331ec8ae22e0e6db69013ca5434727` |
| szse-rules-2026-notice.html | 2026-10-06T08:03:58Z | `08d05a9d3f9c7dac31e8ac33712bac26b3995585718031e99a953e9128eec2d2` |
| szse-trade-rules-2026.pdf | 2026-10-06T08:03:59Z | `9b66f8b0db70f84a25ef1ccb4ee2351001724e408117552d75f6d8993483c586` |
| szse-holidays-2026-oct.html | 2026-10-06T08:05:01Z | `7b0c4264d27f4ba14a1904ab31cb3b2b870e4e68d6b8d8c0f6cf4254c1a045a4` |
| szse-legal.html | 2026-10-06T08:03:59Z | `5398c463263421a98cbf90918dcaa16d6d70ef80f2052a9d0c19c1606ab27936` |

核验方式：官方正常浏览可见链接→限定GET；现行规则PDF采用`pdftotext -layout`及`pypdf`独立文本提取定位上述页码；SDK直接源码核对；原件sha256与ignore核对。未做产品测试或真实入库验收，不把研究/未来计划称作真实FINAL闭合。
