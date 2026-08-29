# 开发交接

> 这是项目唯一权威交接文档。新信息直接并入本文档，Git 保存历史。  
> 对应版本：0.1.1  
> 最后核对：2026-08-29。

## 项目定位和范围

为 Cockpit 多账号切换后的 Antigravity 自动检查专用代理、清除黑屏实例并恢复启动。

## 唯一真源与禁止覆盖的资产

- 源码：`src/`。
- 开发交接：本文档。
- 版本：`VERSION`。
- 禁止覆盖：待按项目补充。

## 架构、模块和启动方式

- `Antigravity-Recovery-Launcher.exe`：稳定桌面入口、进度窗口、调用监督器。
- `Antigravity-AccountWatcher.exe`：监控 Cockpit 当前账号和无代理 `--reuse-window` 实例。
- `Antigravity-ProxySupervisor.ps1`：配置/启动 17897、关闭旧实例、注入代理并验证 language server。
- `build.ps1` 构建；`install.ps1` 备份并安装桌面入口和 HKCU Run 监控器。

## 数据、同步、迁移、备份和恢复

运行数据留在 `%LOCALAPPDATA%\Antigravity`；源码和发布物在本项目。安装不会迁移或清理 Antigravity 用户数据。

## 配置、隐私、密钥和权限边界

不保存账号凭据或节点密钥。不会修改 Google 付款资料、账号地区、全局代理或外部账号状态。

## 版本、构建、发布和回滚

- 当前版本：0.1.1。
- 构建：Windows .NET Framework 4.0 C# 编译器生成两个 winexe，脚本执行语法检查。
- 发布：`releases/current`，桌面快捷方式直接指向正式 EXE。
- 回滚：恢复 `shortcut-backups` 中的快捷方式，删除 HKCU Run 的 `AntigravityAccountWatcher` 值并停止本项目监控器；不删除用户数据。

## 测试和当前验收

- 2026-08-29 20:40：正式 EXE 退出码 0；唯一主进程 PID 29972 带 `17897`；language server PID 32168 到专用端口有 8 条连接；状态为 ready。
- 2026-08-29 20:53：`17897` 已改为转发现有全局 `7897`，出口从美国变为日本；监督器 1.6.0，主进程 PID 26728，language server PID 39544，有 8 条连接。
- 已复现并自动修复 Cockpit `--reuse-window` 顶掉正确实例导致的黑屏。
- 真实模型回复仍是独立验收层；账号地区 400 不能由本地 ready 代替。

## 已知问题、技术债和风险

- 目标 Mihomo 路径和订阅节点匹配仍是本机值，跨电脑前需做自动发现配置。
- Antigravity 窗口不允许自动注入测试消息，因此真实模型验收需要用户发送一条消息，再读取日志判定。

## 当前状态和下一步

- 状态：维护。
- 下一步：观察 Cockpit 再次切号后监控器是否持续稳定；真实消息按 ResponseID 和无新 400 验收。
- 下一位维护者先读：`README.md` 和 `docs/DESIGN.md`。
- 禁止：删除登录态/会话、伪造账号地区、修改全局 7897，或用 Google 204 冒充模型成功。

## 维护规则

架构、数据源、目录、持久化、发布流程、重要业务规则或已知风险变化时，必须同步更新本文档。

