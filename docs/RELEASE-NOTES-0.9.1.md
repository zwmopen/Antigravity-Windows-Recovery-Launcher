# 0.9.1 发布说明

0.9.1 针对“昨天能用、今天启动后又无回复”的故障收紧了候选来源和失败状态。它仍保持专用 `127.0.0.1:17897` 与日常 Clash `127.0.0.1:7897` 隔离，不修改 Clash 模式、节点、订阅刷新状态或 Antigravity 登录数据。

## 这版解决什么

- 不再把订阅缓存目录里已经过期的历史 YAML 当成今天的备选线路。
- 同时读取 Clash Verge 与 Mihomo Party 的订阅索引，按来源交叉发现日美节点；本机这次发现日本 12 条、美国 13 条，共 25 条有效候选。
- 每条线路仍必须通过配置语法、Google/OAuth、实际出口和官方 `agy` 真实 `OK` 生成门禁；基础连通性不能冒充模型资格。
- 每次运行生成脱敏订阅统计；失败时覆盖旧 `ready` 状态，便于启动器显示真实的本轮失败位置。

## 本地使用

源码开发只需要：

```powershell
Set-Location 'D:\AICode\工具开发\projects\antigravity-recovery-launcher'
& .\build.ps1
& .\install.ps1
```

然后双击桌面的 `Antigravity 启动器`。Setup.exe 和公开 ZIP 不在本机生成，由 GitHub Actions 在远端根据 `VERSION` 构建。

## 验收重点

必须看到 17897 监听、Antigravity 主进程带 17897、language server 连接 17897，并由官方 `agy` 返回结构化 `status=SUCCESS` 与正文 `OK`。`%LOCALAPPDATA%\Antigravity\private-proxy\subscription-report.json` 只包含来源和数量统计，不包含订阅链接、Token、UUID、密码、服务器或账号标识。

## 已知限制

线路是否长期稳定仍取决于用户自己的订阅和 Google 对出口/账号组合的资格判断；日本优先只是本项目策略，不保证每个日本机房出口都有模型资格。若全部日本和美国候选都失败，启动器会安全停止，不自动修改账号地区、购买新代理或切换全局 Clash。
