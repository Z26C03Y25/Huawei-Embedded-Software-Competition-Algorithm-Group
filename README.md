# 华为嵌入式软件大赛 · 算法组

交互式自动聚焦：在有限查询、移动和振荡预算下寻找原始清晰度最大点。

[学习导航](docs/README.md) · [English](docs/README.en.md) · [贡献说明](.github/CONTRIBUTING.md)

已记录最高正式总分 **207650**（2026-10-27，同分两次确认）。[最高分源码](data/versions/main_online_207650.cpp) · [实验记录](docs/持续线上优化记录.md)

## 按功能找文件

根目录只放提交入口 main.cpp 和本说明。其余内容集中为四类：

| 目录 | 用途 | 主要入口 |
| --- | --- | --- |
| **automation/** | AI自动化、线上提交、读取与恢复判分、榜首缓存 | [线上评分入口](automation/judge.py)、[使用说明](automation/README.md) |
| **dev/** | 开发工具、测试、构建产物和临时测试数据 | [运行入口](dev/run.py)、[目录说明](dev/README.md) |
| **data/** | 原始赛题、历史源码、实验参数和正式分数 | [数据导航](data/README.md) |
| **docs/** | 评分讲解、源码导读、实验复现和研究文档 | [学习路线](docs/README.md) |

~~~text
.
├── main.cpp
├── README.md
├── automation/           # 线上评分与AI自动化
│   ├── judge.py          # 对外统一命令
│   ├── online_judge/     # 判分实现和本机浏览器环境
│   ├── prompts/          # 自动优化提示词
│   └── mcp/              # 应用/MCP接入说明
├── dev/                  # 构建与测试
│   ├── run.py
│   ├── tools/            # 本地判题、曲线生成与配对对比
│   ├── tests/
│   ├── build/            # 编译产物和报告，忽略
│   └── tmp/              # 临时测试数据，忽略
├── data/
│   ├── problem/          # 原始赛题PDF
│   └── versions/         # 历史版本、哈希和实验记录
├── docs/
└── .github/              # CI、协作模板和Git规则模板
~~~

.git是本机Git内部目录。Git规则安装到.git/info，各功能目录也有必要规则；不再在根目录放辅助说明或配置文件。

当前按[综合得分与鲁棒性](docs/daily_research/2026-10-26-total-score.md)筛选：平均分包含零分，报告整体零分率和低尾表现；个别退化不再自动否决整体收益。

当前采用[本地优先研究](docs/daily_research/2026-10-26-local-first.md)：22族样例分开发/选择/偏移留出筛算子；自动线上验证每天最多3次，可以为0。

新一轮[混合难例与多分支实验](docs/daily_research/2026-10-26-multi-branch.md)保留困难整族失败，比较四种算子及八个候选，并在经典/混合两域独立确认。

## 离线运行

需要Python 3.10+和支持C++17的GCC g++，以下命令不访问平台：

~~~bash
# 首次克隆：初始化本地Git忽略与字节保护规则
python dev/tools/setup_repository.py

# 编译并运行真实管道烟测
python dev/run.py smoke

# 核心回归与文档检查
python dev/run.py check
~~~

烟测报告在dev/build/smoke.json。退出为0表示交互正常，仍需查看逐例分数和零分原因。[详细步骤](docs/guides/quickstart.md)

## AI与线上评分

~~~bash
# 检查本机浏览器及依赖配置，不上传
python automation/judge.py doctor

# 只读最新作品成绩
python automation/judge.py latest

# 提交当前main.cpp并确认正式终分，会消耗比赛次数
python automation/judge.py submit
~~~

统一入口会优先使用automation/online_judge/.venv。第一次拉取仓库请按[新用户启动指南](automation/GETTING_STARTED.md)安装依赖，并登录自己的比赛账号。

提交结果按作品ID绑定，连续两次相同终分后确认；结果不确定时恢复原任务，不重复上传。榜单只读第一页，重点参考榜首，共用至少两小时缓存。[自动化与额度规则](automation/README.md)

## 从哪里学习

1. [赛题](data/problem/README.md)与[评分解释](docs/concepts/problem-and-score.md)。
2. [源码导读](docs/concepts/solver-walkthrough.md)与[实验复现](docs/guides/reproduction.md)。
3. [已知限制](docs/reference/known-limitations.md)与[后续方向](docs/下一轮优化分析.md)。

强制条件为Q≤199、振荡≤6、真实冗余≤199、停车误差≤3。当前默认策略不能保证任意隐藏数组命中。完整策略诊断仍保留已知失败：

~~~bash
python dev/run.py diagnostics
~~~

当前暂未设置许可证。原始赛题权利以发布方为准；仓库不包含官方隐藏测试集。
