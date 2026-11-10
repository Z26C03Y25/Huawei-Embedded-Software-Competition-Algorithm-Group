# 2026-10-31 线上总分黑盒实验

本地只检查编译、交互、Q/O及停车，不用合成得分挑选候选。每次只上传冻结源码一次，超时恢复原作业。

可核验父版为210599。页面另有210666记录，但暂未找到绑定源码，不能把其他源码标成该分数。原工作区main.cpp在采用确认优胜版时另存备份，采用信息见adoption.json；实验优胜版亦单独归档。

已投递30次，失败1次；最高212686；同源码不同作品独立重测确认：True。

| 实验 | 正式总分 | 相对父版 | 接纳 |
|---|---:|---:|---|
| continue_all | 205085 | -5514 | False |
| continue_short | 210279 | -320 | False |
| neighbor_confirm_3_all | 182519 | -28080 | False |
| inline_triplets_raw_all | 212058 | 1459 | True |
| inline_triplets_clean_all | 212058 | 1459 | False |
| inline_triplets_raw_short | 210591 | -8 | False |
| inline_triplets_raw_midlong | 212066 | 1467 | True |
| inline_triplets_raw_mid | 212320 | 1721 | True |
| hard_frontier_guard | 171145 | -41175 | False |
| reserved_final_core | 208965 | -3355 | False |
| follow_new_peak | 212320 | 0 | False |
| spike_stress_scenarios | 208056 | -4264 | False |
| dense_basin_long | 209780 | -2540 | False |
| priority_only_planner | 212320 | 0 | False |
| continue_mid | 205685 | -4914 | False |
| forward_five | 209621 | -2699 | False |
| interval_sweep_retry_v2 | 206770 | -5550 | False |
| interval_sweep_retry_v2_mid | 211817 | -503 | False |
| interval_early_handoff | 159964 | -52356 | False |
| preserve_coarse_grid | 210298 | -2022 | False |
| sparse_forward_pair | None | None | False |
| triplets_upper_mid | 212668 | 348 | True |
| triplet_band_501_538 | 210233 | -2087 | False |
| triplet_band_576_613 | 212668 | 348 | False |
| triplet_band_539_613 | 212686 | 366 | True |
| near_vertex_triplets | 210724 | -1962 | False |
| inner_forward_pair | 210573 | -2113 | False |
| irreversible_cost_guard | 212686 | 0 | False |
| single_pass_refine | 212686 | 0 | False |
| main_online_212686 | 212686 | 0 | False |

## 分组拟合

同一改动按N≤500、501～650、>650互斥启用，拟合各组的总得分改变量。全N改变量应为三组之和；它不提供逐例峰形或零分归因。未直接测试的推断不得当作正式成绩。

- continue：已测{'all': -5514, 'short': -320, 'mid': -4914}；条件推断{'long': -280}。
  二分拟合：{'N<=500': -320, 'N>500': -5194}；仅启用正收益组的预测总分210599，不是新正式成绩。
- gap_audit_16：已测{}；条件推断{}。
- neighbor_confirm_3：已测{'all': -28080}；条件推断{}。
- neighbor_clean_3：已测{}；条件推断{}。
- inline_triplets_raw：已测{'all': 1459, 'short': -8, 'mid': 1721, 'midlong': 1467}；条件推断{'long': -254}。
  二分拟合：{'N<=500': -8, 'N>500': 1467}；仅启用正收益组的预测总分212066，不是新正式成绩。
- inline_triplets_clean：已测{'all': 1459}；条件推断{}。
- interval_sweep_retry_v2：已测{'all': -5550, 'mid': -503}；条件推断{}。

进一步互斥N分段的条件拟合：{'501..575': -348, '576..650': 2069, '501..538': -366, '539..575': 18, '576..613': 2069, '614..650': 0}。由差值推断的单段不是单独正式成绩；组合需要直接验证。

相邻点用于核查连续峰与孤立高点。原始数组的最高值始终保留；任何中位数/清洗只允许影响趋势建议，不能替代正式目标。

raw/clean对照保持相同的动作生成规则，但清洗会影响后续分支和查询位置。因此比较的是完整策略效果，不能解释成在完全相同数据上的独立降噪收益。

这是一组黑盒策略对照，未声称能反演隐藏数组或由总分证明减少了多少零分。
