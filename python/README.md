# 项目内 Python

本机可直接从仓库根目录调用，无需安装程序或修改环境变量：

```powershell
& ./python/runtime/python.exe --version
& ./python/runtime/python.exe dev/run.py smoke
```

`runtime/` 是本机复制部署的 Python 3.12.14 解释器和标准库，来源为 Codex 已捆绑运行时。包含原始 LICENSE；未复制第三方 site-packages。离线评测工具只用标准库。随后为本次授权的线上验证，在此运行时安装了 pip 和 Playwright 依赖；使用本机 Chrome，无需另下载浏览器。旧 `automation/online_judge/.venv` 引用了其他机器的路径，不能直接使用；`automation/judge.py` 现在优先使用项目内运行时。

```powershell
& ./python/runtime/python.exe automation/judge.py doctor
& ./python/runtime/python.exe automation/judge.py browser
& ./python/runtime/python.exe automation/judge.py latest
```

便携 C++ 编译器在 `dev/toolchains/w64devkit/bin/g++.exe`，来源为官方 skeeto/w64devkit v2.10.1 发布包。`dev/run.py build` 和 `smoke` 自动优先使用该位置，也可通过 `--compiler` 指定其他路径；不写系统或用户 PATH。

解释器及编译器属于本机运行环境，不应随算法源码提交。
