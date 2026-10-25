# Git协作配置

根目录仅保留main.cpp和README.md。协作模板与Git规则源文件统一保存在此目录。

- workflows/：离线CI。
- ISSUE_TEMPLATE/、PULL_REQUEST_TEMPLATE.md：问题与贡献模板。
- CONTRIBUTING.md、SECURITY.md：贡献和账号信息处理说明。
- repository.gitignore、repository.gitattributes：跨目录忽略与字节保护规则模板。

首次克隆运行 `python dev/tools/setup_repository.py`，规则写入该仓库本地.git/info/exclude和.git/info/attributes，保留已有自定义内容。各功能目录也自带必要的忽略/属性规则。CI同样执行该初始化步骤。

Git内部数据不随仓库分享，因此新环境需要执行初始化；它不会连接网络，也不创建根目录配置文件。
