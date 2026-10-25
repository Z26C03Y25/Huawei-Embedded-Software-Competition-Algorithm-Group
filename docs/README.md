# 文档导航

[返回首页](../README.md)

从“看懂题目”到“设计一次可检验的改进”，建议按下面顺序阅读。

## 入门路线

1. [原始赛题](../data/problem/README.md)：确认交互、评分及约束来源。
2. [问题与评分](concepts/problem-and-score.md)：用一条轨迹理解移动、冗余和停车。
3. [快速开始](guides/quickstart.md)：无账号、无浏览器，跑通真实管道交互。
4. [源码导读](concepts/solver-walkthrough.md)：按调用关系阅读单文件求解器。
5. [测试与诊断](guides/testing.md)：区分工具正确性与启发式性能。
6. [复现实验](guides/reproduction.md)：固定版本、配对曲线、解释收益与回退。

## 进阶资料

| 资料 | 用途 | 时效 |
| --- | --- | --- |
| [算子与分支设计](搜索算子与分支策略设计.md) | 特征、场景分类、96个设计项及约束推导 | 设计资料，部分建议尚未实现 |
| [持续优化总结](持续线上优化总结.md) | 199291版本参数、正式结果和已知失败 | 2026-10-25记录 |
| [逐次正式分数](持续线上优化记录.md) | 查实验、参数与源码哈希 | 自动记录入口 |
| [下一轮优化分析](下一轮优化分析.md) | 消融、边缘补查和后续队列 | 待验证方案 |
| [外部建议审查](外部优化建议审查.md) | 如何用代码和反例审查直觉优化 | 分析案例 |
| [榜单参考](榜单参考与后续目标.md) | 公开榜首与自身差距、缓存策略 | 快照有时间，不代表实时榜单 |

## 工程资料

- [2026-10-25离线研究与次日准备](daily_research/2026-10-25.md)

- [目录职责与依赖](reference/repository-map.md)
- [已知限制与研究问题](reference/known-limitations.md)
- [本次整理与验证记录](reference/restructure-report.md)
- [线上工具](../automation/online_judge/README.md)
- [自动化状态机](../automation/README.md)
- [MCP/应用工具接入边界](../automation/mcp/README.md)
- [贡献指南](../.github/CONTRIBUTING.md)

## 历史记录

[archive/](archive/README.md) 保存旧版分析、旧测试结果和早期笔记。原文中的“当前版本”指写作当时的版本。旧文档路径保留跳转导航，不能据此判断今天的源码状态。

最高正式源码以 [data/versions/](../data/versions/README.md) 的分数和哈希为准；现阶段入口与199291归档字节相同。
