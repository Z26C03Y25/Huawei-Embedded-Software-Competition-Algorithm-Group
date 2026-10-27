# 2026-10-26：以综合得分为主，验证实际鲁棒性

[文档导航](../README.md) · [上一阶段历史](2026-10-26-zero-first.md) · [最终汇总](../../data/experiments/robust_confirm_20261026/research_summary.json)

## 用户澄清与评价目标

用户明确“可以本地算分，只要求鲁棒性较好，主要是综合得分尽量高”。因此旧的逐例零分否决和零分数优先排序不再作为当前研究目标。使用原计分公式，零分按0计入综合平均分；个体退化完整报告，允许用整体得分和风险改善判断取舍。

[综合评价器](../../dev/tools/robust_score.py)对新鲜母曲线按场景族和数据划分等权计算均分，包含22族中的无结构随机与单点尖峰。完全相同数组去重，镜像/偏移/缩放只作稳健性诊断，不重复计入独立证据。旧反例和验收集单独报告，不用重放集抬高主指标。

鲁棒性检查在实验前冻结：选择与分布偏移留出的综合分提高、总体零分率不增加、最低四分之一平均分CVaR25不下降，合并留出的配对bootstrap区间下界大于0；协议、Q≤199、O≤6及最佳已观测点停车检查保持硬约束。CVaR25就是把最差25%样例的分数取平均，零分照计。未达到这些检查的方案仍可作为本地研究线索，不能直接进入线上队列。

这些是合成测试的选择规则，不是对官方分布的概率保证。历史zero_first诊断仍保留，当前排序以score_ranking.json为准。研究配置中的旧零分/场景均值门槛字段仅供历史分支，当前执行robust_total_score分支。

## 五版本配对消融

冻结索引90–125，每族每划分36条，共2376条新母曲线；完全相同数组去重后主统计为2374条。另有198条变体、29条公共烟测/冻结反例、34条针对性验收，总2637条，5个版本共13185次真实管道交互。

两个因素：平坦覆盖终点175或160；是否启用下降阶梯模型限幅。四个组合继承同一宽域波谷验证，其余参数一致，并与正式203239源码比较。

| 版本 | 本地综合均分（含0） | 相对正式版 | 新鲜母曲线零分数 | CVaR25 |
| --- | ---: | ---: | ---: | ---: |
| 正式203239 | 1866.19 | 0 | 480 | 308.05 |
| 上一轮本地175＋宽域波谷 | 1901.24 | +35.06 | 436 | 444.31 |
| 缩短为160 | 1884.77 | +18.58 | 456 | 382.41 |
| **175＋下降阶梯限幅** | **1920.08** | **+53.89** | **417** | **505.51** |
| 160＋下降阶梯限幅 | 1903.60 | +37.41 | 437 | 443.59 |

缩短平坦覆盖节省常数曲线成本，却漏掉更多稍迟出现的信号，整体下降16.47分/例。下降阶梯算子在两种覆盖半径上均贡献18.83分/例；本批没有观测到交互作用。见[因子差分](../../data/experiments/robust_total_20261026/factorial_effects.json)与[相对上一轮本地版本](../../data/experiments/robust_total_20261026/incremental_vs_local_incumbent.json)。

下降算子要求至少7段已观测斜率全部非正且至少3段严格下降，给出基于已观测最高平台右端的探索上界；只缩小原有上界，不扩大它。观测到上升后条件解除。它是可检验的阶梯/下降前缀模型，不是全局单调证书。

新算子在筛选集新增2条个体零分，同时修复65条，净减少63条；综合分与尾部均改善。因此按用户最新目标保留该方案，而不因2条损失自动丢弃。完整新失败曲线仍保留在[counterexamples/desc175.json](../../data/experiments/robust_total_20261026/counterexamples/desc175.json)，下一轮研究减少这类误限幅。

## 固定源码后的独立确认

多版本比较完成后，将唯一优胜源码与摘要冻结到[selection_decision.json](../../data/experiments/robust_total_20261026/selection_decision.json)，然后才运行全新索引126–143。没有根据确认结果更换候选或继续调参。

确认集1188条新母曲线，另加变体及公共验收，总1449条；仅比较正式基线与固定候选，共2898次交互。

| 指标 | 正式203239 | 固定候选 |
| --- | ---: | ---: |
| 综合均分（含0） | 1872.33 | **1915.89** |
| 零分数 | 241 | **216** |
| CVaR25 | 305.67 | **463.93** |

确认均分提高43.56分/例，约2.33%；未新增个体零分，修复25条。合并选择/偏移留出的均分差bootstrap区间约[29.77,76.22]，检查通过。[确认评分卡](../../data/experiments/robust_confirm_20261026/scorecards/champion.json)

本轮总计16083次真实交互，未上传、未读取榜单。所有版本的协议、查询、振荡及已观测冠军停车检查通过；零分仍存在，已经计入上表。正式总分仍是203239，不能把本地均分或其提升加到正式成绩上。

## 候选与下一步

[独立确认的候选源码](../../data/experiments/robust_total_20261026/flat175_desc.cpp)摘要为37d00d6071bfbccc0d94e4719983407c54a98a0e6bb62ded498b86a8d770a235。只有这一份进入[合格候选清单](../../data/experiments/qualified_candidates.json)，真实运行上传前证据审核已通过。另三个参数/算子对照不构成上传队列。

main.cpp仍保护最高正式版本。下一次有官方次数且调度启用时，优先只验证这一个候选，收到正式总分后再决定下一步。本次发现已有定时任务处于PAUSED，同步目标说明时保留暂停状态，没有擅自恢复。每日自动研究上限仍为3次团队提交，可以为0，不以用尽额度为目标。

0–143号样例块均已观察，后续新算子需要144号以后的数据或新冻结种子。优先减少下降前缀误判带来的2条损失，保留阶梯收益；继续按综合分评价，而不是只报修复数。

## 复现

Python3.10+、GCC C++17。完整数组与轨迹在dev/build/research的本机忽略目录，公开源码、生成器、种子、哈希和报告足以重建。

```bash
python dev/tools/screen_operators.py --out data/experiments/robust_total_20261026 --case-offset 90 --per-family 36 --extra-cases data/experiments/zero_first_20261026/acceptance_cases.json --program formal203239=main.cpp --program local175=data/experiments/zero_first_20261026/flat175_widevalley.cpp --program flat160=data/experiments/robust_total_20261026/flat160_score.cpp --program desc175=data/experiments/robust_total_20261026/flat175_desc.cpp --program desc160=data/experiments/robust_total_20261026/flat160_desc.cpp
python dev/tools/screen_operators.py --out data/experiments/robust_confirm_20261026 --case-offset 126 --per-family 18 --extra-cases data/experiments/zero_first_20261026/acceptance_cases.json --program formal203239=main.cpp --program champion=data/experiments/robust_total_20261026/flat175_desc.cpp
python dev/run.py check
```

输入、策略或源码变化时应使用新输出目录；已有报告不会在身份不一致时被当作断点复用。历史研究记录中的旧命令绑定旧目标和输入，新策略下重算应另建目录并明确评价版本。
