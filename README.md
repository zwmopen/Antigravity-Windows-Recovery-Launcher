# Antigravity 恢复启动器

> 项目 ID：`antigravity-recovery-launcher`  
> 版本：0.1.0  
> 状态：维护  
> 服务对象：AI基础设施与 Windows 工作环境  
> 创建日期：2026-08-29

## 为什么开发

为 Cockpit 多账号切换后的 Antigravity 自动检查专用代理、清除黑屏实例并恢复启动。

这个工具必须回到“AI基础设施与 Windows 工作环境”中验证价值；如果不能改善对应系统或项目的现实结果，应停止扩建或重新定义。

## 目标用户

在 Windows 上通过 Cockpit Tools 切换 Antigravity 多个 Google 账号，并需要固定美国专用代理的个人用户。

## 核心使用流程

1. 双击桌面唯一的 `Antigravity` 图标。
2. 小应用检查专用 Mihomo、Google 连通性、Antigravity 设置和桌面入口。
3. 小应用关闭 Cockpit 遗留的无代理或黑屏实例，再以 `127.0.0.1:17897` 完整重启。
4. 后台监控器发现 Cockpit 再次以 `--reuse-window` 覆盖正确实例时，自动重复修复。

## 安装与启动

已安装入口：桌面 `Antigravity.lnk`。

正式应用目录：`releases/current/`。构建运行 `build.ps1`，安装运行 `install.ps1`。

## 数据和隐私

- 运行状态与脱敏日志：`%LOCALAPPDATA%\Antigravity\private-proxy`。
- 不上传数据；不保存账号密码、Cookie、Token 或节点密钥。
- 不清理 Antigravity 登录态、会话和项目；旧快捷方式保存在 `%LOCALAPPDATA%\Antigravity\shortcut-backups`。

## 项目文档

- [设计与原则](docs/DESIGN.md)
- [架构与数据流](docs/ARCHITECTURE.md)
- [开发交接](docs/HANDOFF.md)
- [踩坑与故障排查](docs/TROUBLESHOOTING.md)
- [变更记录](CHANGELOG.md)

## 当前限制

- 本工具只能保证本机启动、代理链和黑屏恢复。Google 返回的账号地区资格 400 仍需以真实对话验收，本工具不能修改账号国家或绕过 Google 风控。

## 源码与发布

- 源码真源：本目录 Git 仓库的 `src/`。
- 发布包：`releases/`；大型二进制不进 Git。
- 中间产物：`.work/`、`build/`、`dist/`，可重建、可删除。

