# Antigravity 恢复启动器

> 项目 ID：`antigravity-recovery-launcher`  
> 版本：0.7.0
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
2. 小应用检查专用 Mihomo、候选节点来源、Google 连通性、美国出口、真实模型生成资格、Antigravity 设置和桌面入口。
3. 小应用关闭 Cockpit 遗留的无代理或黑屏实例，再以 `127.0.0.1:17897` 完整重启。
4. 后台监控器同时检查 Cockpit 真实切号、运行时代理绕过，以及 `17897 → Google/OAuth` 的持续健康状态。

启动器会校验专用代理的实际出口国家必须为 US。0.7.0 从 Clash Verge 与 Mihomo Party 的本地订阅缓存发现最多 32 条美国候选，按不同订阅交叉排列，并使用 Google 官方 Antigravity CLI 发出最小 `OK` 生成探针。只有真实生成成功的候选才会启动桌面客户端；断流、非 US 出口和地区 400 会隔离 20 分钟。后台每 20 秒检查 Google 与 OAuth，连续 3 次失败才恢复；旧失败会话回放的地区错误会先真实复核当前节点，避免误杀和重启风暴。

自动恢复只重建 Antigravity 专用 `17897` 并在必要时重启 Antigravity；全程不刷新订阅、不切换 Clash 规则/全局/直连、不修改日常节点或系统代理 `7897`。后台恢复不弹窗口，最多重试 3 次并退避，所有候选不可用时停止折腾并留下脱敏原因。

启动器不会因为历史地区限制 400 重启同一条代理链；它只在代理进程、配置或实际连通性异常时修复。专用代理优先读取 Clash 当前运行合并配置，不依赖全局 7897；其他电脑必须重新发现并真实测试可用节点。

用户日常 Clash 保持“规则模式”。启动器不会刷新全部订阅，不会切换规则/全局/直连模式，也不会修改 Clash 日常节点；`7897` 与 Antigravity 专用 `17897` 相互隔离。正常使用直接打开即可；Cockpit 真实切号和专线持续断流都会由后台自动恢复，桌面启动器仍可作为手动兜底。

## 可分享的独立中文助手

0.4.0 新增与本机代理恢复链完全隔离的 `Antigravity 中文助手`。分享给其他 Windows 用户时，只发送 `releases/shareable/Antigravity-Chinese-Assistant-0.4.0-windows-x64.zip`：对方完整解压后双击 EXE，即可启动中文版、恢复英文原版或创建桌面入口。独立版自动发现官方安装目录，不携带 `17897`、Clash 节点、Cockpit 账号监控、开机启动或本机日志。

```powershell
& .\build-shareable.ps1
```

分享包不是纯单文件，因为可审查的 JS 词库需要与 EXE 放在同一目录；ZIP 已把运行文件、使用说明、校验清单和第三方说明放在一起。用户无需安装 Python、Node.js、Go 或开发环境。

## 简体中文外部扩展

当前 0.4.0 沿用 0.3.1 已实测的高性能 DOM 运行时，并增加独立便携应用。Antigravity 2.11.0 实际会忽略 Chromium `--load-extension`，因此主要路径通过应用已有的 DevTools 调试端口注入；`--load-extension` 只保留为兼容回退。整个过程不修改 `resources\app.asar`、`dist\preload.js`、登录态、会话、项目文件或网络请求。

扩展现在覆盖 2.11.0 Settings 的 General、Application、Appearance、Models、Customizations、Browser、AICode、Conversations、Shortcuts、Feedback、Account 等页面，并保护虚拟列表中的用户对话标题、消息、Markdown、代码、终端、编辑器和输入值。React 动态刷新仍使用 80 ms 尾部防抖与 300 ms 最大等待，同时支持权限请求、额度、时间、数量、模型和 breakdown 等动态文本。

扩展会翻译侧边栏、设置标题、策略值、按钮和指定长句说明；输入框内容、可编辑区域、对话消息、Markdown、代码块、终端和编辑器内容默认保护。React 动态刷新使用 80 ms 尾部防抖，并设置 300 ms 最大等待。

## 安装与启动

桌面只创建一个 `Antigravity 启动器.lnk`，指向正式恢复 EXE。中文启用、英文恢复和官方原版入口只保留在开始菜单，避免桌面出现多个容易混淆的图标。

构建输出目录：`releases/current/`；安装后的稳定运行目录：`%LOCALAPPDATA%\Antigravity\launcher\`。构建运行 `build.ps1`（会先安全停止本项目旧监控器），安装运行 `install.ps1`。

首次安装或升级：

```powershell
Set-Location 'D:\AICode\工具开发\projects\antigravity-recovery-launcher'
& .\build.ps1
& .\install.ps1
```

安装后：

- `Antigravity 中文版`：清除英文模式标记，启动带中文扩展和现有专用代理的 Antigravity。
- `Antigravity 启动器`：直接启动恢复入口；默认保留上一次的中文/英文选择。
- `Antigravity 英文恢复`：设置可逆英文模式标记，启动不加载扩展的原始英文 UI，但仍保留现有专用代理恢复流程。
- `Antigravity 原版`：直接启动官方程序，不经过本项目的代理恢复流程。

`install.ps1` 不携带或读取本项目中的密钥。它会从 Google 官方更新清单下载当前 Windows `agy`，校验官方 SHA-512 后安装到 `%LOCALAPPDATA%\Antigravity\launcher\tools\agy\agy.exe`。Google 登录由系统 keyring 复用，代理订阅继续由用户自己的代理客户端管理。

## 插件、个人配置和密钥在哪里

- 中文插件源码：`src/localization-extension/`。
- 安装后的中文插件：`%LOCALAPPDATA%\Antigravity\launcher\localization-extension\`。
- 通用规则源码：`src/Antigravity-ProxySupervisor.ps1`。
- 本机生成的专用代理配置、候选冷却和脱敏日志：`%LOCALAPPDATA%\Antigravity\private-proxy\`。
- Clash Verge 本地订阅缓存：`%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\`。
- Mihomo Party 本地订阅缓存：`%APPDATA%\mihomo-party\`。
- Google 登录态：系统 keyring／Antigravity 官方登录体系，本项目不导出。
- 用户的集中秘密真源：`D:\AICode\AI\secrets\` 与 Windows 凭据管理器；本项目不复制其中内容。需要长期配置时，只在 `D:\AICode\AI\private-config\` 保存引用。

安装不会强制关闭已经打开的 Antigravity；第一次点击中文/英文入口时才应用对应运行模式。这样不会因为升级扩展打断正在编辑的对话或文件。

英文恢复不会删除扩展文件或 Antigravity 用户数据；再次点击 `Antigravity 中文版` 即可恢复。需要完全移除时，只需删除本项目安装产生的 `localization-extension`、两个语言切换脚本和语言快捷方式；不要删除 `%APPDATA%\Antigravity` 或 `%USERPROFILE%\.gemini\antigravity`。

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

- `17897` 从 Clash Verge 和 Clash Party 的本地订阅缓存提取候选直连；候选必须实时通过 Google、OAuth 与 US 出口预检。本工具不修改全局节点或代理设置，也不依赖 Clash Party 常驻。
- Clash 界面模式与生成 YAML 可能短暂不一致；诊断日常模式时以界面当前选中状态和运行证据为准，不能只读 `clash-verge.yaml`。
- 当前成功组合是本机当前账号 + 当前时间 + 已验证洛杉矶出口；节点未来更新后仍需以真实对话验收。
- 自动候选只有通过 Google、OAuth 和 US 出口预检后才会接管；首次真实模型资格仍需用户正常发送消息，以新的 `ResponseID` 为成功证据。若候选返回地区 400，监控器会将它移出本轮。
- 动态注入依赖 Antigravity 当前仍提供 DevTools 调试目标；若未来版本关闭该入口或更换本地 UI 协议，程序仍可按英文原版启动，但汉化不会生效。

## 源码与发布

- 源码真源：本目录 Git 仓库的 `src/`。
- 发布包：`releases/`；大型二进制不进 Git。
- 桌面快捷方式和开机监控使用 `%LOCALAPPDATA%\Antigravity\launcher\` 中的运行副本，不依赖源码目录是否移动。
- 中间产物：`.work/`、`build/`、`dist/`，可重建、可删除。
- 完整公开安装 ZIP：运行 `build-release.ps1`，输出到 `releases/public/`；ZIP 不包含订阅、节点、账号、日志、用户数据或 `agy.exe`。

