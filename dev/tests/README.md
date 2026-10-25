# 测试导航

[测试分层说明](../../docs/guides/testing.md) · [已知限制](../../docs/reference/known-limitations.md)

| 测试文件 | 检查内容 | 当前定位 |
| --- | --- | --- |
| [test_local_judge.py](test_local_judge.py) | 正式计分边界、错误输出、超时和真实子进程握手 | 核心工具正确性 |
| [test_compare_solvers.py](test_compare_solvers.py) | 生成器、曲线身份、配对统计和重放 | 实验可信度 |
| [test_solver_regressions.py](test_solver_regressions.py) | 评分归档哈希、协议预算、冠军停车和历史版本回归 | 核心求解器检查，需g++ |
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
