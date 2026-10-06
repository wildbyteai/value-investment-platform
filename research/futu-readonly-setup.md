# 富途已有账号：macOS 本机行情接入准备

主会话后续实际更新：用户表示设置说明不易理解，已从官方动态下载入口下载10.11.7108 Mac包到本机忽略目录并用macOS原生tar解压；`codesign --verify --deep --strict`和`spctl --assess`实际通过（Notarized Developer ID）。仅准备软件，未运行/登录/接受协议。可选SDK已安装且实际导入通过；两股显式接入实现与223项合成库验证见[FT接入记录](../review/FUTU-INTEGRATION.md)。下文“未下载”是研究子任务核查时点的动作边界，不是后续准备状态。

核查日期：2026-10-06。用户已确认有富途/牛牛账号；主会话开始时只读检查本机尚无11111监听、未见OpenD/SDK，后续主会话通知SDK安装已完成（本研究子任务未独立核验安装版本）。本文件基于富途官方v10.11文档与官方Python SDK源码作准备说明，不声称OpenD已安装、登录或已取到港股行情。本研究子任务只写本文件，未下载运行安装包、注册/登录/接受协议、读取凭证或私有账户资料、调用交易或写数据库。

## 最低依赖与网关边界

**不需要新账号或证券开户。** [官方权限页](https://openapi.futunn.com/futu-api-doc/intro/authority.html)明确可用已有牛牛号/注册手机号邮箱登录OpenD，首次API使用需要本人完成问卷和协议确认；APP行情权限不等于API权限。既有账号能否取到本次港股历史日K，仍以OpenD显示的权限和实际返回为准。未开户/资产少于1万HKD也有100标的历史额度，足够本次2只的限量请求；地区/IP条件不得通过改IP或代理绕过。

**没有查证到官方OpenD“服务端仅行情、禁用所有交易API”的配置。** [命令行配置与启动参数表](https://openapi.futunn.com/futu-api-doc/opend/opend-cmd.html)本次HTTP 200；完整表未列`enable_trade`、`disable_trade`、`disable_trd`或`quote_only`，有限官方站内检索也未取得支持依据。这是“未找到官方支持”，不推断未知版本一定不可能。

同一OpenD同时支持行情和交易；仅创建`OpenQuoteContext`是本客户端调用范围，不是网关权限隔离。[官方交易FAQ](https://openapi.futunn.com/futu-api-doc/qa/trade.html)明确模拟交易无需解锁即可下单、改单或撤单；所以“不解锁实盘”“只监听127.0.0.1”都不能等同服务端quote-only。没有可验证的纯行情官方配置入口，不能编造开关或替用户启动一个可能接受交易请求的已登录网关。**首次安装启动、本人登录和API合规确认由用户在本机完成**；此后本项目仅连其明确准备好的本机网关，执行限定行情请求，不创建交易对象、不查询持仓/账户、不解锁、不发模拟或真实交易。

## 官方下载与本人本机设置

1. 从[官方可视化OpenD安装页](https://openapi.futunn.com/futu-api-doc/quick/opend-base.html)的MacOS入口下载：[官方动态下载链接](https://www.futunn.com/download/fetch-lasted-link?name=opend-macos)。两者本次HTTP 200；下载链接仅做HEAD，当前重定向为`https://softwaredownload.futunn.com/Futu_OpenD_10.11.7108_Mac.tar.gz`，`Content-Type=application/octet-stream`、`Content-Length=416963581`（约398MiB）。未下载该文件，版本链接会变化，应使用官方动态入口而不是第三方重新打包版。
2. 本人解压官方包，保留随包配置与数据文件，在本机打开可视化OpenD；按官方安装页设置API监听地址为`127.0.0.1`、端口`11111`、日志级别`info`。只在本机使用，不填`0.0.0.0`或开启远程Telnet。可视化版通过WebSocket连接命令行组件，会启用WebSocket；其监听也限定本机，不能错误声称GUI完全关闭了WebSocket。
3. 本人用已有牛牛账号在OpenD界面输入凭证、完成必要验证。首次API登录若提示问卷/协议，阅读后由本人决定并确认，完成后重新登录。账号、密码、验证码、协议内容、截图和完整日志留在本机，不发聊天或入Git。不要点击交易解锁或运行交易示例。
4. 登录后查看**港股API行情权限及历史K线额度**。只需告诉项目操作者“OpenD本机已登录、127.0.0.1:11111可用、港股API权限/历史额度已显示”，不发送账号信息或持仓截图。若权限不足、协议不允许本机保留分析、登录失败或要求采购，停在对应步骤；不为此新开户、入金或购买。

若使用命令行版，官方配置键名与CLI参数不能混写：`OpenD.xml`中监听键是`ip`，默认`127.0.0.1`；`api_port`默认`11111`；CLI对应`-api_ip=127.0.0.1 -api_port=11111`。Telnet默认不启用，命令行WebSocket默认不启用。以下是**供本人操作的官方参数示例，未在本轮执行**：

```sh
# 在官方包解压目录，由本人操作；不把密码放命令行或配置示例
./OpenD.app/Contents/MacOS/OpenD -api_ip=127.0.0.1 -api_port=11111
```

[官方命令行页](https://openapi.futunn.com/futu-api-doc/opend/opend-cmd.html)说明10.10起直接启动默认进入交互登录；macOS路径变化可能影响同目录配置查找，可由本人用`-cfg_file`指定实际绝对路径。以上仅是本机监听配置，**不是禁交易配置**；不擅自执行随包脚本、记住密码参数、解除系统安全控制或修改账户权限。

## SDK与最小行情请求

[官方快速示例](https://openapi.futunn.com/futu-api-doc/quick/demo.html)本次HTTP 200，macOS安装包名是`futu-api`，Python导入名`futu`；官方支持`pip3 install futu-api`。主会话后续已报告SDK安装成功；实际包/OpenD版本以其本机验证记录为准。官方整段demo同时包含模拟下单，不能照抄执行；只使用行情对象与下列行情接口。

**先核证券身份，后取日K，固定两代码。** [官方基本信息文档](https://openapi.futunn.com/futu-api-doc/quote/get-static-info.html)和[官方SDK源码](https://github.com/FutunnOpen/py-futu-api/blob/master/futu/quote/open_quote_context.py)本次均可实际读取HTTP 200。调用应是：

```python
from futu import OpenQuoteContext, Market, SecurityType, KLType, AuType

quote = OpenQuoteContext(host="127.0.0.1", port=11111)
try:
    ret, info = quote.get_stock_basicinfo(
        Market.HK, stock_type=SecurityType.STOCK,
        code_list=["HK.01211", "HK.09969"],
    )
    # 必须先核对ret、恰好两行、身份及下述停点；此处不自动接受info。
    # 身份/币种/来源保存分析权限通过后，分别调用：
    # ret, bars, next_key = quote.request_history_kline(
    #     code, start="2026-09-01", end="2026-09-30",
    #     ktype=KLType.K_DAY, autype=AuType.NONE, max_count=40,
    #     page_req_key=None, extended_time=False,
    # )
finally:
    quote.close()
```

这是接口参数示例，未运行、不保存数据或生成产品验收结论。实际取得原始响应后仅留本机忽略目录，常规输出只记成功状态/日期覆盖/行数/原文hash，避免直接输出OpenD登录信息或完整连接日志。

**个人存储/分析权利与行情权限分开。** 本次实际读到的[官方权限页](https://openapi.futunn.com/futu-api-doc/intro/authority.html)支持已有账号获得相应API行情及历史额度，[历史接口](https://openapi.futunn.com/futu-api-doc/quote/request-history-kline.html)支持取得历史bars；它们不是明示永久留存、企业应用、再分发或外部模型分析的许可。本次没有登录账户或接受协议，也没有实际取得本人适用的API问卷/行情协议全文，**个人本机保留与确定性分析的具体授权条文仍不可确认**；SDK源码公开/可安装也不授予市场数据使用权。后续本人首次合规步骤须核对所接受协议的个人研究与存储范围，记录适用协议版本/条款依据，才能将有限原始bar保存在本机；不允许从“免费LV1/LV2”推断组织共享、商业服务、再分发或模型外发权利。本项目的本机保留/不入Git/不外发措施限制使用范围，但它们本身不补足上游许可。

基本信息核对须检查：返回代码集合恰为两只、比亚迪/诺诚健华的发行人名称及既有证券映射、`stock_type=STOCK`、`exchange_type`为相应香港交易所挂牌、`delisting=False`、有效`stock_id`，不能以请求入参代替实际回读。官方注明：未知/不存在证券可能仍成功返回占位行，名字“未知股票”、退市标志及其他默认值；因此`ret==RET_OK`本身不能证明身份。传入`code_list`时`market`会被忽略；必须检查回读的`HK.`前缀及交易所，不能以参数`Market.HK`作证据。`listing_date`已停止维护，不用于正式挂牌历史依据。

**基本信息不返回币种。** 官方SDK的`get_stock_basicinfo`输出列与文档均没有`currency`；[快照文档](https://openapi.futunn.com/futu-api-doc/quote/get-market-snapshot.html)本次HTTP 200，也未列证券报价币种。不能伪造`info['currency']`、用“HK股票一律HKD”假设覆盖双币柜台，或把交易账户币种当证券报价币种。本次01211/09969需要从已核实的发行人/挂牌交易币种原件等独立官方证据确认港元，并绑定本次精确证券代码；缺证据则保留币种门，不能为拿币种扩大到私有账户查询。

候选[HKEX官方证券列表XLSX入口](https://www.hkex.com.hk/eng/services/trading/securities/securitieslists/ListOfSecurities.xlsx)本次**未请求或下载**，没有可达状态或两代码币种回读。[此前实际核查的HKEX条款§5](https://www.hkex.com.hk/Global/Exchange/Terms-of-Use?sc_lang=en)限制未经其书面许可的程序/脚本访问网站Information与系统性提取；公开文件链接不能自动补足这项权利。未取得此文件特定自动访问许可，故保留来源停点，不通过隐藏接口、其他镜像、代理或改文件获取方式绕过。币种依据须明确对应当前报价/交易柜台；发行价曾以HKD计、公司注册资本或账户结算币种为HKD，都不等于精确挂牌当前报价币种已确认。客户端可保留“行情已捕获、币种/保存权限门未通过而不可入库”的独立状态，不把缺证据字段填为HKD。

[官方历史日K](https://openapi.futunn.com/futu-api-doc/quote/request-history-kline.html)本次HTTP 200；默认前复权`AuType.QFQ`，必须显式不复权`AuType.NONE`（[官方行情枚举](https://openapi.futunn.com/futu-api-doc/quote/quote.html)本次HTTP 200明确该含义）。固定2026-09-01…09-30、`KLType.K_DAY`、最多40行；返回`code/name/time_key/close`等，港股时间默认北京时间。30日窗口如仍有下一页key、范围外数据、重复日、无数据、权限/身份错误等，先停止核查，不循环扩大范围。历史接口无需先下载K线或订阅实时报价；本次不启用轮询/回调/自动刷新。

## close与正式FINAL边界

官方历史接口只把`close`定义为“收盘价”，没有给该字段返回CAS定价状态、供应商纠错完成状态、最终版本水位或不可修订承诺。本次核查的历史接口、行情枚举、快照及FAQ没有取得足以证明两只证券每个日期`close`等于本项目批准CAS FINAL的官方定义。[行情FAQ](https://openapi.futunn.com/futu-api-doc/qa/quote.html)虽然介绍`HK_CAS`/`CLOSED`市场状态，它不是历史bars最终性证明，也不能把状态表固定时刻当成逐日交易所批准最终时点。

因此初次真实取样可作为**未复权REFERENCE日收盘参考资料**：固定供应商/OpenD版本、实际取得时间、精确证券身份、日期、币种、原始close、原始响应hash与权限依据。没有相应批准政策、最终性证据和市场日历，不标FINAL、不产生正式seal。独立同日FX可采用已实际通过的ECB两币种交叉参考路线，但必须保留其欧洲发布时间/实际知识截止；不能把港股价与欧洲当日晚间才知悉的FX回填为香港收盘前已知。

本次交付只完成官方设置与接口事实核查。最低下一步是用户在本机准备并登录OpenD，明确本机网关可供限定行情使用；交易API隔离、实际港股权限、原值取样、港元币种证据、许可保存分析及CAS FINAL并未由此文件自动验证或授权。
