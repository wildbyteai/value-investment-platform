# 编码准备收口记录

2026-10-01。基线75ec4c7dedfe9b2b516ed9ab96769b067b86910c。本轮为用户授权的编码前准备：正式设计与交接更新，产品没有启动。

资料接入补齐已写入04/05/06/07/14、字段真源与生成15、三份1.0 Schema、原创合成示例、T-44…49、17开发交接。新增阅读状态原型不处理真实文件、不调用API/模型/评分、不下载链接。真实参考输入及本地分析留在local-evidence，本轮Git材料不包含原表内容或网址。

字段生成和材料检查已通过，新增阅读状态原型11项交互/四视口检查通过，未观察到页面脚本错误或HTTP请求。检查输入以各报告source_sha256绑定当次工作树，运行时HEAD为上述基线；最终提交包含这些输入。编码前准备可以收口；启动实施、运行依赖锁定和实际DB分类核验属于M0，不是本轮已经完成的事实。11/12已确认业务合同不变，供应商/生产/真实模型与通知事项仍按阶段后置，不增加可选终审轮次。

编码入口与任务/依赖/停止条件以[17](../docs/17-coding-readiness.md)为准。历史终审与主原型检查保留，新增原型证据单独记录；真实产品T-01…49和T-UX签收未运行。


## 验证记录

- `python3 tools/render_database_design.py`：生成79表、801字段设计字典；字段/FK目标/唯一键字段引用检查通过；没有SQL。
- `python3 tools/validate_design.py`：当前材料检查通过，精确检查数和输入hash见[结果](./validation-result.json)。新增DTO正例/负例和目录一致性检查是离线材料验证，不是运行适配器。
- `node tools/verify_intake_prototype.cjs <bundled Playwright> <Chrome>`：独立无头浏览器、HTTP拦截、本地file页面；11项合成阅读交互和1440/1280/390/430宽度检查通过。结果见[报告](./design-detail/intake-prototype-checks.json)，截图为桌面/手机首屏；不是目标用户测试。
- 原型首轮脚本名与浏览器全局`top`冲突导致页面未渲染，已改为局部名称并复验；第二轮原生select的Home键行为不符测试假定，改用真实按钮Enter/Escape验证键盘交互，未声称原生select全平台测试。失败报告保留为intake-prototype-failure.json、intake-prototype-failure-02.json。
- `python3 tools/build_review_pack.py`：同步整包及文本备用入口，包含编码交接；不发送外部评审，不包含local-evidence或真实Excel。
- `git diff --check`及目录生成回读通过；本轮只包含文档、Schema、原创合成示例、设计原型与检查工具。

未执行：完整draft-2020-12标准库验证、产品编码、实际解析/DB/API/worker/RBAC/评分/策略/事务/恢复测试、真实源与模型、真实用户/设备UAT、部署与通知。材料检查器只覆盖实际使用的保守Schema子集；标准Schema验证器集成与OpenAPI客户端生成属于M0，不因本地未装该库新增准备门槛。
