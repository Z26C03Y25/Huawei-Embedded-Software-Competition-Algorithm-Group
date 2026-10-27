# 版本与正式反馈

[返回首页](../../README.md) · [字节校验清单](manifest.json) · [实验目录说明](online_search/README.md) · [复现指南](../../docs/guides/reproduction.md)

本页分数是已记录的正式反馈，不是本地重放官方隐藏数据的结果。当前入口采用2026-10-27最高正式字节；历史分数保留对照。已评分源码保持原字节，新实验创建新文件。

| 源文件 | 说明 | 已知正式总分 |
| --- | --- | --- |
| [main_online_205415.cpp](main_online_205415.cpp) | 2026-10-27 保留原前探目标并加一个途中查询 | **205415** |
| [main_online_205376.cpp](main_online_205376.cpp) | 2026-10-27 粗扫结构改进正式最高分 | **205376** |
| [main_online_203239.cpp](main_online_203239.cpp) | 2026-10-26 最高正式分归档 | **203239** |
| main_online_199291.cpp | 2026-10-25 持续线上优化的最高分归档 | **199291** |
| main_v1_154353.cpp | 已评分首版归档 | 154353 |
| main_v2_145904.cpp | 已评分第二版归档 | 145904 |
| main_strategy_159487.cpp | 用户本次反馈的分层算子策略，原样归档 | 159487 |
| main_trend_153592.cpp | 平坦期限与趋势显著性两项修正，线上任务已确认完成 | 153592 |
| main_before_strategy.cpp | 本轮改造前实际 main.cpp 原样备份，与上述两份均不同 | 未映射，不能套用归档成绩 |
| 仓库根目录 main.cpp | 与 main_online_205415.cpp 完全一致 | **205415** |
| main_flat199_candidate.cpp | 单独修改平坦期限的消融候选 | 未评分 |
| main_trend_candidate.cpp | 与 main_trend_153592.cpp 相同的开发副本 | 153592 |
| main_frontier_candidate.cpp | 多项失败/有限收益实验，保留用于消融，不推荐提交 | 未评分 |

归档 SHA256：

- main_online_203239.cpp：b9f585fcbc25c3428ce7d9dd92f22e6e1d0cf88534c3244e0017b2eb222311cc。

- main_v1_154353.cpp：7d0e2319335d2eabe1e48a453f84579079c8c538e4b0ac8b3f43379e1b1f7b74。
- main_v2_145904.cpp：39ab2920c8317a44c1015182914b139673ba131abe818382ed28dbef51d955c4。
- main_before_strategy.cpp：b0b2ff0bb4885dd0ed554782c0565476bba1803604d8128a68487f69e28b67dc。
- main_strategy_159487.cpp：d98855c0f56b0c302f939252804ac8e7b38080e39bd06d43014020f1a8877336。
- main_trend_153592.cpp：71ac5e827f6631d2e5ca00df353d4734109f0e17a40570b7f584f0b1c7eb596c。
- main_online_199291.cpp：fcd7096e113824a46532ead285299368507cc8ca3594dc9d9457e83ca9c31f82。

历史：2026-10-25 00:12:46（北京时间）的作品 16805a26530b44db85b8f24bca5bb828 为 153592，低于 159487 基线。

历史最高（10月25）：2026-10-25 01:27:22（北京时间）的作品 ea00d99014aa450482173b08f51c74d1 已连续两次确认 success / 199291。本地任务 20261024T172719777020Z_53694d04f1bf 已完成。今日 30/30 次额度已用尽，最高源码已回存 main.cpp。

已评分源码不应原地修改。最新结果见 docs/持续线上优化总结.md，逐次正式分数见 docs/持续线上优化记录.md。其余旧候选文件保留作历史对比。

历史：2026-10-26 02:50:12（北京时间）的作品 9b7d32ca96b94c4aa7392a11bf02af02 已独立连续确认 203239。本日30次全部正式完成，官方30/30、剩余0。见[当日分析](../../docs/daily_research/2026-10-26-analysis.md)。

历史突破：2026-10-27 08:44:03作品0aeed21212f74e47b969b10cbf7e9389正式205376，已由恢复刷新后的普通查分流程连续确认。SHA256：bf7fa9d1d32233839783a5c743a332c831231de08cfb5c953e4fb30a4c08c5e2。

当前最高：2026-10-27 09:11:40作品869ab468dec54a2f9b113f1978ae71c9正式205415，已自动刷新连续确认。SHA256：827376b81ce389f67aa4aec450043eebec3cde801c914dbdf5c44bb52e390e37。
