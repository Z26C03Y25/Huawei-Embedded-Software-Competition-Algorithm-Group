# 线上提交与判分

目标页面：[华为嵌入式软件大赛提交](https://developer.huaweicloud.com/competition/information/1300000312/submission)。源码入口为仓库根目录 `main.cpp`。

这是可选的线上工具。先完成[离线快速开始](../../docs/guides/quickstart.md)；普通测试不会上传，也不需要登录。调度、账户限制与每日研究流程见[automation](../README.md)。

## 配置自己的环境

配置模板为 [config.example.json](config.example.json)。现有config.json保留兼容；新使用者可复制模板为config.local.json，修改Chrome路径，再使用：

```powershell
python automation/online_judge/judge.py --config automation/online_judge/config.local.json doctor
```

实时命令需要安装requirements.txt中的Playwright及本机Chrome。setup_environment.py支持创建Windows或Linux虚拟环境；Windows便捷脚本见下文。Linux需在本地配置中填写真实Chrome路径，使用.venv/bin/python。该工具未承诺跨平台浏览器全部实测。profile、runs、虚拟环境和*.local.json已在忽略列表。

## 快速使用

在仓库根目录运行 PowerShell：

```powershell
# 第一次安装；本机独立虚拟环境已配置时可以跳过
.\automation\online_judge\setup.ps1

# 启动专用 Chrome 窗口，第一次在这个窗口手动登录华为云
.\automation\online_judge\judge.ps1 browser

# 读取当前页面第一行
.\automation\online_judge\judge.ps1 latest

# 读取榜单第一页和榜首参考；共享两小时缓存，不翻页、不上传
.\automation\online_judge\judge.ps1 ranking

# 上传当前 main.cpp 的不可变快照，并等待该次成绩
.\automation\online_judge\judge.ps1 submit
```

`browser` 使用 `C:\Program Files\Google\Chrome\Application\chrome.exe`，登录保存在本目录的 `.chrome-profile/`。登录、验证码由使用者手动完成，脚本操作比赛提交页及只读榜单页，不读取或复制其他 Chrome profile 的 Cookie。

本机 Playwright 已安装在 `.venv/`。也可以直接使用虚拟环境 Python，方便 Codex 发起命令和解析 JSON：

```powershell
.\automation\online_judge\.venv\Scripts\python.exe automation/online_judge/judge.py doctor
.\automation\online_judge\.venv\Scripts\python.exe automation/online_judge/judge.py latest
.\automation\online_judge\.venv\Scripts\python.exe automation/online_judge/judge.py submit --file main.cpp --timeout 600
```

没有配置 PowerShell 脚本执行权限时，直接使用上面的 Python 命令即可，无需修改执行策略。新机器可用 `python automation/online_judge/setup_environment.py` 安装依赖。

## 成绩读取规则

默认 `score_source: "auto"`：优先读取 Chrome 页面自身发出的查分接口响应，接口不可用或结构变化时回退到 DOM。`latest` 返回接口结果/页面顺序的第一条，`history` 返回当前页记录，不会按分数排序。用户提供的例子中：

```json
{
  "filename": "main.cpp",
  "submitted_at": "2026-10-24 18:22:20",
  "score": 145904,
  "status": "success",
  "source": "api"
}
```

第二行 154353 不是最新成绩。提交时间保留网页原文，按中国标准时间理解；本地任务时间使用带时区的 ISO 字符串。这条历史成绩未与任何本地源码哈希强行绑定。

## CMD 出现 Cannot connect 时

先启动脚本专用 Chrome，再查看成绩和提交：

```cmd
cd /d "D:\work\2026华为嵌入式软件大赛-算法组"
automation\online_judge\.venv\Scripts\python.exe automation\online_judge\judge.py browser
```

等命令输出 `"state": "browser_ready"`，在弹出的窗口手动登录并保持窗口开启，然后执行：

```cmd
automation\online_judge\.venv\Scripts\python.exe automation\online_judge\judge.py latest
automation\online_judge\.venv\Scripts\python.exe automation\online_judge\judge.py submit
```

普通方式打开的 Chrome 没有脚本所需的本机调试端口。若 `browser` 自身报错，请保留它的完整输出进行诊断；不要通过关闭所有 Chrome 或删除运行中 profile 的锁文件来尝试修复。脚本连接本机调试服务时绕过 HTTP 代理，并区分调试端口不可访问、非 Chrome 响应、Playwright 握手失败。

接口为 `POST https://devdata2.huaweicloud.com/rest/developer/fwdu/rest/developer/user/hdcompetitionservice/v1/works/get-competition-works`。脚本监听页面实际发送的请求及响应，不单独重放请求，不猜测 `competition_id/stage_id`，也不读取、复制或保存 Cookie、CSRF、请求头或请求体。页面自身处理登录和动态凭据；401/403 会明确提示手动重新登录，不用旧 DOM 分数掩盖鉴权错误。

响应 `results` 按原顺序解析，只保留作品 `id`、`name`、`created_time`、`score`、`status/message` 的规范化判分信息和 `stage_name`。不保存原始响应或用户/域信息。实测 `created_time` 的无时区字符串为 UTC，转为北京时间后与页面一致；`is_invalid=true` 在实测成功作品中也存在，因此不能据此认定判题失败或 0 分。

提交前记录历史身份；API 模式优先用稳定的作品 `id` 识别新提交和跟踪结果，也支持同一秒的不同作品。旧分页记录仍会通过时间屏障排除。DOM 回退及旧任务继续兼容 `文件名 + 提交时间` 规则，TinyGrid 的 `data-rowid="row_1"` 只是当前行号，不能用作持久提交 ID。绑定后即使该次记录落到第二行，`wait` 也继续跟踪同一条记录。已经绑定 API 作品 ID 的任务，暂时只能拿到无 ID 的 DOM 结果时继续等待 API，不擅自换到同秒的另一作品。

等待时必须有明确 `success` 状态，并连续两次观察到相同终分才结束。排队中的 `0`、空分数和未知状态继续等待；明确成功后的真实 0 分可以正常返回。`latest` 是原始观察，不负责等待终态。

## 低频读取第一页与榜首参考

```powershell
# 独立读取榜单，不上传、不消耗提交次数
automation\online_judge\.venv\Scripts\python.exe automation\online_judge\judge.py ranking
```

榜单地址为 [打榜排名](https://developer.huaweicloud.com/competition/information/1300000312/ranking)。按用户要求，只读第一页，重点关注榜首分数，取消所有自动翻页。需要更新且两小时缓存期已过时，才在现有专用 Chrome 中打开独立临时标签页，监听页面自身的榜单响应；不重放请求或读取请求凭据，只保留公开字段。

独立命令和提交后的自动参考共享 `runs/rankings/` 的缓存与跨进程锁，至少间隔两小时才允许再次实际读取；失败尝试也先写入两小时冷却，避免连续重试。没有强制刷新选项。已有历史完整快照会在本地裁成第一页视图，保留真实采集时间，不为迁移数据再次访问服务器。读取结束只关闭自己新建的标签页。

快照保存到 `automation/online_judge/runs/rankings/`，包括第一页 JSON、CSV 和 `latest.json`。`scope=first_page`，`row_count` 是本页条数，`total` 是榜单总条数；`complete=false` 是正常的第一页结果，不代表读取失败，不触发补抓。重点字段为 `leader` 和 `gap_to_leader`；自己不在本页时，不推断全榜中紧邻自己的上一名。`captured_at` 是实际读取时间，`refreshed_at` 是榜单自身刷新时间，均带北京时间时区。`check_state.json` 记录下次可读取时间；命令输出的 `cache_hit` 表示复用缓存，`stale` 表示刷新失败后保留旧参考。`--output-dir PATH` 仅导出本地结果，不绕过共享缓存。

默认配置已启用 `capture_ranking_on_completion: true`。`submit` 或 `wait` 在同一作品正式终分被连续两次确认后，自动附带缓存中的榜首参考；仅在允许的更新时点按需读第一页，不是每次判分都发起榜单请求。`ranking_after` 保留参考路径、缓存状态和下次检查时间。没有可用参考时只记 `ranking_error`，不改变已确认分数，不触发重传；后续检查仍受两小时冷却约束。

榜单有独立刷新周期，提交判完不代表榜单已经包含新分数。`gap_from_submission_to_leader` 是该次已确认作品分数与快照榜首的数值差；`gap_to_leader` 是榜单中当前队伍分数与榜首的差，二者不能混用。榜单只作竞争分数参考，不用于确认作品判分，也不能据此推断别人的算法或逐例成绩。

## 任务、恢复与防重复

每次提交保存在 `runs/<job_id>/`：

- `main.cpp`：上传的确切字节快照；即使之后修改工作区文件，也不改变这次提交。
- `job.json`：源码 SHA-256、大小、原路径、提交前记录、绑定身份、判分状态、成绩和错误。

```powershell
# 上传另一个版本，平台看到的文件名仍为 main.cpp
.\automation\online_judge\judge.ps1 submit --file data/versions/main_v1_154353.cpp

# 查看任务列表或完整记录
.\automation\online_judge\judge.ps1 jobs
.\automation\online_judge\judge.ps1 jobs --job JOB_ID

# 超时/断网后继续等待，不重新上传
.\automation\online_judge\judge.ps1 wait JOB_ID --timeout 600

# 只发送一次上传动作并立即返回任务，之后用 wait 接续
.\automation\online_judge\judge.ps1 submit --no-wait

# 相同源码已经判完时，默认复用成绩；明确需要重新上传才使用此参数
.\automation\online_judge\judge.ps1 submit --repeat
```

任何可能启动上传的动作之前，先持久化 `delivery_uncertain` 状态。动作超时或中途崩溃后，再次运行相同源码的 `submit` 只恢复查询，不会盲目上传第二次。只有 `snapshot_ready`（上传意图尚未写入）可以安全开始首次上传。不同源码的旧任务尚未结束时，脚本拒绝再提交新代码；跨进程锁也会阻止同时提交。

API 提供稳定作品 ID，DOM 表格本身没有该 ID。人工同时提交、多个新候选或记录翻页消失，仍可能使本次源码的归属无法确定。出现歧义时返回 `ambiguous`，不擅自取最高分或第一行。核对候选后可显式选择：

```powershell
.\automation\online_judge\judge.ps1 jobs --job JOB_ID
.\automation\online_judge\judge.ps1 bind JOB_ID --submitted-at "2026-10-24 18:22:20"
.\automation\online_judge\judge.ps1 wait JOB_ID
```

`bind` 只允许选择该歧义任务保存的唯一候选时间；同秒多个候选仍会拒绝绑定。它只更新本地关联，不上传。若记录离开当前页，先手动让该记录回到可见列表，再恢复 `wait`。

退出码：`0` 为读取正常或已完成；`2` 为等待中/超时；`3` 为平台明确判题失败；`4` 为身份歧义；`5` 为浏览器、配置或本地错误。超时会保留任务，不能当作 0 分。

## 页面适配

`config.json` 已配置用户提供的路径和控件：

- 按钮：精确文本 `上传作品`。
- 表格：`div.tiny-grid__body-wrapper table.tiny-grid__body`。
- 空列表提示：`div.tiny-grid__body-wrapper .tiny-grid__empty-block`。
- 列：`col_1` 文件名，`col_2` 类型，`col_3` 提交时间，`col_7 .scoringBox` 成绩，`col_6` 状态。

`score_source` 可设为 `auto`（API 优先、DOM 兜底）、`api`（只使用新 API 响应）或 `dom`（只使用表格）。DOM 读取会等待异步渲染完成，确认有有效记录；真实空列表必须有明确可见空提示及已稳定的网络状态，不把刚挂载的零高度空表当作查分结果。

上传按钮只点击一次，然后处理文件选择器或唯一的 `input[type=file]`。若页面另外要求确认提交，请观察实际按钮文本后设置 `confirm_button_text`；默认不猜测并点击不明按钮。多个上传控件、多个表格或登录失效都会报错，并保留可恢复任务。

默认调试端口为本机 `127.0.0.1:9222`，仅支持回环地址；`.chrome-profile/`、`.venv/`、`runs/`、安装临时目录均不进入 Git。Chrome 调试会话采用独立 profile，符合 [Chrome 对调试目录的要求](https://developer.chrome.com/blog/remote-debugging-port)。连接与选文件分别使用 [Playwright CDP](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp) 和 [文件上传接口](https://playwright.dev/python/docs/input#upload-files)。

## 离线自检

以下命令不会启动 Chrome、登录或上传：

```powershell
.\automation\online_judge\judge.ps1 doctor
.\automation\online_judge\judge.ps1 latest --html automation/online_judge/samples/submissions.html
.\automation\online_judge\.venv\Scripts\python.exe -m unittest discover -s automation/online_judge/tests -v
```

当前离线工具测试最近验证为133项通过，包含判分身份、防重复上传及第一页共享缓存。真实提交流程已有后续正式实验记录，见[优化总结](../../docs/持续线上优化总结.md)。测试数量不是所有策略性能用例都通过的声明。新环境先运行browser并手动登录，再用latest验证读取正常，最后按本人授权决定是否submit。
