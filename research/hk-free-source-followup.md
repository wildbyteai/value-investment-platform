# 港股免费渠道续查

核查日期：2026-10-06；代码基线 `25f0659a228c1eda0a77f4536a9a3e1e756e8690`。延续比亚迪 A/H、格力 A 和近30天范围，仅查公开官方文档、条款与供应商覆盖页；未注册、采购、接受账户协议、调用证券行情或写真实库。research 技能的子 Agent 两次因服务拥堵未启动，以下由当前会话核查，不是独立评审结果。

## 结论与候选

EODHD 密钥已有效，但它的实际官方交易所列表不包含 HK，这一步已有真实请求证据，不能用付费升级建议替代覆盖证明。以下候选也未通过真实港股取样验收；不存在“查到免费产品即已接通”的结论。

| 候选 | 官方证据与实际限制 | 当前处置 |
|---|---|---|
| 富途 OpenAPI | [历史K线](https://openapi.futunn.com/futu-api-doc/quote/request-history-kline.html)实际正文包含港股代码、北京时间、close及复权参数，默认前复权，后续必须显式不复权。[权限与额度](https://openapi.futunn.com/futu-api-doc/intro/authority.html)官方索引说明 API 权限与 APP 不完全一致，首次登录须完成问卷及协议；本轮该权限页正文抓取超时，未据搜索片段断言用户可免费取港股日线。 | 若用户已有富途账户，先核验其实际行情权限与历史额度、协议，再用行情只读权限取样；不为此新建证券账户，不接交易权限。 |
| 老虎 OpenAPI | [官方SDK](https://github.com/tigerfintech/openapi-python-sdk)说明开户并入金后可免费使用API。[费用与权限](https://quant.itigerup.com/openapi/zh/python/permission/feePermission.html)官方索引说明API行情与APP独立、部分港股L2权限按大陆IP赠送；正文请求超时。 | 仅作为已有账户候选；不能把“API免费”理解为全部行情免费，也不改变代理/IP来获得地区权限。 |
| IBKR | [现行官方FAQ](https://www.interactivebrokers.com/docs/third-party-integrations/general-third-party-frequently-asked-questions)实际正文明确：API历史bars需流式Level 1订阅，试用账户不能取得大多数证券的历史K线。 | 不能推荐为无需账户的免费港股历史源；已有账户仍核验订阅。 |
| Twelve Data | [香港市场页](https://twelvedata.com/exchanges/XHKG)实际标注Pro+/Venture+，试用标的是1299；[免费Basic](https://twelvedata.com/pricing)包括美国/FX/加密货币与全球试用标的，不是全部香港股票。 | 不建议为了比亚迪1211先申请免费Key；市场覆盖与免费额度不能混为一谈。 |
| Alpha Vantage | [官方文档](https://www.alphavantage.co/documentation/)确有未复权日线和全球证券搜索；本轮正文没有Hong Kong或.HKG匹配，未核实比亚迪港股身份/覆盖。 | 不能据“global”重复承诺HK可用；无密钥或真实身份回读，不推进取价。 |
| DataCedar | [香港市场](https://datacedar.com/markets/hkex)与[API文档](https://datacedar.com/docs)声称免费Explorer提供一年日线，需要账户Key；支持带交易所身份及raw参数。[条款§4–6](https://datacedar.com/terms)允许内部研究及合理保留结果，禁止复制档案/转分发，第三方权利仍适用。覆盖页同时显示没有足够历史进入sitemap的HK符号页。 | 免费非证券账户候选，尚未验证1211实际bars、上游出处/权利和最终性；不能要求用户再注册一把未经取样证明可用的Key或宣称接入已完成。 |
| TabQuant | [数据目录](https://tabquant.com/datasets?lang=en)将hk_daily列为free、标注港股通范围及2026-03起积累，API需Key；来源只写hk_spider。其[条款](https://tabquant.com/terms)允许个人研究/内部应用、禁止原值转分发。 | 未核实其报价上游授权与1211真实返回，不将许可其软件使用等同报价权利完整。 |

没有使用 HKEX 明确限制程序化系统提取的网站作为自动行情来源，没有用腾讯/新浪/东方财富公开报价或 AKShare 代码许可跨过来源门，也没有把供应商日线 close 升为 CAS FINAL。本轮没有港股价格或FX写入。

## 日历与股份的独立进展

[深交所2026中秋/国庆休市通知](https://investor.szse.cn/disclosure/notice/general/t20260917_622911.html)的官方索引正文给出9月25–27日及10月1–7日休市、10月8日开市；本轮直接正文请求超时。[网站法律声明](https://www.szse.cn/application/laws/)官方正文允许非商业浏览/下载并保留其他权利。该通知是日历候选依据，尚未作为固定可读修订入库或批准版本；不能只凭节假日列表推导每个挂牌的完整最终交易时点。

两家公司更新股数公告的搜索未得到本轮可固定入库的巨潮原件；其他网站摘要和月份标签不能证明普通股已发行数、库存股变动及证券同权范围。现有比亚迪报告日覆盖门和格力已知期后到期门保留。对历史价格，后来取得的月报表也不能回填过去的知识截止。

最小下一步是用户已持有的官方行情访问方式（优先富途账户的行情权限），或有明确上游权利和1211真实覆盖的免费供应商访问方式。无需再次批准原两家公司/三年/本机追加范围，但账户注册、接受新协议及采购不在已授权自动动作内。用户无需把账号、密码或密钥发到聊天。当前经营rubric、股份、同日FX、批准日历及FINAL的缺口仍见[续建记录](../review/REAL-FINANCIAL-CONTINUATION.md)。

## 当前只读交付复核

本轮 GitHub `main` 再次回读确认为上述基线SHA，8766 API健康；在核验实际本机真实数据库位置后的只读事务中取得原researcher身份，仅HTTP GET读取已有研究与正式记录：两家公司各五指标仍有效，研究ID/manifest未变、状态partial、真实seal=0。证据在本机忽略目录 `local-data/verification/continuation-current-readonly.json`，没有新建研究或修改业务记录。166项测试及构建属于财务续建基线的已执行结果，本轮仅文档/只读研究，不重跑或宣称新的产品验收。
