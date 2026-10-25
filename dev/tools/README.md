# 离线工具与研究脚本

[返回首页](../../README.md)

## 推荐入口

| 命令 | 行为 |
| --- | --- |
| python dev/run.py smoke | 编译当前main并运行真实管道烟测，报告到build/smoke.json |
| python dev/run.py check | 文档/归档、工具测试、判题器和求解器核心回归 |
| python dev/run.py diagnostics | 完整策略诊断，保留已知失败并原样返回退出码 |
| python dev/run.py docs | 只检查本地Markdown链接和归档哈希 |

## 底层工具

| 文件 | 用途 | 适合阶段 |
| --- | --- | --- |
| [local_judge.py](local_judge.py) | 管道交互、计分、烟测/扩展合成曲线 | 入门与回归 |
| [compare_solvers.py](compare_solvers.py) | 配对对比、逐族统计、完整JSON重放 | 算法实验 |
| [check_docs.py](check_docs.py) | 本地链接和不可变归档检查 | 文档维护 |
| [policy_search.py](policy_search.py) | 从固定159487归档生成变体、登记正式结果 | 历史实验工具，需理解父版本 |
| [online_search_loop.py](online_search_loop.py) | 历史连续提交控制器 | 会消耗次数，非默认开发入口 |
| [strategy_lab.cpp](strategy_lab.cpp) | 早期候选的内存协议适配 | 专项消融 |
| [evaluate_frontier.py](evaluate_frontier.py) | 对应lab配置的训练/留出实验 | 依赖预编译的历史实验配置 |

dev、local_judge、compare_solvers和check_docs均不访问平台。policy_search生成候选本身不上传，但record会更新正式记录和恢复最高源码。online_search_loop是可执行的线上历史控制器，保留本机路径和旧停止逻辑，不应当作通用快速启动脚本。

## 修改前看这里

不要更改评分归档来试参数；创建新的候选。先用local_judge确认交互，再用compare_solvers做配对实验。命令选项可通过--help查看。[实验步骤](../../docs/guides/reproduction.md)
