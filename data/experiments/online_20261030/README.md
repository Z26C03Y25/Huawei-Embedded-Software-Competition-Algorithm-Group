# 2026-10-30 线上逐轮优化

本地快照：2026-10-30T03:23:06+08:00。只读现有记录，本报告不联网、不提交。

初始最高分 **210599**，当前采用最高分 **210599**，变化 **+0**。main.cpp 与保存的最高分 SHA 一致。

当日实际投递尝试 **23/30**，唯一已投递源码 **23**，重复源码尝试 0 次；按本地实际尝试计剩余 7 次。失败及待判分均计入。

已按用户最新要求停止后续上传，转入[多维特征分析与算法设计](../../../docs/research/README.md)。剩余次数没有继续使用。

已有榜单参考：榜首 **231029**，当前采用版本差 **20430**。采集时间 2026-10-30T02:17:06+08:00，榜单自身刷新时间 2026-10-30T01:05:00+08:00，范围 first_page。该缓存不是实时榜单，本次未请求榜单。

## 逐轮正式结果

| 轮 | 名称 | 父分数 | 正式分数 | 相对父版本 | 采用 | 本地 job 状态 |
| ---: | --- | ---: | ---: | ---: | --- | --- |
| 1 | short_nonflat4 | 210599 | 210571 | -28 | 否 | completed |
| 2 | short_flat4 | 210599 | 210599 | +0 | 否 | completed |
| 3 | initial_phase23 | 210599 | 202826 | -7773 | 否 | completed |
| 4 | short_rising_half | 210599 | 210567 | -32 | 否 | completed |
| 5 | acceleration_half | 210599 | 210250 | -349 | 否 | completed |
| 6 | sparse_phase_walk | 210599 | 195439 | -15160 | 否 | completed |
| 7 | model_residual_validate | 210599 | 207684 | -2915 | 否 | completed |
| 8 | model_close_peak_audit | 210599 | 210563 | -36 | 否 | completed |
| 9 | valley_separated_clusters | 210599 | 210599 | +0 | 否 | completed |
| 10 | competitive_cell_priority | 210599 | 210599 | +0 | 否 | completed |
| 11 | seed25 | 210599 | 205271 | -5328 | 否 | completed |
| 12 | seed28 | 210599 | 188629 | -21970 | 否 | completed |
| 13 | noisy_trend_frontier | 210599 | 194582 | -16017 | 否 | completed |
| 14 | rival_reach_223 | 210599 | 210599 | +0 | 否 | completed |
| 15 | short_half_skeleton_noise | 210599 | 210561 | -38 | 否 | completed |
| 16 | accel_half_skeleton_noise | 210599 | 210224 | -375 | 否 | completed |
| 17 | curvature_scaled_noise | 210599 | 210499 | -100 | 否 | completed |
| 18 | decline_frontier_latch | 210599 | 206019 | -4580 | 否 | completed |
| 19 | long_plus1 | 210599 | 210309 | -290 | 否 | completed |
| 20 | mid_plus1 | 210599 | 208251 | -2348 | 否 | completed |
| 21 | long_plus4 | 210599 | 207748 | -2851 | 否 | completed |
| 22 | mid_plus4 | 210599 | 191491 | -19108 | 否 | completed |
| 23 | economic_suffix_allN | 210599 | 210599 | +0 | 否 | completed |

正式分数仅取源码 SHA 匹配且状态 completed 的已有 job。待判分、未知与失败不会被写成零分。平分保留原版。

## 源码与作品标识

| 轮 | 公开赛事源码 | SHA256 | 作品 ID |
| ---: | --- | --- | --- |
| 1 | [data/versions/online_search/scored_210571_28197c5b86c9.cpp](../../versions/online_search/scored_210571_28197c5b86c9.cpp) | 28197c5b86c93d32d026fd5532298a5042c1b5a600ffbcee176a1d1146da38be | 2c4e701f251849bb919321eb13e25aea |
| 2 | [data/versions/online_search/scored_210599_db8bab3d05d8.cpp](../../versions/online_search/scored_210599_db8bab3d05d8.cpp) | db8bab3d05d8570935ddfc1fd78f9cbd64ab276cf05fb2f26e8831a541960027 | b5e4d8ccb77242398f8cc3b5819aa23a |
| 3 | [data/versions/online_search/scored_202826_e2eb48a66176.cpp](../../versions/online_search/scored_202826_e2eb48a66176.cpp) | e2eb48a66176f72a86fec11d8b243750c819bc3e6ae6b73e45ba25dfeba84422 | f807af7d5d7647be81cb4e372cd80bb2 |
| 4 | [data/versions/online_search/scored_210567_28f89a58bb08.cpp](../../versions/online_search/scored_210567_28f89a58bb08.cpp) | 28f89a58bb083d3b37d4cbd349e40d9ddf884bc6e4ec46372d2c800fd558e515 | fbf671439e274178864529bc4fd3a160 |
| 5 | [data/versions/online_search/scored_210250_63ed3b1e7017.cpp](../../versions/online_search/scored_210250_63ed3b1e7017.cpp) | 63ed3b1e7017e8107c29cbbe34846c6af3070e0bce14c7e8c0bc1c253fcea31d | 26f35742bd144126a62c1e03053d0483 |
| 6 | [data/versions/online_search/scored_195439_bea7f6a70f47.cpp](../../versions/online_search/scored_195439_bea7f6a70f47.cpp) | bea7f6a70f477e358e355985d93ba73959d10f7ad5efdaf59004f02d61b224a7 | e81e82c820824023bd7b20afcd5555cc |
| 7 | [data/versions/online_search/scored_207684_bd8d54d74441.cpp](../../versions/online_search/scored_207684_bd8d54d74441.cpp) | bd8d54d7444121591222067f69cc7a7071b92fd295f21da1effdc66598a8e89a | 98c079a19cb24a3d91971acd90b6c103 |
| 8 | [data/versions/online_search/scored_210563_03c97f0391a6.cpp](../../versions/online_search/scored_210563_03c97f0391a6.cpp) | 03c97f0391a6533c93f6697dd0e067b9b7fe3bda3b60fd3bc2b09c7f65d0c0fd | a7ef52b3421b4f028cfb9b3578fbb340 |
| 9 | [data/versions/online_search/scored_210599_0157477d9e66.cpp](../../versions/online_search/scored_210599_0157477d9e66.cpp) | 0157477d9e667cd296ac0ffb46ffb3e339a9a28eee4f11c9ee605391f3981f20 | 06c3e9ec4cc441849c24e3b6ba1d0a00 |
| 10 | [data/versions/online_search/scored_210599_b919a7d230f5.cpp](../../versions/online_search/scored_210599_b919a7d230f5.cpp) | b919a7d230f5133558a3dda97dd927bc8d30288f5b472d137211dcb72fc7aea7 | f5ae60a40f9543f292ada6103aa43e63 |
| 11 | [data/versions/online_search/scored_205271_d372983215e5.cpp](../../versions/online_search/scored_205271_d372983215e5.cpp) | d372983215e591b92dd1fc063890585ba13107f520218e93a86d284cde00882e | 34e0678777d44671b4f12c2b914a52b5 |
| 12 | [data/versions/online_search/scored_188629_acebb0ee7fa2.cpp](../../versions/online_search/scored_188629_acebb0ee7fa2.cpp) | acebb0ee7fa2d7c56b0b648d91266ff1cd136ab1c618828f9a17a9e9ca7992f2 | 926577434d4a405889e710415c8f1fe3 |
| 13 | [data/versions/online_search/scored_194582_e8b16c791714.cpp](../../versions/online_search/scored_194582_e8b16c791714.cpp) | e8b16c7917146a5d1d0025ec318ba145fc4620019dde4801ee979aced1343979 | 3d53ad760ef8476a85b1a371d43d4ef2 |
| 14 | [data/versions/online_search/scored_210599_f38de21a6a4f.cpp](../../versions/online_search/scored_210599_f38de21a6a4f.cpp) | f38de21a6a4f17c3b1d105ab4ee8b4ed17516707b4a4230e9218219809ca90ee | 8fc236d6aaed47c89430641cfa764011 |
| 15 | [data/versions/online_search/scored_210561_49f9f83300d3.cpp](../../versions/online_search/scored_210561_49f9f83300d3.cpp) | 49f9f83300d393b33d626f511df7839e70df69d68c1b6f73838156c853ccb66b | d41f2f3ea18e49d3b170509f8ededdfc |
| 16 | [data/versions/online_search/scored_210224_2eee96f82018.cpp](../../versions/online_search/scored_210224_2eee96f82018.cpp) | 2eee96f8201847f876508046c7f33dfc43109ddeeb66b5b3f2ddd22273a8186b | 2bfacf3910d347d7b4291c536f58e286 |
| 17 | [data/versions/online_search/scored_210499_d4e6b8735ca3.cpp](../../versions/online_search/scored_210499_d4e6b8735ca3.cpp) | d4e6b8735ca3e3232b69724ee29bc393d205a3265d94897bc07ba6b5edbada6c | 5cfed2795e8540b0a91f41d76e2283cf |
| 18 | [data/versions/online_search/scored_206019_8aa580c84b99.cpp](../../versions/online_search/scored_206019_8aa580c84b99.cpp) | 8aa580c84b997d1b65a75f27036162a6056980b324258cbe28616656d9c339e7 | 0938996da2df4ac4b3e6781c3f07d563 |
| 19 | [data/versions/online_search/scored_210309_2eb016fa1a4b.cpp](../../versions/online_search/scored_210309_2eb016fa1a4b.cpp) | 2eb016fa1a4b50f93635f25894dc5a75f5cc71a75b4bf5435b9135378b6341c5 | ae40050c79484f4bb27aec2ffa97b4f3 |
| 20 | [data/versions/online_search/scored_208251_394c059bd1a3.cpp](../../versions/online_search/scored_208251_394c059bd1a3.cpp) | 394c059bd1a3d18c16511bba171d9eb6f56bb2ab10bf9f4252e062c9fa422bde | 63423ca6e4954ef7a538775def4c0e60 |
| 21 | [data/versions/online_search/scored_207748_3e38e532d909.cpp](../../versions/online_search/scored_207748_3e38e532d909.cpp) | 3e38e532d90962699e2823e894b99f93a22fea425e94dea02633709f4d5d3fce | 0889e1567b5a4c8fb86821822f74ddcd |
| 22 | [data/versions/online_search/scored_191491_98772cfd7ca9.cpp](../../versions/online_search/scored_191491_98772cfd7ca9.cpp) | 98772cfd7ca98357f866233ff7b2920736e8526e32c61940fe9723b3007bff0c | 03ae91c354ca414790fa174b3d033e54 |
| 23 | [data/versions/online_search/scored_210599_aac687301b98.cpp](../../versions/online_search/scored_210599_aac687301b98.cpp) | aac687301b98c2e39e3586079734f458895ae075ef2c8dd513409c7e4b1bda06 | 7c5239facbb649a08785783fcaba0fb0 |

## 已有检查证据

控制器记录严格编译及烟测通过 21 轮、真实管道烟测 546 条，包含 68 条合成零分；源码静态审查通过 21 轮。合成零分与协议违规分别记录。

最初两轮通过 --resume 导入，缺少控制器 preflight 元数据；另有人工作业的 dev/build 烟测证据，未冒充为控制器自动检查。

- short_nonflat4：dev/build/online_short_nonflat4_smoke.json，26 条；该 JSON 不含源码 SHA 绑定。
- short_flat4：dev/build/online_short_flat4_smoke.json，26 条；该 JSON 不含源码 SHA 绑定。

本地报告只更新本目录 README.md 与 summary.json；不修改 main.cpp、状态、正式结果、版本索引或归档哈希。
