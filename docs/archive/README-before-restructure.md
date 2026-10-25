# 华为嵌入式软件大赛 · 算法组

智能摄像机自动聚焦，单文件 C++17 交互式求解器。当前 main.cpp 为已正式确认的最高分 **199291** 版本，与 versions/main_online_199291.cpp 字节完全一致。2026-10-25 今日团队 30/30 次提交额度已用完；距离 200000 目标仍差 709。

最新结果、参数和未通过的合成性能案例见 docs/持续线上优化总结.md；29 次新提交的完整轨迹见 docs/持续线上优化记录.md。

## 当前策略

- 原始值与趋势双通道，分辨平坦、上升、下降、宽峰、多峰和低置信度结构。
- 原始峰显著性门槛为 24 倍波动估计，粗网格主要步长 8、粗搜额度 128。
- 后半程峰采用 16 格的侦察门槛，前半程保留 96～144 格；完全平坦观测期限为较小中央下标加 144。
- 减少弱候选簇补查；在低波动、预测一致、单峰明确时验证局部 13 点邻域，缩短精修。
- 12 类、96 个设计项融入共享流水线；按条件触发，不依次执行全部算子。
- 所有实际查询统一计数，普通查询保留停车额度，总查询不超过 199。
- 实际移动前检查方向和返回路径，振荡不超过 6；精修按单调批次执行。
- 以竞争区左端约束模型前探，避免宽峰只跟随右侧粗采样最高点。
- 候选超过额度时，用内部模拟退火优化采样子集；内部尝试不产生真实查询。
- 最后实际查询最佳已观测点，再输出 DONE；严格执行原始最大值及中央平局规则。

默认冗余边界依赖峰形模型，不能保证任意隐藏主峰的真实冗余≤199。可选 --strict-redundancy 使用可证明的目标下界，严格控制冗余，但会放弃部分远端搜索。题面没有足够形状约束，有限查询无法保证任意数组同时全局命中且满足全部阈值。

## 文件

- main.cpp：正式提交入口，当前分层策略。
- docs/搜索算子与分支策略设计.md：完整设计、96 个算子的条件与风险。
- docs/持续线上优化总结.md：当前 199291 分版本、预算、参数、正式结果与剩余问题。
- docs/持续线上优化记录.md：本轮 29 次新线上提交及源码哈希。
- docs/策略实现说明.md：159487/153592 版本的历史实现映射与预算说明。
- docs/159487复盘与第二轮实验.md：当前版本实验、被排除的方案和独立验证。
- docs/策略验证结果.md：159487 归档版本的历史合成验证。
- docs/赛题分析.md：旧版本分析与历史实验，非当前实现说明。
- tools/local_judge.py：本地交互判题器，记录全部查询轨迹和计分指标。
- tools/compare_solvers.py：跨分布对比、源码哈希和完整曲线回放。
- tools/strategy_lab.cpp、tools/evaluate_frontier.py：保持查询应答隔离的快速消融测试。
- tests/：判题器、版本归档、求解器与新策略回归。
- versions/main_before_strategy.cpp：本轮改造前的实际入口文件，原样保留。
- versions/main_strategy_159487.cpp：本次反馈 159487 的确切源码，原样保留。
- versions/main_online_199291.cpp：当前最高正式分源码，原样保留。
- versions/online_search/：可重放策略参数、每次正式分数、不可变源码归档与停止状态。
- versions/main_v1_154353.cpp、versions/main_v2_145904.cpp：已知正式成绩归档，未修改。
- online_judge/：线上工具；本轮没有上传或提交。
- online_judge/ranking.py：只读榜单第一页，重点参考榜首，共享两小时缓存，减少重复请求。
- 赛题/：原始 PDF。

## 编译与验证

所有命令在仓库根目录执行。

```powershell
New-Item -ItemType Directory -Force build
g++ -O3 -Wall -Wextra -Wpedantic -std=c++17 main.cpp -o build/main.exe
python -m unittest discover -s tests -v
python tools/local_judge.py --program build/main.exe --suite smoke
python tools/local_judge.py --program build/main.exe --suite extended --seed 2026 --json-output build/strategy_extended.json
```

程序先读 N，然后每输出一个查询下标就等待清晰度应答。不要把完整数组直接送入求解器；请使用交互判题器。正式只提交 main.cpp，无第三方依赖。

## 可选模式

```powershell
python tools/local_judge.py --program build/main.exe --program-arg=--trace --suite smoke
python tools/local_judge.py --program build/main.exe --program-arg=--strict-redundancy --suite smoke
python tools/local_judge.py --program build/main.exe --program-arg=--late-flat --suite smoke
```

--trace 只向 stderr 输出状态、算子和账本。--late-flat 扩大长期平坦后的探索范围，可能救回迟起峰，也可能使常数数组冗余超限。它和 --strict-redundancy 同时使用时，证明边界始终优先。

## 版本比较

```powershell
g++ -O3 -Wall -std=c++17 versions/main_before_strategy.cpp -o build/before_strategy.exe
g++ -O3 -Wall -std=c++17 versions/main_v1_154353.cpp -o build/reference_v1.exe
python tools/compare_solvers.py --programs before=build/before_strategy.exe v1=build/reference_v1.exe strategy=build/main.exe --seed 8209 --seed 4843 --count 144 --json-output build/comparison.json
```

本地合成结果不预测正式 102 个真实用例的成绩。协议错误与合法零分分别统计；保存的 JSON 可查看所有零分原因、真实目标、停车误差、移动、冗余和反转。

build/、tmp/ 下的二进制、报告和阅读缓存不进入版本控制。

## 榜单参考

```powershell
online_judge\.venv\Scripts\python.exe online_judge\judge.py ranking
```

该命令不上传作品，只读第一页，不翻页。快照为 `online_judge/runs/rankings/latest.json`。命令和提交后的榜首参考共享两小时缓存，失败后也冷却两小时；连续提交复用已有数据。用法及榜单独立刷新周期见 `online_judge/README.md`。
