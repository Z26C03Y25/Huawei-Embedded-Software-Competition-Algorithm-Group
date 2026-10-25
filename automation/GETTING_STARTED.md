# 新用户启动：从仓库到自己的评测环境

[返回首页](../README.md) · [详细工具说明](online_judge/README.md)

## 可以直接复现什么

| 功能 | 条件 |
| --- | --- |
| 离线编译、合成测试、实验重放 | Python 3.10+，GCC g++ C++17 |
| 自动上传一个候选、等待判分、断点恢复 | 再安装Playwright与Chrome，登录本人的比赛账号 |
| AI每天研究、改代码、用完提交次数 | 再配置本人的AI客户端、模型额度和周期任务 |

仓库不会附带作者的虚拟环境、Chrome登录、作品运行状态或客户端定时任务。历史连续控制器是专用实验脚本，不是一个通用AI服务；不要直接复用作者的controller/queue状态。

## Windows默认Chrome路径

在仓库根目录运行：

```powershell
# 1. 初始化本仓库的Git规则；无网络、无上传
python dev/tools/setup_repository.py

# 2. 安装独立虚拟环境与Playwright，需要下载依赖
python automation/online_judge/setup_environment.py

# 3. 启动比赛专用Chrome；第一次手动登录
python automation/judge.py browser

# 4. 登录后只读验证
python automation/judge.py latest

# 5. 确认使用自己的团队次数后，上传main.cpp并等待正式终分
python automation/judge.py submit
```

安装不等于上传；doctor和latest也不会上传。browser_ready只代表调试端口可用，登录仍由本人完成。源码快照、任务、浏览器profile与榜首缓存随后在本机创建，不从作者的运行目录复制。

## Chrome路径或操作系统不同

复制[config.example.json](online_judge/config.example.json)为automation/online_judge/config.local.json，修改chrome_path。执行时显式传自己的配置：

```bash
python automation/judge.py --config automation/online_judge/config.local.json doctor
python automation/judge.py --config automation/online_judge/config.local.json browser
python automation/judge.py --config automation/online_judge/config.local.json latest
```

安装脚本最后用默认配置做doctor。若依赖已装好但默认Chrome路径不存在，会非零退出；这时填写本地配置并运行上面的doctor确认，不必误以为上传发生或全部依赖安装失败。

安装器与包装入口支持Windows/Linux的虚拟环境目录差异；完整实时浏览器流程当前主要在Windows验证，不能把配置支持等同于所有系统实测。

## 配置AI定时优化

离线和只读验证完成后，使用[任务提示词模板](prompts/daily-optimization.md)，填写自己的仓库路径、允许上传的账号与每日次数范围，在自己的客户端创建周期任务。模型与调度能力来自客户端，不由git clone安装。

任务应区分每日提交次数与模型账户用量：平台次数用尽后转离线研究，次日核查刷新；模型额度恢复后从断点继续。榜单只读第一页，共享至少两小时缓存，不因每次提交而重复刷新。

自动化适用于本赛事的接口与页面，尚不是支持任意比赛平台的通用提交器。

## 已验证的范围

2026-10-25使用仅含公开候选文件的干净副本验证，未复制本机虚拟环境、Chrome profile或runs，使用未安装Playwright的Python环境：离线HTML读取、133项工具测试、文档检查和26例烟测均正常执行。doctor明确返回依赖未就绪，符合首次安装前的状态。没有用作者登录替代新用户完成一次真实上传；安装与本人登录仍是在线运行前提。
