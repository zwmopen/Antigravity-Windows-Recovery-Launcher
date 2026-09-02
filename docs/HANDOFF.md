# 开发交接

> 这是项目唯一权威交接文档。新信息直接并入本文档，Git 保存历史。  
> 对应版本：0.7.0
> 最后核对：2026-09-02。

## 项目定位和范围

为 Cockpit 多账号切换后的 Antigravity 自动检查专用代理、清除黑屏实例、恢复启动，并提供可逆的外部简体中文 UI 扩展。

## 唯一真源与禁止覆盖的资产

- 源码：`src/`。
- 开发交接：本文档。
- 版本：`VERSION`。
- 禁止覆盖：待按项目补充。

## 架构、模块和启动方式

- `Antigravity-Recovery-Launcher.exe`：稳定桌面入口、进度窗口、调用监督器。
- `Antigravity-AccountWatcher.exe`：监控 Cockpit 当前账号、无代理 `--reuse-window` 实例，以及 17897 到 Google/OAuth 的持续健康；0.5.0 连续 3 次网络失败或新地区 400 才触发有界后台恢复。
- `Antigravity-ProxySupervisor.ps1`：监督器 2.3.0 从 Clash Verge 与 Mihomo Party 本地缓存发现跨来源美国候选，维护失败冷却，配置/启动 17897，并以官方 `agy` 最小真实生成作为桌面启动前门禁。
- `localization-extension/translation-core.js`：可审查的词库和纯替换核心；完整句子、UI 短词、权限/额度/时间/数量/模型动态规则分层。
- `localization-extension/content.js`：本地 UI DOM 观察、属性翻译和防抖调度；保护虚拟列表对话标题及用户内容。
- `Set-AntigravityLocalization.ps1` + 两个 `.cmd`：中文启用/英文恢复的可逆开关。
- `Antigravity-Chinese-Assistant.exe`：可对外分享的独立便携界面，只负责查找官方客户端、动态汉化、英文恢复和桌面入口，不依赖本机代理恢复链。
- `build-shareable.ps1`：构建独立 Windows x64 ZIP、校验清单和用户说明。
- `build.ps1` 构建；公开 ZIP 根目录的 `Install.cmd` 是普通用户双击安装入口，内部调用 `install.ps1` 备份并安装桌面入口和 HKCU Run 监控器。

## 数据、同步、迁移、备份和恢复

运行数据留在 `%LOCALAPPDATA%\Antigravity`；源码和发布物在本项目。安装不会迁移或清理 Antigravity 用户数据。

## 配置、隐私、密钥和权限边界

不保存账号凭据或节点密钥。不会修改 Google 付款资料、账号地区、全局代理或外部账号状态。

## 版本、构建、发布和回滚

- 当前本机恢复链版本：0.7.0；监督器 2.3.0、AccountWatcher 0.5.2。
- 独立分享版仍为 0.4.0，且不包含监控组件、节点池或代理配置。
- 构建：Windows .NET Framework 4.0 C# 编译器生成两个 winexe，脚本执行语法检查。
- 发布：`releases/current`；安装时复制到 `%LOCALAPPDATA%\Antigravity\launcher`，桌面快捷方式和开机监控指向该稳定运行目录，不依赖源码目录路径。
- 中文扩展随发布包复制到 `%LOCALAPPDATA%\Antigravity\launcher\localization-extension`；启动器默认追加 `--load-extension`，英文恢复标记存在时跳过该参数。
- 可分享版输出到 `releases/shareable/Antigravity-Chinese-Assistant-<version>-windows-x64.zip`；只包含中文助手、Loader、词库、使用说明、第三方说明和 SHA-256 清单，不包含监督器、账号监控器或任何代理配置。
- 安装会创建一次性的 `localization-extension-pending.flag`，防止升级时监控器立即重启用户正在使用的窗口；显式中文/英文启动成功后由监督器清除。
- 公开 ZIP 根目录包含 `Install.cmd`；它只切换到自身目录并以 Bypass 策略调用同目录 `install.ps1`，失败时保留窗口和退出码，核心安装逻辑仍保持模块化、可审计。
- 桌面与用户开始菜单均维护 `Antigravity.lnk`，启动器每次运行会校验并在变更前备份；安装更新时只停止本项目旧监控器并替换稳定运行副本。
- 回滚：恢复 `shortcut-backups` 中的快捷方式，删除 HKCU Run 的 `AntigravityAccountWatcher` 值并停止本项目监控器；不删除用户数据。

## 测试和当前验收

- 2026-09-02 12:25–12:41：官方 `agy 1.1.24` 经官方 SHA-512 校验安装。基础 Google/OAuth/US 预检出现多次假阳性，真实模型门禁准确识别地区 400 与断流；候选 `E64D…3C7` 连续两次最小真实生成返回 `OK`，桌面端随后以 17897 启动，language server 建立专用连接，7897 保持原 PID 与规则模式。
- 2026-09-02：监督器 2.3.0 将真实生成门禁加入每个候选；LocationFailure 先复核活动候选，修复旧失败会话日志回放造成的误轮换。策略测试、Watcher 14 项策略测试、中文扩展测试、独立助手隔离测试和 Windows x64 构建全部通过。
- 2026-09-02：0.7.0 公开发布边界完成初审：仓库和历史未发现代理协议链接、订阅 Token、refresh token、client secret 或私钥；公开 ZIP 不包含 `agy.exe`、订阅缓存、生成配置、账号数据或日志。
- 2026-09-02：公开 ZIP 增加根目录双击安装入口 `Install.cmd` 后重新构建；AccountWatcher 14 项、17 候选故障转移、中文扩展和独立助手隔离测试全部通过。ZIP 共 19 个文件，包含 `Install.cmd`，不含 `agy.exe` 或日志；修复 Windows PowerShell 哈希和中文编码兼容问题后的 SHA-256 为 `F87528CE71849CF1AB32A7FFC2CE4DA4CF0CB29B528E533A80D6F3F4E175739D`。
- 2026-09-02：首次从公开 ZIP 真实运行 `Install.cmd` 发现系统 `powershell.exe` 不提供 `Get-FileHash`，安装在官方 `agy` 校验阶段退出 1。安装脚本随后改用 .NET SHA-512 实现，避免依赖 PowerShell 4+；必须重新构建并从公开 Release 复验双击路径后再收口。
- 2026-09-02：第二次公开 ZIP 双击验收通过哈希阶段后，在创建中文 `.lnk` 时触发 COM 路径扩展名错误；根因是 Windows PowerShell 将无 BOM UTF-8 脚本中的中文路径解码损坏。`install.ps1` 改为 UTF-8 BOM，`build-release.ps1` 增加 BOM 发布门禁。
- 2026-09-02 13:33–13:35：第三次从 GitHub Release 全新下载 ZIP，SHA-256 与 `F87528CE71849CF1AB32A7FFC2CE4DA4CF0CB29B528E533A80D6F3F4E175739D` 一致，19 个文件且不含 `agy.exe`/日志；Windows PowerShell 5.1 通过 `Install.cmd` 安装成功。桌面只有 `Antigravity 启动器.lnk`，目标为稳定安装目录；从该快捷方式启动后 17 候选发现、US 出口和官方 `agy` 真实生成门禁通过，Antigravity PID 30828 ready，language server PID 38964 建立 8 条 17897 连接，7897 仍为原 PID 8240。公开 CI `33595128036` 通过。

- 2026-09-02：连续真实请求再次出现 `FAILED_PRECONDITION 400: User location is not supported`，旧监督状态显示候选池仅 4 条且全部同源。安装 Clash Party 2.0.2 后逐卡更新 4 份有效订阅；一元机场订阅端点返回 HTTP 200 空内容，未导入。
- 2026-09-02：新增订阅的 6 条美国线路经隔离临时端口完成两轮 Google、OAuth 与 US 出口测试，6/6 通过。监督器 2.2.0 改为读取 Clash Verge 与 Clash Party 的全部本地订阅缓存，按完整节点定义去重、按订阅来源交叉排列，实机策略探测得到 17 个唯一美国候选，策略测试通过。

- 2026-08-29 20:40：正式 EXE 退出码 0；唯一主进程 PID 29972 带 `17897`；language server PID 32168 到专用端口有 8 条连接；状态为 ready。
- 2026-08-29 20:53：`17897` 已改为转发现有全局 `7897`，出口从美国变为日本；监督器 1.6.0，主进程 PID 26728，language server PID 39544，有 8 条连接。
- 已复现并自动修复 Cockpit `--reuse-window` 顶掉正确实例导致的黑屏。
- 2026-08-29：移除基于历史语言服务日志的地区 400 强制重启。地区 400 属于 Google 账号/资格层结果，不能用重启同一上游修复；启动器只依据当前进程、配置和连通性状态做修复。
- 2026-08-29 21:11：源码语法检查、构建和安装通过；桌面与开始菜单均指向正式 EXE。连续两次启动均复用同一个 17897（无新增历史 400 重启），第二次状态为 ready，主进程 PID 8864、language server PID 7480、专用端口连接 7 条。
- 2026-08-29：修复账号监控器把实际启动器误认成未运行的旧进程名，避免恢复窗口期间重复拉起启动器。
- 2026-08-29：专用 17897 改为从当前 Clash 订阅缓存提取美国2 gemini，绕过全局 7897；找不到目标节点时不启动错误代理。
- 2026-08-29：监督器 1.9.0 增加通过 17897 的实际出口国家校验，必须为 US；仅 Google 204/Generative Language 404 不再足以判定代理链完整。
- 2026-08-29：账号监控器改为对 Cockpit 账号文件变化做防抖修复，覆盖快速 A→B→A 切换；修复失败不再写入已处理状态，而是自动重试；同时存在合规与不合规主进程时仍会触发修复。
- 2026-08-29：构建脚本会在编译前按绝对路径停止本项目旧账号监控器，避免旧监控器锁住待覆盖的 EXE。
- 真实模型回复仍是独立验收层；账号地区 400 不能由本地 ready 代替。
- 2026-08-30：切回此前真实成功的大号后，US2 仍返回地区 400；按历史成功证据将本机专用目标切换为 US1。仅变更 `17897`，不变更全局 `7897`。
- 2026-08-30：用户确认账号长期使用地区为日本；监督器 1.10.1 改为只从当前有效订阅自动选择日本节点、为当前 IPv6 日本专线启用 IPv6 并校验 JP 出口，修复当前订阅没有 US1 导致桌面入口无法启动的问题。当前 `2x专线-日本-4 (IPv6)` 即使启用 IPv6 仍无法通过 Google 预检，因此未标记为可用；真实模型结果仍需新 `ResponseID` 验收。
- 2026-08-30：发现 Clash Verge 当前运行合并配置中已有新鲜的日本1/专线节点，而原始 profile YAML 只暴露 IPv6 节点。监督器改为优先读取 `clash-verge.yaml`，默认选择当前活动配置中的 `日本1|移动优化`，避免订阅更新后仍使用旧缓存。
- 2026-08-30：进一步确认当前 profile 实际包含新日本节点，但节点名未加 YAML 引号，旧正则只支持单引号。监督器 1.10.2 已兼容三种节点名格式。
- 2026-08-30 15:20–15:22：刷新订阅后，`美国洛杉矶-1|联通优化` 在专用 `17897` 上连续产生 12 个 `streamGenerateContent ResponseID`，无同期地区限制 400，用户确认 Antigravity 已回复。监督器 1.11.0 已固定该成功节点；全局 `7897` 经复验仍为 JP。
- 2026-08-30：用户确认 Clash 日常固定使用“规则模式”。诊断期间刷新全部订阅曾扰动 Clash 模式并影响其他网络会话；后续启动器和维护流程禁止自动刷新全部订阅、禁止切换规则/全局/直连、禁止修改日常节点。
- 2026-08-30：Computer Use 复验界面“规则”已高亮，Windows 系统代理仍为 `127.0.0.1:7897`，专用 `17897` 独立监听。与此同时 `clash-verge.yaml` 仍残留 `mode: global`，说明模式验收不能只依赖该生成文件。
- 2026-08-30：对比公开 `yuexps/Antigravity-Hans` `v0.4.0` 后没有直接替换其 Go 启动器或逐条正则扫描实现；保留当前 Loader、恢复入口和代理链，只吸收高价值 UI/Settings、权限、额度、时间、数量和模型文案，并改为合并正则。
- 2026-08-30：0.3.0 修复短词污染（`Settings / On / Model / Rules` 只在 UI 标签或属性上下文生效）、Settings 长句漏翻、动态 breakdown/额度/时间文案漏翻，以及侧边栏用户对话标题被改写的问题。
- 2026-08-30：真实进入 2.11.0 Settings 后发现旧观察器会对每次 React 更新重复遍历文本和元素树，渲染器内存升至约 4.6 GB 并使 CDP 读取超时；0.3.1 改为单次 TreeWalker、合并待处理根节点、缓存已翻译文本/属性值并防止重复安装 observer。
- 2026-08-30：0.3.1 真实进入 Settings 的 General、Application、Appearance、Models、Customizations、Browser、AICode、Conversations、Shortcuts、Feedback、Account 页面；进入后立即及等待 20 秒两次只读检查均通过，marker 为 0.3.1，混合污染为 0，对话标题未改写，渲染器保持响应且约 220–284 MB。
- 2026-08-30：0.4.0 新增独立可分享中文助手；静态隔离测试确认源码不包含 `17897`、Clash、AccountWatcher 或代理环境变量，首次 Windows x64 便携包构建通过。
- 2026-08-30：0.4.0 分享包实机验收通过：从发行目录启动的窗口标题、FileVersion 和 ProductVersion 均为 0.4.0；发行包 Loader 对当前 Antigravity 页面注入成功，marker 为 0.4.0，混合污染与对话标题污染均为 0。最终 ZIP 为 `Antigravity-Chinese-Assistant-0.4.0-windows-x64.zip`，SHA-256 `689975BFD5DAC4AE5FF2751FB12D0BC9A4DC8A2432060E1981FE61833FA1A905`，内部 8 个文件哈希全部复核一致。
- 2026-08-30：实时日志确认旧 AccountWatcher 在 `current_account_id` 未变化时，因 Cockpit 两次普通文件写入分别触发恢复启动器，造成两次非用户发起的重启。0.4.1 移除“任意文件写入即修复”，改为账号 ID 真实变化、单实例/修复中门禁、成功冷却和每类最多 3 次退避重试；策略测试 9 项通过。21:08 安装后，21:09 的同账号写入被记录为 `accounts_file_write_ignored`；随后连续观察 45 秒，Antigravity PID 36036 未变、新增 `repair_started` 为 0、Loader/恢复启动器均未常驻，17897 保持 3 条已建立连接。
- 2026-08-30 22:19–22:21：实时只读诊断确认 `7897` 连续正常返回 Google 204，而 `17897` 连续超时；专用 Mihomo 与 language server 本地连接均存在，应用日志为 Google OAuth `EOF`。根因层级是专用节点上游断流，不是本地端口、分流或账号地区 400。
- 2026-08-30：0.5.0 增加持续高可用链。AccountWatcher 每 20 秒检查 Google/OAuth，连续 3 次失败或新地区 400 后无窗口调用监督器；监督器从当前活动配置发现最多 6 条洛杉矶候选，失败节点冷却 20 分钟，成功后稳定 60 秒再检查。
- 2026-08-30 23:01–23:05：0.5.1 实机安装与桌面快捷方式完整启动通过。发现并修复三项恢复链缺陷：日志并发占用会中断流程、状态保存误读候选字段会假失败、Windows 进程树回收超过 5 秒会误报关闭失败。最终 `7897` 前后均为 PID 14660，系统代理仍为 `127.0.0.1:7897`；`17897` 为 PID 35108，US 出口，Antigravity PID 32192 与 language server PID 41956 建立 9 条专线连接。Computer Use 新建最小测试对话并得到 `OK`；23:05 日志产生两条新的 `streamGenerateContent ResponseID`，无同期地区限制 400。
- 2026-08-30 23:12–23:28：专用主候选断流，Watcher 连续 3 次失败后自动轮换；4 个候选当时均无法通过 Google/OAuth，监督器按安全策略停止 17897。发现 0.5.1 在三轮失败后永久停止重试、且手动启动仍受冷却限制。0.5.2 改为恢复轮次耗尽后每 5 分钟再做一轮有界恢复，用户主动双击启动器可优先对最后成功候选做一次冷却突破。23:25 手动恢复命中原成功候选，17897 PID 28848、US 出口、language server 9 条连接；7897 始终为 PID 14660。界面中失败请求重新执行后正常回复，23:27–23:28 连续产生 6 条新 `streamGenerateContent ResponseID`，无同期地区限制 400。

## 已知问题、技术债和风险

- Mihomo 路径和订阅缓存目录仍是本机值；当前默认策略为当前活动订阅中已真实验收的洛杉矶候选，跨电脑安装前需自动发现 Clash 路径、订阅格式、账号和可用节点，不复制本机节点结论。
- 启动器现在依赖 Cloudflare trace 的 `loc=US` 做出口一致性门禁；若目标节点不可访问该 trace 或出口不是 US，会安全停止启动。
- 真实模型验收优先使用 Computer Use 在明确授权下发送无工具、无文件修改的最小测试消息，再读取新日志判定；若平台不可用，则由用户发送。不得改用 CDP/本地接口伪造模型验收。
- `--load-extension` 是 Chromium/Electron 版本兼容边界；扩展若未加载，优先检查主进程命令行、`localization-extension_enabled` 日志和本地 UI 协议，不要修改 `app.asar` 兜底。
- AccountWatcher 会常驻以处理真实切号和运行时代理绕过，但 Loader 与恢复启动器在完成后退出。监控器不得把普通 `accounts.json` 写入当作恢复条件；若日志出现同账号写入后的 `repair_started`，说明仍在运行旧版。
- 0.4.1 安装时没有强制重启已经打开的 Antigravity，因此当时运行窗口仍保留 0.3.1 汉化 marker；用户下次主动点击“Antigravity 中文版”时才应用 0.4.0 词库。这是“不打断当前工作”的预期行为，不是 watcher 修复失败。
- 自动候选的 Google/OAuth/US 预检只能证明链路候选可接管，不能证明 Google 模型资格；候选首次被真实使用后必须以新 `ResponseID` 验收，若产生新地区 400，0.5.1 会隔离并轮换。
- 监督器运行时的快捷方式自检偶发 `COMException`，但 2026-08-30 实际桌面与开始菜单快捷方式目标、工作目录和图标均已人工读取验证正确，且桌面双击完整启动通过。该非致命诊断噪声后续可改为逐快捷方式重试；不得因此覆盖或删除用户其他 Antigravity 快捷方式。

## 当前状态和下一步

- 状态：0.7.0 已完成私有 Git 备份、公开仓库、MIT 许可证、Windows CI 和正式 Release；发布 ZIP 包含普通用户可双击的 `Install.cmd`。公开 ZIP 已重新下载并通过 Windows PowerShell 5.1 安装，SHA-256 一致，不含 `agy.exe`、日志或 Mihomo 生成配置；桌面只有一个主入口，真实模型门禁通过，17897 language server 连接正常且 7897 未变。
- 私有仓库：`https://github.com/zwmopen/antigravity-windows-recovery-launcher-private`。
- 公开仓库：`https://github.com/zwmopen/Antigravity-Windows-Recovery-Launcher`；Release：`v0.7.0`。
- 下一步：维护观察真实出口稳定性；若所有普通机房候选长期被拒绝，增加用户自有的干净 ISP/住宅出口适配，但不得把凭据或节点配置写入仓库。
- 下一位维护者先读：`README.md` 和 `docs/DESIGN.md`。
- 禁止：删除登录态/会话、伪造账号地区、修改全局 7897、刷新全部订阅、改变 Clash 日常规则模式、修改 `app.asar`，或用 Google 204 冒充模型成功。

## 维护规则

架构、数据源、目录、持久化、发布流程、重要业务规则或已知风险变化时，必须同步更新本文档。

