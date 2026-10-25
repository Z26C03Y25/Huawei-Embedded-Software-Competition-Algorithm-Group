# 工程地图与文件职责

[文档导航](../README.md)

## 四个功能目录

automation负责线上评分和AI调度，dev负责开发/构建/测试，data保存赛题与实验资料，docs负责学习文档。根目录普通文件仅main.cpp和README.md；Git协作配置在.github，各目录说明从根README进入。

## 当前入口

| 路径 | 职责 | 可独立使用 |
| --- | --- | --- |
| [main.cpp](../../main.cpp) | 单文件交互式求解器 | 提交时仅需此文件 |
| [dev/tools/local_judge.py](../../dev/tools/local_judge.py) | 子进程交互、轨迹计分、合成曲线 | Python标准库 |
| [dev/tools/compare_solvers.py](../../dev/tools/compare_solvers.py) | 配对比较、逐族统计、JSON重放 | Python标准库 |
| [dev/run.py](../../dev/run.py) | 面向读者的离线命令 | check/smoke需g++ |
| [automation/judge.py](../../automation/judge.py) | 统一线上评分入口，转交online_judge实现 | 优先使用包内虚拟环境 |
| [data/versions/](../../data/versions/README.md) | 评分字节归档、开发候选、实验元数据 | 按清单核对 |
| [automation/](../../automation/README.md) | 调度说明与提示词模板 | 调度依赖用户自己的客户端 |

## 数据怎样流动

离线：合成数组只归判题器所有；求解器只能收到自己查询位置的回复。判题器保存完整曲线和轨迹以便重放。

线上：用户维护的专用浏览器会话负责登录；工具保存源码快照、绑定作品ID并确认终分；策略记录器保护最高分源码。榜首参考独立缓存，不替代作品判分。

自动化：客户端调度唤醒智能体，智能体通过CLI执行上述流程。本仓库没有独立运行的MCP server，也没有在克隆后自动安装的系统定时器。

## 持久研究与本机状态

| 内容 | 放置位置 | 版本管理 |
| --- | --- | --- |
| 赛题、说明、代码、合成生成器 | 对应公开目录 | 保留 |
| 正式分数与不可变源码 | data/versions、正式记录 | 保留 |
| 候选设计与日研究总结 | docs中的研究资料 | 只保留已整理的证据 |
| 编译产物、完整大报告 | dev/build、dev/tmp | 忽略 |
| 浏览器profile、虚拟环境、提交任务和榜单缓存 | automation/online_judge的本机目录 | 忽略 |
| 客户端定时任务配置、账户用量、凭据 | 用户客户端或automation/local | 不导出到仓库 |

有效任务与实验JSON的路径已迁移到新布局，源码哈希不变。历史文档原文可能仍记录旧目录，这是当时的上下文；执行时以当前README为准。首次克隆运行dev/tools/setup_repository.py，把共享Git规则模板安装到本地.git/info。

## 文档层次

concepts解释为什么，guides说明怎么做，reference说明边界和工程状态，archive保存旧版本原文。仍在持续生成或被定时任务引用的正式记录和研究文档保留原路径，由[文档导航](../README.md)统一索引。
