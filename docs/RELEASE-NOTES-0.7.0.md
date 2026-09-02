# Antigravity Windows Recovery Launcher 0.7.0

首次公开发布完整 Windows 恢复套件，把中文界面、专用代理、真实模型资格检查、节点轮换和 Cockpit 切号恢复合并为一个桌面启动入口。

## 核心变化

- 桌面只保留一个 `Antigravity 启动器`。
- 从 Clash Verge 与 Mihomo Party 本地缓存发现跨订阅美国候选，不上传或复制订阅。
- 每个候选先通过 Google/OAuth/US 基础检查，再通过 Google 官方 Antigravity CLI 的最小真实 `OK` 生成门禁。
- 地区 400、断流和错误出口自动冷却并切换候选。
- 通过 CDP Loader 注入可逆简体中文界面，不修改 `app.asar`、登录态、会话或项目数据。
- AccountWatcher 对真实切号、代理绕过和专线上游故障做有界恢复，避免无限重启。
- 日常 Clash `127.0.0.1:7897`、规则模式和用户当前节点保持不变；Antigravity 独立使用 `127.0.0.1:17897`。

## 安装

1. 安装并登录官方 Antigravity。
2. 安装 Clash Verge 或兼容的 Mihomo 客户端，并由用户自行导入合法订阅。
3. 解压本 Release 的 ZIP。
4. 双击解压目录根部的 `Install.cmd`，等待安装完成。
5. 双击桌面的 `Antigravity 启动器`，等待真实模型门禁完成。

`Install.cmd` 会调用同目录中可审计的 `install.ps1`。安装脚本会从 Google 官方更新清单下载 `agy` 并校验官方 SHA-512；Release 本身不分发 `agy.exe`、Mihomo、代理订阅或任何凭据。

## 已知限制

- Google 会动态限制部分机房/托管出口；美国 IP、Google 204 或模型列表正常都不等于真实生成可用。
- 成功探针会使用少量账号额度，只在启动和真实故障恢复时执行，不作为高频心跳。
- 首次使用需要已经存在的 Antigravity 官方登录态；本工具不自动处理登录、验证码或账号地区。
- 当前支持 Windows x64，并重点验证 Antigravity 2.11.0。

完整安全边界、回滚和故障排查见仓库 README、SECURITY 与 `docs/`。
