# 独立项目迁移

日期：2026-09-30。状态：用户明确授权并完成。项目由BYTEWATCHER的BW-0051迁出，成为与其同级的独立项目；项目根目录就是Git根目录。

完整移动原独立checkout与.git，保留main、commit历史和wildbyteai/value-investment-platform remote，不创建另一份Git真源。原事项只留metadata与迁移指向，保留registry历史分配，ID不回收。事项关闭只表示移交完成，不表示产品开发完成。

本项目由PROJECT.md/README/AGENTS管理，不再依赖BYTEWATCHER事项路由、知识库控制面或内容生产流程。原事项元数据与本机迁移manifest放local-evidence并忽略Git，精确hash核对后持久保留。GitHub仓库保持原私有可见性，未改变真实数据/部署权限。

本次只改项目结构、入口与交接，业务、配置和关键Schema不因迁移改变。设计仍v0.2；先冻结迁移后的Git revision，再进行第二轮业务/工程复审与GPT Pro交接，评审建议不自动改业务合同。
