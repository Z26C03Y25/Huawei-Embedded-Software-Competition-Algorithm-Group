# 复现实验：从分数回到源码与轨迹

[文档导航](../README.md) · [版本目录](../../data/versions/README.md)

## 1. 确定比较对象

当前入口为main.cpp；正式最高分归档为versions/main_online_199291.cpp。运行 `python dev/run.py docs` 会校验[评分源码清单](../../data/versions/manifest.json)。不要在已评分归档上直接改代码，复制到新候选文件再实验。

正式总分来自本地保存的已确认评测记录。克隆仓库可以核对源码字节与实验表，不能重新生成官方隐藏数据或在没有账号时重新证明正式成绩。

## 2. 配对比较

在build目录已存在的前提下，PowerShell示例：

```powershell
g++ -O3 -Wall -std=c++17 data/versions/main_strategy_159487.cpp -o dev/build/baseline.exe
g++ -O3 -Wall -std=c++17 main.cpp -o dev/build/candidate.exe
python dev/tools/compare_solvers.py --programs baseline=dev/build/baseline.exe candidate=dev/build/candidate.exe --seed 2026 --count 28 --json-output dev/build/comparison.json
```

Linux编译时使用无.exe后缀路径即可。相同种子、数量和生成器版本保持相同曲线。对比报告保留完整数组、轨迹、源码/程序信息、逐族统计、修复零分与新增零分。

## 3. 重放同一批曲线

```powershell
python dev/tools/compare_solvers.py --programs candidate=dev/build/candidate.exe --replay-json dev/build/comparison.json --json-output dev/build/replay.json
```

重放使用报告中的数组，不依赖后来是否更改了随机生成逻辑。孤立尖峰和无结构数组单独统计，避免将信息受限曲线混成主要结构表现。

## 4. 再做消融

每份实验记录至少写父版本、源码哈希、改动参数、验证样本、分数变化与新失败。多个参数一起改变只能报告组合收益，不能把全部收益归给其中一项。

例如正式198409→199291同时开启模型收尾并将半径16缩为12，不能直接宣称模型收尾独立增加882分。[后续消融设计](../下一轮优化分析.md)

## 5. 学习历史实验时的注意点

[results.json](../../data/versions/online_search/results.json)和部分旧manifest保留原工作区绝对路径、作品ID和历史队列，用于追溯当时的实验，不是跨机器可直接执行的配置。评分源码副本在versions中，学习比较使用其仓库相对路径。

旧内存判题适配器strategy_lab.cpp和evaluate_frontier.py对应早期候选与预编译配置；先读[工具说明](../../dev/tools/README.md)。新手先用真实管道判题器建立基线。

离线证据有助于解释机制和排除坏方案，但不预测正式102例分数。上线前还需使用自己的账号、明确团队剩余额度，并遵守[提交工具](../../automation/online_judge/README.md)的身份绑定与防重规则。
