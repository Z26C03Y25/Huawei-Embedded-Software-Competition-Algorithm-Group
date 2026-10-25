# 离线研究与次日候选

[数据导航](../README.md)

[research_state.json](research_state.json)指向最新已完成研究、当日额度确认日期与次日队列。跨北京时间日期后必须重新核查官方次数，不能把旧的0永久缓存。

每批候选与可分享摘要按日期存放。正式分数为null表示尚未线上判分；离线改善不能覆盖已评分的最高版本。

- [2026-10-25研究记录](../../docs/daily_research/2026-10-25.md)
- [批次A摘要](2026-10-25/batchA_summary.json)
- [次日候选队列](2026-10-25/next_day_queue.json)

完整曲线与轨迹报告保存在本机dev/build/research，按相邻run_batch.py可离线重建。代码、参数、数据分组与实际执行时机共同定义一个实验，改变输入需要建立新批次。
