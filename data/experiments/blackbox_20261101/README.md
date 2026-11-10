# 2026-11-01 线上结构优化

用户授权用完今日30次线上机会。后续禁止同代码复测；固定种子的随机策略可复现，改变规则或种子才是新候选。此前已投递的基线对照只取回原作品结果。以正式总分选择，本地仅检查编译、交互、Q/O和真实停车。未知结果恢复同一作品，不重复上传。

初始最高212686；当前最高216258。总分不能恢复逐例零分原因或数量。

| 候选 | 父版 | 正式总分 | 分差 | 采用 | 状态 |
|---|---:|---:|---:|---|---|
| cell_complete_model | 212686 | 211743 | -943 | False | completed |
| hybrid_random_hull | 212686 | 191736 | -20950 | False | completed |
| main_online_212686 | 212686 | 212686 | 0 | False | completed |
| anchored_random_audit | 212686 | 209783 | -2903 | False | completed |
| geometry_residual | 191736 | 184652 | -7084 | False | completed |
| skeleton_noise_audit | 209783 | 212243 | 2460 | False | completed |
| skeleton_expert_long | 212686 | 212321 | -365 | False | completed |
| flat_random_burst | 212686 | 212686 | 0 | False | completed |
| optimistic_interval_refine | 212686 | 191562 | -21124 | False | completed |
| viability_parking_v2 | 212686 | 212686 | 0 | False | completed |
| skeleton_expert_mid | 212686 | 212624 | -62 | False | completed |
| early_rebound_pilot | 212686 | 210233 | -2453 | False | completed |
| halve_postpeak_scout | 212686 | None | None | False | 排除误归属；本候选成绩未确认，不重传 |
| wide_cruise_scan | 212686 | 212354 | -332 | False | completed |
| compact_fine_routes | 212686 | 212535 | -151 | False | completed |
| validated_quadratic_stop | 212686 | 212686 | 0 | False | completed |
| marginal_signal_tail_guard | 212686 | 212686 | 0 | False | completed |
| doubao_casefix | 212686 | 191308 | -21378 | False | completed |
| prefix_complete_audit | 212686 | 208572 | -4114 | False | completed |
| resolved_descent_half_scout | 212686 | 216233 | 3547 | True | completed |
| resolved_descent_long | 212686 | 213161 | 475 | False | completed |
| median_descent_stop | 216233 | 216233 | 0 | False | completed |
| dense_midpoints_current | 216233 | 216114 | -119 | False | completed |
| doubao_resolved_coarse_v2 | 191308 | 204728 | 13420 | False | completed |
| renew_rising_frontier | 216233 | 216233 | 0 | False | completed |
| right_width_stop | 216233 | 216258 | 25 | True | completed |
| wide_expert_long | 216258 | 216217 | -41 | False | completed |
| stratified_long_grid | 216258 | 211218 | -5040 | False | completed |
| compact_expert_noisy | 216258 | 216051 | -207 | False | completed |
| median_frontier_lease | 216258 | 216258 | 0 | False | completed |

已确认有效机制：在两侧半高点均已读到、最近至少三次显著下降且无上升/回升时，才缩短峰后探测。正式总分216233，相对212686提高3547；不能仅从总分确定哪些样例或哪一项扣分改善。

互斥N分组：N>650已直接测得贡献+475；N<=650合计条件推断+3072。条件推断利用相同基线和仅按N启用的确定性策略，不等于逐例成绩；后续不同机制的组合收益仍须实测。

结束时实时核对：30/30，剩余0次；记录时间2026-11-01T08:11:13+08:00。不为恢复最后上传文件而复测最高分源码。

归属更正：2026-11-01 02:04:15 的146180分由用户明确说明为其手动实验，已从正式成绩索引及候选拟合中剔除。不能据此判断减半探测成功或失败；宽缓上升节省查询实验是独立候选。原观察与源码保存在 attribution_rejections 中，不修改源码字节。

豆包代码测试：修正版正式总分191308，相对212686差-21378。保留[用户原文](doubao_original.cpp)；[测试版本](doubao_casefix.cpp)只修正case3..6为合法switch分支，并处理告警，不重新设计其采样或评分。四处分支修正会改变执行行为，不能将这个分数称作未经修改原文的成绩。

源码审查发现：transientSpikes只收录已读位置，但pool.add在已读位置直接返回，且所有调用均未传transient=true，所以毛刺降权条件无法命中；弱证书只记录级别、没有停止作用；候选覆盖分支的(i*candidates.size())%candidates.size()恒为0。这些是可由源码确定的实现问题，不能由总分断言各自造成多少损失。

待确认：[]

[最高分入口](../../../main.cpp) · [前一日结果](../blackbox_20261031/README.md)
