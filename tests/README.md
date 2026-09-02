# 测试与验收

记录可重复执行的语法、单元、集成、回归和手动验收方法。不要只写“已测试”，必须包含命令、环境和真实结果。

## 0.7.0 真实模型门禁与公开包

```powershell
& .\tests\run-account-watcher-tests.ps1
& .\tests\run-failover-policy-tests.ps1
node .\tests\localization-extension.test.js
node .\tests\shareable-assistant.test.js
& .\build-release.ps1
```

故障转移策略必须声明真实模型门禁并提供不少于 30 秒的探针超时。公开发布构建会扫描常见代理协议、订阅 Token 和秘密赋值模式；ZIP 中不得出现 `agy.exe`、运行日志、生成 Mihomo 配置、账号文件或订阅缓存。实机最终还应确认最小生成返回 `OK`、桌面和 language server 使用 17897、日常 7897 未改变。

## 0.5.0 持续健康与故障转移

```powershell
& .\tests\run-account-watcher-tests.ps1
& .\tests\run-failover-policy-tests.ps1
```

策略测试要求：一次和两次网络失败不切换，连续三次才恢复；新地区 400 立即轮换；后台原因只映射到三种受控监督器模式。节点池测试只读取当前活动 Clash 配置，不改运行状态；本机应发现至少 2 条唯一洛杉矶候选、已验证主节点排序第一、冷却不少于 15 分钟。

实机验收还必须确认：断流恢复只改变 `17897` 专用 Mihomo；`7897` PID、系统代理和 Clash 规则模式不变；后台不弹窗；新候选通过 Google/OAuth/US 预检；最终由用户正常对话后的新 `ResponseID` 确认模型可用。

## AccountWatcher 0.4.1 防无限重启回归

```powershell
Set-Location 'D:\AICode\工具开发\projects\antigravity-recovery-launcher'
& .\tests\run-account-watcher-tests.ps1
```

策略测试覆盖：同账号文件写入不修复、A→B 只修复一次、重复 B 不再触发、修复中和启动器运行中不并发、成功冷却、失败最多 3 次并退避，以及 `runtime_proxy_bypass` 仍可触发。安装后还必须实机观察 `account-watcher.log` 与 Antigravity PID，静态通过不能代替运行稳定性验收。

2026-08-30 实机结果：9 项策略测试、汉化扩展测试、分享版隔离测试、正式构建和安装均通过。新版 watcher 启动后捕获一次 Cockpit 同账号写入并记录 `accounts_file_write_ignored`；45 秒连续观察中 PID 36036 不变、新增修复为 0、Loader/启动器不常驻、17897 有 3 条已建立连接。当前窗口因安装不打断策略仍为旧 marker 0.3.1，待用户下次主动启动中文版后再做 0.4.0 marker 复验。

## 0.4.0 外部中文扩展与分享包回归

```powershell
Set-Location 'D:\AICode\工具开发\projects\antigravity-recovery-launcher'
node .\tests\localization-extension.test.js
node .\tests\shareable-assistant.test.js
& .\build.ps1
& .\build-shareable.ps1
```

静态扩展测试覆盖：MV3 manifest、本地 URL 匹配、全部必需词条、长句替换、UI 短词隔离、动态数量/时间/权限文案、属性翻译、对话标题保护、80 ms 防抖、300 ms 最大等待和 `MutationObserver`。构建后还应确认 `releases\current\localization-extension\manifest.json` 与三个切换入口存在。

当前客户端已通过 Loader 注入时，可额外执行只读界面检查：

```powershell
node .\tests\live-ui-check.js
```

该检查只读取 DevTools 的 DOM 文本和扩展标记，不点击、不输入、不发送模型请求；页面路由只显示部分文案时，`chineseMatches` 以当前可见内容为准。

```powershell
Set-Location 'D:\AICode\工具开发\projects\antigravity-recovery-launcher'
& .\build.ps1
& .\install.ps1
Start-Process '.\releases\current\Antigravity-Recovery-Launcher.exe'
```

验收项：

1. `releases/current` 两个 EXE 和监督器脚本存在，PowerShell 脚本语法检查通过。
2. 桌面与用户开始菜单的 `Antigravity.lnk` 均指向正式 `Antigravity-Recovery-Launcher.exe`，旧入口有时间戳备份。
3. `127.0.0.1:7897` 与 `127.0.0.1:17897` 均监听，17897 的拥有进程命令行指向 `mihomo-antigravity.yaml`。
4. Antigravity 唯一主进程命令行含 `--proxy-server=http://127.0.0.1:17897`，language server 有到 17897 的连接。
5. 连续启动两次时，第二次在配置和端口健康的情况下记录 `proxy_reused`，不因语言日志中的历史地区 400 重启代理。
6. 启动前官方 CLI 最小真实生成必须返回 `OK`；如进行桌面验收，再从新请求后的日志判断 `ResponseID` 或新的地区错误。
7. `17897` 通过 Cloudflare trace 的 `loc` 必须为 `US`，状态文件包含 `egress_country=US`；否则启动必须停止。
8. Cockpit 账号文件发生写入但 `current_account_id` 未变时不得恢复；A→B 应触发一次，重复 B 不得再次触发；账号和运行时修复失败均不得超过 3 次。
9. 若同时存在带 `17897` 和不带 `17897` 的 Antigravity 主进程，监控器必须判定为需要修复。
10. 在账号监控器运行时重复执行 `build.ps1`，应先停止同一路径旧监控器并成功覆盖构建，不得影响其他同名进程。
11. 执行 `install.ps1` 后，稳定运行目录下应存在两个 EXE 和监督器脚本，桌面/开始菜单快捷方式及 HKCU Run 均指向稳定运行目录，而非源码目录。

## 2026-08-29 实机结果

- PowerShell 语法检查：通过。
- `build.ps1`：通过，生成正式 Launcher、AccountWatcher 和监督器脚本。
- `install.ps1`：通过，桌面与开始菜单快捷方式均已指向正式 Launcher；旧快捷方式已进入带时间戳的备份目录。
- 第一次修复启动：17897 复用，Google `204`、Generative Language 根路径 `404`，Antigravity ready，language server 8 条连接。
- 第二次修复启动：17897 仍复用，历史地区 400 重启计数不变，Antigravity ready，language server 7 条连接。
- 未完成项：因 Computer Use 平台策略拦截 Antigravity，无法自动输入真实测试消息；不能用连通性状态替代模型回复验收。
- 监控器静态回归：判断的进程名为正式 `Antigravity-Recovery-Launcher`，不再使用旧的 `Antigravity-Launcher`。
- 连通性回归：首次 HTTP 自检瞬时失败时最多重试 3 次；持续失败仍必须阻止启动。
- 目标节点回归：专用配置必须包含当前订阅中的美国2 gemini，不得包含全局 7897 转发，不得自动选择美国1。
- 0.1.4 新增代码检查：PowerShell 语法和 AccountWatcher 编译通过；待正式构建后复验出口国家门禁和账号文件变化路径。

