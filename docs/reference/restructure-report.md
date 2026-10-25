# 仓库学习化整理记录

日期：2026-10-25。此次实际合并目录、迁移命令与运行状态，不调整寻峰策略。

## 当前布局

根目录只保留main.cpp、README.md两个普通文件。automation保存线上工具和AI自动化，dev保存构建与测试，data保存赛题与历史版本，docs保存学习资料；.github保存Git协作和规则模板。

开发入口改为python dev/run.py，线上入口改为python automation/judge.py。原根目录tools、tests、online_judge、versions、build、tmp已移入相应功能目录，不再保留根目录兼容副本。周期任务已更新新入口，浏览器profile和既有作品记录已迁移。

## 已完成

- 中英文README、五阶段学习路线和分层文档导航。
- 赛题目录说明、评分手算例子、源码调用关系与实验复现步骤。
- concepts / guides / reference / archive分层，历史旧路径保留导航。
- 六份历史文档原字节与六份源码归档均有清单，并保护Git换行行为。
- 自动化职责、MCP/应用工具边界和可迁移提示词；不导出本机任务与登录配置。
- 离线dev命令、文档链接检查、CI配置、贡献指南、问题与PR模板。
- 本机编辑器设置、profile、runs、虚拟环境与本地配置继续忽略。

## 本地验证

| 检查 | 实际结果 |
| --- | --- |
| dev/run.py check | 新路径核心检查通过：133项工具、15项判题器、9项对比、10项核心求解器测试，共167项 |
| dev/run.py smoke | 新路径26条合成例交互正常，3条合法零分，报告保留 |
| 完整策略诊断 | 整理前记录为13个测试方法、8个子用例失败，原始断言与源码保留 |
| 无Playwright的干净虚拟环境 | 133项工具测试通过，离线依赖声明得到单独验证 |
| Git换行过滤 | 12份受保护归档的过滤前后字节一致 |
| main.cpp | SHA256仍为fcd7096e113824a46532ead285299368507cc8ca3594dc9d9457e83ca9c31f82 |

诊断原始日志在本机dev/build/strategy-diagnostics.log，烟测报告在dev/build/smoke.json。这些本机产物不进入版本管理。诊断失败的含义见[已知限制](known-limitations.md)，没有删除或放宽原断言。

CI文件已配置新路径，尚未在GitHub runner上实际执行；本次没有推送、发布或上传作品，也未刷新榜单。76份C++文件哈希未变，86份有效元数据路径已更新。Git根级规则移入.github模板并安装到本地.git/info；独立目录的共享规则同时保留。

根据维护者选择，暂不设置许可证。未来路线见[ROADMAP](../ROADMAP.md)。
