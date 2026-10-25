# 快速开始：离线跑通一次实验

[文档导航](../README.md)

## 环境

Python 3.10或更新版本、支持C++17的GCC g++。Windows可使用已安装的MinGW工具链并将g++加入PATH；Linux使用发行版的GCC工具链。源码使用bits/stdc++.h，默认面向GCC，不提供原生MSVC支持。

```bash
python --version
g++ --version
python dev/run.py smoke
```

所有命令从仓库根目录运行。使用py启动器时，将python替换为py -3。无需安装任何Python包，离线工具使用标准库。

## 输出在哪里

| 产物 | 路径 |
| --- | --- |
| Windows可执行文件 | dev/build/main.exe |
| Linux可执行文件 | dev/build/main |
| 含每例完整轨迹的烟测报告 | dev/build/smoke.json |

控制台逐例输出score、q、travel、osc、red、d、status。Q和O合法但d或R超限，是合法交互下的零分，不是协议错误。当前烟测程序的退出码只检查交互状态，分数要看报告。

## 手动运行和TRACE

先创建build目录，再编译。以下示例为PowerShell：

```powershell
New-Item -ItemType Directory -Force dev/build
g++ -O3 -Wall -Wextra -Wpedantic -std=c++17 main.cpp -o dev/build/main.exe
python dev/tools/local_judge.py --program dev/build/main.exe --suite smoke --program-arg=--trace --json-output dev/build/trace.json
```

Linux将目录创建改为mkdir -p dev/build，程序路径改为dev/build/main。TRACE只写到stderr；不要让调试信息进入stdout交互协议。

不要把整条数组直接重定向给main程序。裁判必须在每次查询之后回复该位置的值；Python判题器已经实现这个握手。

## 下一步

```bash
python dev/run.py check
python dev/tools/local_judge.py --list-cases --suite extended
```

更完整的性能诊断见[测试分层](testing.md)。如果要比较自己的候选，先读[实验复现](reproduction.md)。线上提交和浏览器配置是[可选进阶部分](../../automation/online_judge/README.md)。
