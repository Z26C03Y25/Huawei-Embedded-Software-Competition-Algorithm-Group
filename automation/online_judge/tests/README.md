# 线上工具的离线测试

[工具说明](../README.md) · [全仓库测试导航](../../../dev/tests/README.md)

```bash
python -m unittest discover -s automation/online_judge/tests
```

测试使用保存的HTML、模拟浏览器页面、假时钟、临时任务目录和接口载荷。它们不会连接Chrome、访问比赛平台或上传作品，运行这组测试不需要安装Playwright。

覆盖API/DOM读取、稳定作品身份、两次相同终分、上传结果不确定时禁止重传、并发锁、浏览器适配、第一名数据解析和共享两小时缓存。最近一次本地验证为133个测试通过；新增测试后以实际输出为准。

真实站点结构变化仍需要授权后的单独验证。克隆者不应复制其他人的profile、Cookie或提交任务来运行在线命令。
