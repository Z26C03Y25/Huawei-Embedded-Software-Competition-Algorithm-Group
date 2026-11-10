# 2026-10-29：按 N 止损实验

正式基线为 [210599 源码](../../versions/main_online_210599.cpp)，SHA256 `55f74d74926c235485d16ddb31e5e073a4fbde7ad0b71159410fa80429ad23ed`。本目录均为候选，不以文件名赋予正式分数。

本轮本地选定 [safe_short_suffix.cpp](safe_short_suffix.cpp)，SHA256 `52a8c3f8ee4a70abe52f2fc873a6fe54fd30e9984fa382d1c54baabeff4a24c5`。它保留现有三段粗搜确认距离，仅在 N≤500 的普通精修批次中尝试截断后缀。需要当前原始最佳点±3已读、显著低噪声、非平台、没有已观察到的远端竞争峰；有限插值场景比较包括真实停车的查询、移动和转向。评估后恢复随机数与状态机，避免未触发分支产生无关轨迹变化。VMAX 分支禁用新增止损。

这些条件不是全局峰值证书。局部模型仍可能漏掉未读尖峰。

## 本地证据

V4 混合生成器，种子标签 `20261029402`，28 族含4个新族；每族每阶段25条独立母曲线，三阶段共2100条母曲线，另252条兄弟变换不计独立样本。源码在新混合开发集之前冻结；预设短数组备选在选择集之后、读取偏移盲测候选结果之前选定。

| 分组 | 母曲线数 | 含零平均分变化 | 新增零分 |
| --- | ---: | ---: | ---: |
| 开发集 | 700 | +0.246 | 0 |
| 选择集 | 700 | +0.327 | 0 |
| 偏移盲测 | 700 | +1.067 | 0 |
| N≤500（三阶段） | 492 | +2.333 | 0 |
| 全体 | 2100 | +0.547 | 0 |

整体零分863条，与基线相同；没有修复既有零分。36条改变轨迹且双方正分的曲线，平均减少8.69次读取、23.06格移动。全体与基线的真实冗余和停车误差相同。留出族均衡增益bootstrap 95%区间约[0.425,0.991]，只描述合成分布。最低四分之一均分双方均为0，本指标在该难例分布中缺乏区分能力。

26条烟测无协议错误，保留3个既有零分；12条VMAX/平局回归与基线查询轨迹一致。结构化结果见 [results.json](results.json)。原始曲线、逐例路径、冻结源码与编译器哈希在本机 `dev/build/stoploss_mandatory_fresh_20261029/`。

## 被否定的方案

- `long_model_cap.cpp`：经典开发集均分-1.64，新增1个零分；不继续缩相邻参数。
- `all_suffix.cpp` 与 `safe_suffix_window.cpp`：短邻域确认不能阻止近邻双峰误停。经典偏移留出集新增1个零分；组合总体虽+2.53，留出零率与低尾检查失败。
- `mandatory_suffix.cpp`：先完成原pool中priority≥100候选才止损。修复了已知近邻双峰回归，但全新混合选择与盲测各新增1个零分，整体-0.18，因此淘汰。
- `model_window.cpp`：开发集约+0.42；单独模型窗口不作为本轮最终候选。
- `combined_suffix_window.cpp`：VMAX保护前的中间稿，评估中止，不能作为已验证版本。

经典失败反例 `blind_shift/close_competitors/019`：N=999，真实峰267，左侧次峰252。基线2305分；过早止损省9次查询与25格移动，停车误差15，整例归零。这是有限插值场景没有表达未读更高峰的问题。

## 复现

从仓库根目录运行；不修改环境变量、不访问线上：

```powershell
& ./python/runtime/python.exe data/experiments/stoploss_20261029/build_candidates.py
foreach ($phase in @('development','selection','blind_shift')) {
    & ./python/runtime/python.exe dev/tools/fresh_stoploss_study.py --out dev/build/stoploss_reproduction --per-family 25 --source short=data/experiments/stoploss_20261029/safe_short_suffix.cpp --source mandatory=data/experiments/stoploss_20261029/mandatory_suffix.cpp --split $phase
}
& ./python/runtime/python.exe dev/tools/summarize_stoploss.py --out dev/build/stoploss_reproduction
```

本地收益很小，不能换算为官方总分或宣称追上榜首。

## 正式线上结果

用户授权后仅提交一次，提交前页面显示29/30次已用。北京时间2026-10-29 11:23:25上传，作品ID `9ea8c640f10c43e0a029663c681dcdcf`，任务 `20261029T032329929166Z_c32134f9f6d4`。同一作品连续两次成功终分确认 **210599**，与最高分持平，提升 **0**。没有重复上传，今日30次已用完。未安排零点自动提交。

确切上传字节已归档至 [正式源码](../../versions/online_search/scored_210599_52a8c3f8ee4a.cpp)。`main.cpp` 保留原210599源码；本地小幅收益未转化为本次官方总分收益，不能由总分持平反推两版官方逐例轨迹完全相同。

判分后的工具遵守共享两小时缓存规则，读取榜单第一页：11:25:34采集，榜单刷新时间10:30，榜首230023，当前210599，差19424。榜首比此前缓存227592有所提高，该快照仍不是本次判分证据。
