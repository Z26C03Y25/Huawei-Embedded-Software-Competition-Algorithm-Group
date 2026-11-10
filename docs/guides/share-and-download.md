# 下载与运行

仓库保留算法源码、历史正式版本、实验数据、研究文档与自动评测工具。编译产物、编译器、Python运行时、浏览器缓存和登录信息由每台电脑自行准备。本机这些文件仍保留，不会被删除。

## 下载项目

在GitHub仓库页点击 Code → Download ZIP，或运行：

```powershell
git clone https://github.com/Z26C03Y25/Huawei-Embedded-Software-Competition-Algorithm-Group.git
cd Huawei-Embedded-Software-Competition-Algorithm-Group
```

## 编译与离线测试

准备Python 3.10或更新版本和支持C++17的GCC。Windows也可将便携w64devkit放在 `dev/toolchains/w64devkit`，Python放在 `python/runtime`，通过完整路径调用，无需修改环境变量。

```powershell
python dev/run.py build
python dev/run.py smoke
```

`main.cpp` 是交互式程序，需要判题器回复每次查询，不能通过双击完成测试。烟测使用合成曲线，不能代替线上成绩。当前无打表版本正式218796分，历史224148版本另外归档。

## 在线评测

按[新用户启动说明](../../automation/GETTING_STARTED.md)安装依赖并登录自己的账号。浏览器路径不同时，复制 `automation/online_judge/config.example.json` 为 `config.local.json`，修改Chrome路径，按说明使用 `--config` 参数。

历史研究数据中的时间、绝对路径、任务编号和控制器状态只用于核对证据；另一台电脑应新建自己的运行任务，不应直接运行旧日期的连续提交控制器。
