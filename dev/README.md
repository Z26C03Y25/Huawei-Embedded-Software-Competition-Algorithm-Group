# 开发、构建与测试

[返回首页](../README.md)

本目录集中放置开发工具、测试代码与本机构建产物，不负责上传作品。

| 路径 | 内容 |
| --- | --- |
| [run.py](run.py) | 统一离线入口：build / smoke / check / diagnostics / docs |
| [tools/](tools/README.md) | 判题器、曲线生成、配对对比、实验辅助工具 |
| [tests/](tests/README.md) | 判题器、求解器与性能反例 |
| build/ | 编译程序和本次验证报告，不进入Git |
| tmp/ | 测试临时数据、临时虚拟环境，不进入Git |
| editor/ | 本机编辑器配置备份，不进入Git |

```bash
python dev/run.py smoke
python dev/run.py check
python dev/run.py diagnostics
```

前两项分别用于烟测和核心检查；最后一项保留已知性能失败，不将它们隐藏成全通过。需要Python 3.10+和GCC C++17。详细说明见[快速开始](../docs/guides/quickstart.md)。

第一次克隆后，可运行 `python dev/tools/setup_repository.py` 将Git规则模板安装到本地.git/info；不会创建根目录配置文件或访问网络。
