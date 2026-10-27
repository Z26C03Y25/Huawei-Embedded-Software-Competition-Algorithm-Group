# 测试导航

[测试分层说明](../../docs/guides/testing.md) · [已知限制](../../docs/reference/known-limitations.md)

| 测试文件 | 检查内容 | 当前定位 |
| --- | --- | --- |
| [test_local_judge.py](test_local_judge.py) | 正式计分边界、错误输出、超时和真实子进程握手 | 核心工具正确性 |
| [test_compare_solvers.py](test_compare_solvers.py) | 生成器、曲线身份、配对统计和重放 | 实验可信度 |
| [test_research_policy.py](test_research_policy.py) | 多场景生成、母曲线身份、自动上限与证据、午夜刷新和恢复 | 不联网 |
| [test_solver_regressions.py](test_solver_regressions.py) | 评分归档哈希、协议预算、冠军停车和历史版本回归 | 核心求解器检查，需g++ |
| [test_zero_first.py](test_zero_first.py) | 新零分否决、修复去重、正分低尾与严格冲突证据 | 研究目标与证书检查 |
| [test_robust_score.py](test_robust_score.py) | 包含零分的综合分、留出尾部、配对身份、变体去重 | 当前研究目标 |
| [test_mixed_scenarios.py](test_mixed_scenarios.py) | 混合生成、压力分层、划分模板、种子及母曲线身份 | 防单一分布过拟合 |
| [test_search_losses.py](test_search_losses.py) | 原计分损失分解、负运动差额及得分耗尽 | 优化优先级的记账依据 |
| [test_strategy_solver.py](test_strategy_solver.py) | 各类峰、噪声、预算与性能断言 | 完整诊断，有已知失败 |
| [automation/online_judge/tests/](../../automation/online_judge/tests/README.md) | 浏览器适配的离线模拟、任务身份、缓存和防重 | 不访问真实网站 |

完整核心检查：`python dev/run.py check`。

只有Python时可分别执行：

```bash
python -m unittest discover -s automation/online_judge/tests
python -m unittest discover -s dev/tests -p test_local_judge.py
python -m unittest discover -s dev/tests -p test_compare_solvers.py
```

完整策略诊断：`python dev/run.py diagnostics`。普通的 `python -m unittest discover -s dev/tests -v` 会包含这组诊断，当前预期仍可能失败。不要把这个非零退出与上传工具的协议失败混为一谈，也不要忽略新出现的失败。

[实际C++协议传输与异常收尾测试](test_protocol_transport.py)：直接编译协议候选及隔离故障注入桩，验证上下界、消息预算和DONE生命周期。

[少量点拟合求解器测试](test_sparse_curve_solver.py)：真实管道验证拟合触发、原始已观测尖峰保留与协议极值。

[粗扫覆盖归因测试](test_coarse_gaps.py)：区分不可逆越峰、尾部未覆盖和可局部补查漏点；事后真值仅用于诊断。

[粗扫与竞争区实际求解器测试](test_coarse_compete_solver.py)：三个冻结源码的协议、停车、单次前向探针和最多两次中点补查。
