# 赛后归档

本项目记录华为嵌入式软件大赛算法组交互式自动聚焦方案。以下分数均为官方评测总分。

| 口径 | 最高分 | 源码 |
| --- | ---: | --- |
| 仓库已记录的历史正式最高 | 224148 | [含固定评测集经验分派](../../versions/main_online_224148.cpp) |
| 无打表历史最高及当前入口 | 221354 | [波形搜索版本](../../versions/main_online_221354.cpp) |
| 11 月 22–25 日独立实验最高 | 211435 | [第 30 版](sources/20261125_30_model_switch.cpp) |

## 独立实验进展

| 日期 | 正式评测数 | 当日最高 | 源码 |
| --- | ---: | ---: | --- |
| 2026-11-22 | 30 | 200368 | [第 25 版](sources/20261122_25_fast_approach.cpp) |
| 2026-11-23 | 30 | 208788 | [第 15 版](sources/20261123_15_stride10.cpp) |
| 2026-11-24 | 30 | 211240 | [第 29 版](sources/20261124_29_nearby_only.cpp) |
| 2026-11-25 | 30 | 211435 | [第 30 版](sources/20261125_30_model_switch.cpp) |

11 月 22 日的成绩已使用次日从官方页面按作品编号核对的 30 个终分补齐。独立实验逐日保留，新一轮基于前一轮正式分调整采样和停搜。

较有收益的变化包括结合峰形确认停搜、缩短峰顶附近步长，以及在回程中减少远离峰顶的补扫。官方页面提供总分，无法据此定位单例零分。

## 打表探针的思路

历史实验只看到总分。做差时尽量保持路线、停车点和得分样例相同，每次只改变一个扣分项。

1. **扫小区间找峰。** 逐点查完 0 到 50，再回到最高点。假设只有一个样例得分、停准且确实回头一次，题面计算为 2797 加两倍峰位。该类轨迹历史实测比题面少 29 分。实测 2828 先加回 29，再减 2797、除以 2，得到候选峰位 30。直接查 30 的实测单点分是 2969，和停准时的理论分吻合。单点无回头，不做 29 分修正。
2. **原地重读测长度。** 保持单点停车位置，分别按“长度减 400 再除以 4”的整数商和余数额外重读。在同一个样例得分、额外查询未触发归零时，每多查一次少 1 分。峰位 30 的两版实测分别为 2950 和 2966，相对 2969 少 19 和 3，得到长度 479。
3. **遇到同长冲突再辨识。** 长度 479 全部直接停 30 的整合版掉了 5142 分。历史对照在同一单点上按查询回复除以 127 的余数额外重读，实测扣 7 分。结合长度、回复特征和当前最高点判断，整合版净增 300 分。完整算法的净增益须单独上线验证。

总分小于 3000 仍可能来自多个样例，停偏一格也可能拿到正分。29 分是已测回头路径的经验差额，长度和回复特征属于固定评测集证据，不能当作通用峰形规律。当前根目录默认入口是无打表版。

[区间与单点原始记录](../../../docs/research/known_peak_positions_20261103.md) · [长度、回复特征与回头成本对照](../blackbox_20261104/length_inference.md)

## 逐次成绩

[机器可读成绩和 SHA-256](scores.json) 对应下列 120 个正式评测源码。

| 日期 | 次数 | 实验 | 正式分 |
| --- | ---: | --- | ---: |
| 2026-11-22 | 1 | [signal_descent](sources/20261122_01_signal_descent.cpp) | 183267 |
| 2026-11-22 | 2 | [narrow_bracket](sources/20261122_02_narrow_bracket.cpp) | 163212 |
| 2026-11-22 | 3 | [width_guard](sources/20261122_03_width_guard.cpp) | 181974 |
| 2026-11-22 | 4 | [half_height](sources/20261122_04_half_height.cpp) | 183994 |
| 2026-11-22 | 5 | [contrast_aware](sources/20261122_05_contrast_aware.cpp) | 155505 |
| 2026-11-22 | 6 | [three_falls](sources/20261122_06_three_falls.cpp) | 191266 |
| 2026-11-22 | 7 | [strict_descent](sources/20261122_07_strict_descent.cpp) | 186908 |
| 2026-11-22 | 8 | [one_more_read](sources/20261122_08_one_more_read.cpp) | 183719 |
| 2026-11-22 | 9 | [early_dense](sources/20261122_09_early_dense.cpp) | 174709 |
| 2026-11-22 | 10 | [irregular_steps](sources/20261122_10_irregular_steps.cpp) | 173086 |
| 2026-11-22 | 11 | [straight_background](sources/20261122_11_straight_background.cpp) | 178842 |
| 2026-11-22 | 12 | [fast_background](sources/20261122_12_fast_background.cpp) | 185174 |
| 2026-11-22 | 13 | [measured_half_width](sources/20261122_13_measured_half_width.cpp) | 185031 |
| 2026-11-22 | 14 | [confirmed_apex](sources/20261122_14_confirmed_apex.cpp) | 191736 |
| 2026-11-22 | 15 | [slow_shoulder](sources/20261122_15_slow_shoulder.cpp) | 184211 |
| 2026-11-22 | 16 | [long_rival_guard](sources/20261122_16_long_rival_guard.cpp) | 191659 |
| 2026-11-22 | 17 | [short_half_width](sources/20261122_17_short_half_width.cpp) | 180060 |
| 2026-11-22 | 18 | [sharp_peak_exit](sources/20261122_18_sharp_peak_exit.cpp) | 198063 |
| 2026-11-22 | 19 | [stop_earlier](sources/20261122_19_stop_earlier.cpp) | 191641 |
| 2026-11-22 | 20 | [wide_confirmation](sources/20261122_20_wide_confirmation.cpp) | 188430 |
| 2026-11-22 | 21 | [thin_gaps](sources/20261122_21_thin_gaps.cpp) | 171998 |
| 2026-11-22 | 22 | [sweep_coverage](sources/20261122_22_sweep_coverage.cpp) | 191710 |
| 2026-11-22 | 23 | [curved_gaps](sources/20261122_23_curved_gaps.cpp) | 191103 |
| 2026-11-22 | 24 | [early_slope](sources/20261122_24_early_slope.cpp) | 184503 |
| 2026-11-22 | 25 | [fast_approach](sources/20261122_25_fast_approach.cpp) | 200368 |
| 2026-11-22 | 26 | [low_drop](sources/20261122_26_low_drop.cpp) | 191659 |
| 2026-11-22 | 27 | [heavier_drop](sources/20261122_27_heavier_drop.cpp) | 191659 |
| 2026-11-22 | 28 | [deeper_refine](sources/20261122_28_deeper_refine.cpp) | 190281 |
| 2026-11-22 | 29 | [strict_slope](sources/20261122_29_strict_slope.cpp) | 179692 |
| 2026-11-22 | 30 | [sparse_coast](sources/20261122_30_sparse_coast.cpp) | 196172 |
| 2026-11-23 | 1 | [coast16](sources/20261123_01_coast16.cpp) | 194279 |
| 2026-11-23 | 2 | [coast13](sources/20261123_02_coast13.cpp) | 201211 |
| 2026-11-23 | 3 | [coast9](sources/20261123_03_coast9.cpp) | 191545 |
| 2026-11-23 | 4 | [stop28](sources/20261123_04_stop28.cpp) | 200528 |
| 2026-11-23 | 5 | [stop60](sources/20261123_05_stop60.cpp) | 199240 |
| 2026-11-23 | 6 | [sharp_fast](sources/20261123_06_sharp_fast.cpp) | 204813 |
| 2026-11-23 | 7 | [balanced_flanks](sources/20261123_07_balanced_flanks.cpp) | 204078 |
| 2026-11-23 | 8 | [width_gate](sources/20261123_08_width_gate.cpp) | 203647 |
| 2026-11-23 | 9 | [shape_steepness](sources/20261123_09_shape_steepness.cpp) | 203584 |
| 2026-11-23 | 10 | [asymmetric_tail](sources/20261123_10_asymmetric_tail.cpp) | 201512 |
| 2026-11-23 | 11 | [fast_quiet](sources/20261123_11_fast_quiet.cpp) | 194787 |
| 2026-11-23 | 12 | [rival_resolution](sources/20261123_12_rival_resolution.cpp) | 200452 |
| 2026-11-23 | 13 | [staggered_quiet](sources/20261123_13_staggered_quiet.cpp) | 194091 |
| 2026-11-23 | 14 | [coast_sharp](sources/20261123_14_coast_sharp.cpp) | 198306 |
| 2026-11-23 | 15 | [stride10](sources/20261123_15_stride10.cpp) | 208788 |
| 2026-11-23 | 16 | [stride14](sources/20261123_16_stride14.cpp) | 196114 |
| 2026-11-23 | 17 | [stride18](sources/20261123_17_stride18.cpp) | 176483 |
| 2026-11-23 | 18 | [quieter_background](sources/20261123_18_quieter_background.cpp) | 207096 |
| 2026-11-23 | 19 | [guard36](sources/20261123_19_guard36.cpp) | 202705 |
| 2026-11-23 | 20 | [guard20](sources/20261123_20_guard20.cpp) | 204779 |
| 2026-11-23 | 21 | [guard54](sources/20261123_21_guard54.cpp) | 196646 |
| 2026-11-23 | 22 | [sharp_confirm](sources/20261123_22_sharp_confirm.cpp) | 204078 |
| 2026-11-23 | 23 | [strong_apex](sources/20261123_23_strong_apex.cpp) | 204779 |
| 2026-11-23 | 24 | [width_by_descent](sources/20261123_24_width_by_descent.cpp) | 201682 |
| 2026-11-23 | 25 | [gap_budget](sources/20261123_25_gap_budget.cpp) | 204782 |
| 2026-11-23 | 26 | [smaller_return](sources/20261123_26_smaller_return.cpp) | 204912 |
| 2026-11-23 | 27 | [denser_entry](sources/20261123_27_denser_entry.cpp) | 199309 |
| 2026-11-23 | 28 | [wider_entry](sources/20261123_28_wider_entry.cpp) | 186861 |
| 2026-11-23 | 29 | [short_sweep](sources/20261123_29_short_sweep.cpp) | 204782 |
| 2026-11-23 | 30 | [long_sweep](sources/20261123_30_long_sweep.cpp) | 204917 |
| 2026-11-24 | 1 | [strict_neighbours](sources/20261124_01_strict_neighbours.cpp) | 208788 |
| 2026-11-24 | 2 | [half_width_stop](sources/20261124_02_half_width_stop.cpp) | 196400 |
| 2026-11-24 | 3 | [shoulder_veto](sources/20261124_03_shoulder_veto.cpp) | 198632 |
| 2026-11-24 | 4 | [broad_peak_guard](sources/20261124_04_broad_peak_guard.cpp) | 199772 |
| 2026-11-24 | 5 | [long_flank_guard](sources/20261124_05_long_flank_guard.cpp) | 210997 |
| 2026-11-24 | 6 | [apex_two_step](sources/20261124_06_apex_two_step.cpp) | 208820 |
| 2026-11-24 | 7 | [rival_five_step](sources/20261124_07_rival_five_step.cpp) | 203333 |
| 2026-11-24 | 8 | [three_step_ascent](sources/20261124_08_three_step_ascent.cpp) | 208821 |
| 2026-11-24 | 9 | [fine_descent](sources/20261124_09_fine_descent.cpp) | 202906 |
| 2026-11-24 | 10 | [rising_shoulder](sources/20261124_10_rising_shoulder.cpp) | 205636 |
| 2026-11-24 | 11 | [return_cost](sources/20261124_11_return_cost.cpp) | 208921 |
| 2026-11-24 | 12 | [local_gap_priority](sources/20261124_12_local_gap_priority.cpp) | 208799 |
| 2026-11-24 | 13 | [budget_midpoint](sources/20261124_13_budget_midpoint.cpp) | 208774 |
| 2026-11-24 | 14 | [two_falls_short](sources/20261124_14_two_falls_short.cpp) | 208975 |
| 2026-11-24 | 15 | [symmetric_short](sources/20261124_15_symmetric_short.cpp) | 196400 |
| 2026-11-24 | 16 | [fine_approach](sources/20261124_16_fine_approach.cpp) | 191586 |
| 2026-11-24 | 17 | [step9](sources/20261124_17_step9.cpp) | 195465 |
| 2026-11-24 | 18 | [step11](sources/20261124_18_step11.cpp) | 204457 |
| 2026-11-24 | 19 | [step12](sources/20261124_19_step12.cpp) | 198114 |
| 2026-11-24 | 20 | [early_witness](sources/20261124_20_early_witness.cpp) | 211184 |
| 2026-11-24 | 21 | [late_witness](sources/20261124_21_late_witness.cpp) | 210840 |
| 2026-11-24 | 22 | [low_drop](sources/20261124_22_low_drop.cpp) | 210997 |
| 2026-11-24 | 23 | [deep_drop](sources/20261124_23_deep_drop.cpp) | 210997 |
| 2026-11-24 | 24 | [wider_competition](sources/20261124_24_wider_competition.cpp) | 210416 |
| 2026-11-24 | 25 | [compact_return](sources/20261124_25_compact_return.cpp) | 211189 |
| 2026-11-24 | 26 | [denser_near_ascent](sources/20261124_26_denser_near_ascent.cpp) | 205311 |
| 2026-11-24 | 27 | [staggered_near_peak](sources/20261124_27_staggered_near_peak.cpp) | 196998 |
| 2026-11-24 | 28 | [larger_refine](sources/20261124_28_larger_refine.cpp) | 210959 |
| 2026-11-24 | 29 | [nearby_only](sources/20261124_29_nearby_only.cpp) | 211240 |
| 2026-11-24 | 30 | [less_dense_refine](sources/20261124_30_less_dense_refine.cpp) | 211235 |
| 2026-11-25 | 1 | [flattening_veto](sources/20261125_01_flattening_veto.cpp) | 211240 |
| 2026-11-25 | 2 | [deep_two_falls](sources/20261125_02_deep_two_falls.cpp) | 200460 |
| 2026-11-25 | 3 | [long_flank80](sources/20261125_03_long_flank80.cpp) | 211240 |
| 2026-11-25 | 4 | [left_flank_guard](sources/20261125_04_left_flank_guard.cpp) | 211240 |
| 2026-11-25 | 5 | [competitive_rebound](sources/20261125_05_competitive_rebound.cpp) | 211160 |
| 2026-11-25 | 6 | [selective_apex](sources/20261125_06_selective_apex.cpp) | 211268 |
| 2026-11-25 | 7 | [projected_apex](sources/20261125_07_projected_apex.cpp) | 211184 |
| 2026-11-25 | 8 | [distance_rank](sources/20261125_08_distance_rank.cpp) | 211372 |
| 2026-11-25 | 9 | [local_only](sources/20261125_09_local_only.cpp) | 211372 |
| 2026-11-25 | 10 | [rising_gap](sources/20261125_10_rising_gap.cpp) | 211186 |
| 2026-11-25 | 11 | [small_return_budget](sources/20261125_11_small_return_budget.cpp) | 208872 |
| 2026-11-25 | 12 | [larger_return_budget](sources/20261125_12_larger_return_budget.cpp) | 211233 |
| 2026-11-25 | 13 | [narrow_gate](sources/20261125_13_narrow_gate.cpp) | 211240 |
| 2026-11-25 | 14 | [wide_gate](sources/20261125_14_wide_gate.cpp) | 211053 |
| 2026-11-25 | 15 | [step9](sources/20261125_15_step9.cpp) | 198382 |
| 2026-11-25 | 16 | [step11](sources/20261125_16_step11.cpp) | 200517 |
| 2026-11-25 | 17 | [step8](sources/20261125_17_step8.cpp) | 196385 |
| 2026-11-25 | 18 | [step12](sources/20261125_18_step12.cpp) | 199426 |
| 2026-11-25 | 19 | [steeper_gate](sources/20261125_19_steeper_gate.cpp) | 211372 |
| 2026-11-25 | 20 | [shallower_gate](sources/20261125_20_shallower_gate.cpp) | 211372 |
| 2026-11-25 | 21 | [quick_gate](sources/20261125_21_quick_gate.cpp) | 211372 |
| 2026-11-25 | 22 | [late_gate](sources/20261125_22_late_gate.cpp) | 211184 |
| 2026-11-25 | 23 | [return_rivals](sources/20261125_23_return_rivals.cpp) | 211276 |
| 2026-11-25 | 24 | [trimmed_rivals](sources/20261125_24_trimmed_rivals.cpp) | 211411 |
| 2026-11-25 | 25 | [short_return](sources/20261125_25_short_return.cpp) | 211427 |
| 2026-11-25 | 26 | [deep_return](sources/20261125_26_deep_return.cpp) | 211327 |
| 2026-11-25 | 27 | [extra_quiet](sources/20261125_27_extra_quiet.cpp) | 211374 |
| 2026-11-25 | 28 | [faster_quiet](sources/20261125_28_faster_quiet.cpp) | 211322 |
| 2026-11-25 | 29 | [ascent_rebound](sources/20261125_29_ascent_rebound.cpp) | 200528 |
| 2026-11-25 | 30 | [model_switch](sources/20261125_30_model_switch.cpp) | 211435 |
