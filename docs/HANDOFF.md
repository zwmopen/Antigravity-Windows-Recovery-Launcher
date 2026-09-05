# 开发交接

> 这是项目唯一权威交接文档。新信息直接并入本文档，Git 保存历史。  
> 对应版本：1.0.1  
> 最后核对：2026-09-04。

## 项目定位和范围

为 Cockpit 多账号切换后的 Antigravity 自动检查专用代理、清除黑屏实例、恢复启动，并提供可逆的外部简体中文 UI 扩展。

## 唯一真源与禁止覆盖的资产

- 源码：`src/`。
- 开发交接：本文档。
- 版本：`VERSION`。
- 禁止覆盖：待按项目补充。

## 架构、模块和启动方式

- `Antigravity-Recovery-Launcher.exe`：稳定桌面入口和克制玻璃中文实时状态窗口；从本次新增的脱敏事件显示独立代理、候选数量、Google/OAuth、出口、真实模型、中文注入和应用就绪状态，再调用监督器完成恢复。若后台恢复已先占用监督器，前台会等待并接管其结果。
- `Antigravity-AccountWatcher.exe`：监控 Cockpit 当前账号、无代理 `--reuse-window` 实例，以及 17897 到 Google/OAuth 的持续健康；0.5.0 连续 3 次网络失败或新地区 400 才触发有界后台恢复。
- `Antigravity-ProxySupervisor.ps1`：监督器 2.6.0 从 Clash Verge 与 Mihomo Party 订阅索引定位仍有效的本地缓存，发现跨来源日本/美国候选，维护失败冷却，配置/启动 17897，并以官方 `agy` 最小真实生成作为桌面启动前门禁；新增脱敏候选数量、来源统计和失败状态事件供中文启动器显示。
- `localization-extension/translation-core.js`：可审查的词库和纯替换核心；完整句子、UI 短词、权限/额度/时间/数量/模型动态规则分层。
- `localization-extension/content.js`：本地 UI DOM 观察、属性翻译和防抖调度；保护虚拟列表对话标题及用户内容。
- `Set-AntigravityLocalization.ps1` + 两个 `.cmd`：中文启用/英文恢复的可逆开关。
- `Antigravity-Chinese-Assistant.exe`：可对外分享的独立便携界面，只负责查找官方客户端、动态汉化、英文恢复和桌面入口，不依赖本机代理恢复链。
- `build-shareable.ps1`：构建独立 Windows x64 ZIP、校验清单和用户说明。
- `build.ps1` 构建本地运行组件；公开 ZIP 根目录的 `Install.cmd` 是普通用户双击安装入口，内部调用 `install.ps1` 备份并安装桌面入口和 HKCU Run 监控器。
- `installer/Antigravity-Recovery-Setup.iss` + `build-installer.ps1`：远端 CI 构建中文单文件 Setup.exe；支持粘贴/浏览安装路径、每用户安装、升级复用目录、完成页启动/打开目录和标准卸载。
- `uninstall.ps1`：按安装目录校验并停止本项目进程，移除本项目快捷方式和 HKCU Run；保留所有账号、会话、项目、订阅与 private-proxy 数据。

## 数据、同步、迁移、备份和恢复

运行数据留在 `%LOCALAPPDATA%\Antigravity`；源码和发布物在本项目。安装不会迁移或清理 Antigravity 用户数据。

## 配置、隐私、密钥和权限边界

不保存账号凭据或节点密钥。不会修改 Google 付款资料、账号地区、全局代理或外部账号状态。

## 版本、构建、发布和回滚

- 当前源码恢复链版本：0.9.1；监督器 2.6.0、AccountWatcher 0.5.2、启动器 0.9.1。安装目录在本轮本地构建/安装完成前仍可能是旧版本，不能据此判断源码已经生效。
- 独立分享版仍为 0.4.0，且不包含监控组件、节点池或代理配置。
- 构建：Windows .NET Framework 4.0 C# 编译器生成两个 winexe，脚本执行语法检查。
- 发布：本地只更新 `releases/current` 并安装验证；远端 CI 生成 Setup/ZIP 并上传 Release。Setup 可安装到用户选择目录，ZIP 默认复制到 `%LOCALAPPDATA%\Antigravity\launcher`。桌面快捷方式和开机监控始终指向稳定运行目录，不依赖源码目录路径。
- `build-installer.ps1` 优先使用现有 ISCC；缺失时从 Inno Setup 官方 GitHub Release 获取 7.1.0 x64 安装器，校验固定 SHA-256 `0362A383ED217D4C4239B5933866DD96D3EB2102737DA92F80F6057A4B40DF2F` 和有效数字签名，再装入 `.work/tools` 构建。
- 中文扩展随发布包复制到 `%LOCALAPPDATA%\Antigravity\launcher\localization-extension`；启动器默认追加 `--load-extension`，英文恢复标记存在时跳过该参数。
- 可分享版输出到 `releases/shareable/Antigravity-Chinese-Assistant-<version>-windows-x64.zip`；只包含中文助手、Loader、词库、使用说明、第三方说明和 SHA-256 清单，不包含监督器、账号监控器或任何代理配置。
- 安装会创建一次性的 `localization-extension-pending.flag`，防止升级时监控器立即重启用户正在使用的窗口；显式中文/英文启动成功后由监督器清除。
- 公开 ZIP 根目录包含 `Install.cmd`；它只切换到自身目录并以 Bypass 策略调用同目录 `install.ps1`，失败时保留窗口和退出码，核心安装逻辑仍保持模块化、可审计。
- 桌面与用户开始菜单均维护 `Antigravity 启动器.lnk`，启动器每次运行会校验并在变更前备份；安装更新时只停止本项目旧监控器并替换稳定运行副本。
- 回滚：恢复 `shortcut-backups` 中的快捷方式，删除 HKCU Run 的 `AntigravityAccountWatcher` 值并停止本项目监控器；不删除用户数据。

## 测试和当前验收

- 2026-09-05 01:46–01:51：在不切换账号、不重启客户端、不改变 7897 的前提下，通过稳定目录安装链的 `agy.exe` 经 17897 执行了一次官方最小真实生成。请求超过 90 秒未形成结构化结果，随后仅结束了该次 `agy.exe` 探针进程（PID 33520）；探针日志保留 1 个 `streamGenerateContent`/`ResponseID` 传输标记和 HTTP 200 痕迹，但没有 `status=SUCCESS`、精确 `response=OK` 或 `finishReason`，也没有新的地区限制 400。该次验收判定为未通过，当前新错误类型归为 `model_transport`/流完成卡住，不能把 ResponseID 传输标记冒充模型成功。结束探针后 Antigravity、language server、Watcher、17897 与 7897 均保持原运行链；实时 `fixed-upstream.json` 为独立 JP 上游，不能沿用旧描述推断其正在转发 7897。
- 2026-09-04 22:15–22:20：v1.0.0 完整实机运行与健康自检全部通过。
  - 自动化测试：全部 7 套测试（故障转移 31 候选策略、AccountWatcher 14 项策略、候选容量公平性、监督器状态契约、启动器 UI、安装器契约、中文扩展）100% PASS。
  - 实时专线链路：17897 探针真实验证 Google generate_204 返回 204 OK，generativelanguage 与 oauth2 端点均通畅可达（404），出口 IP 实测为美国洛杉矶纯正专线（`172.96.161.31`，ReliableSite.Net LLC）。
  - 后台静默守卫：`Antigravity-AccountWatcher`（PID 30044）正常常驻并每 20 秒轮询守护，开机启动项 `HKCU:\Software\Microsoft\Windows\CurrentVersion\Run` 正确挂载；
  - 编辑器与代理：`verge-mihomo.exe`（PID 32832）稳定监听 17897，`language_server.exe` 建立 11 条健康长连接，Antigravity 主进程活跃；
  - 自愈体系闭环：坏节点强制加入冷却隔离、Mihomo 重启清空僵死 TCP 连接池、热启动双选胶囊与一键救急重启机制实机全闭环。
- 2026-09-04 17:44：1.0.1 热启动双选胶囊卡片（方案 2 + 极简人话 A 款）全链路实机验收通过。双击桌面启动器在后台运行时弹出 480×146 原生 DWM 拟态胶囊卡片，主按钮 `🚀 直接打开 (3s)`，辅助按钮 `⚡ 重启修复`。实测 3 秒倒计时自动平滑切入代码窗口，穿透 Win32 最小化窗口限制恢复并置顶最前台（`ActivateExistingAntigravity` 成功率 100%）。单实例 Mutex 提前拦截，杜绝多次重复弹窗，桌面唯一入口为 `Antigravity 启动器.lnk`。
- 2026-09-02 16:38–16:44：0.9.0 新版源码构建并安装到稳定目录；桌面快捷方式双击与后台恢复竞态实测通过。前台遇到 `supervisor_run_busy` 后保持状态窗口等待，后台真实模型门禁完成后前台自动接管并正常退出，无“启动未通过”误报。最终状态为 `ready`、候选池 32 条、JP 出口、17897、语言服务 8 条专线连接；7897 仍由原进程监听。
- 2026-09-02：竞态复测中首个候选出现真实模型地区失败后被淘汰，下一条日本候选通过两次官方 `agy` 最小真实生成并启动 Antigravity；证明候选轮换与真实模型门禁均生效。
- 2026-09-02：0.9.0 安装包验收通过。现有 Setup.exe 大小 2,158,174 字节、SHA-256 `C6710685927B08D618ABC95DE7B5C89038F2EE8B6DFF055B9AA79F3874D16D33`；现有 ZIP 大小 84,512 字节、SHA-256 `2D8D0CEDD76D303DD095DB8E98C481B7CB01EEC7D1D2FA25965C9BB80B85ED07`；ZIP 21 个条目，不含 `agy.exe`、日志、Token 或订阅配置。
- 2026-09-02：0.9.0 回归测试全部通过：故障转移 32 候选、AccountWatcher 14 项、启动器中文状态、安装器契约、中文扩展、分享版隔离和 PowerShell 语法检查。
- 2026-09-02 13:43–13:44：0.8.0 中文状态窗口首次实机验收。Computer Use 读取到窗口标题、全部中文步骤和无裁切布局；本次事件实际显示 17 条候选、独立 17897、Google/OAuth 连通、US 出口和真实模型 OK。随后 Antigravity PID 45172 ready，language server PID 18228 建立 10 条 17897 连接，中文 Loader 成功；7897 保持 PID 8240。用户随后指定使用个人开发系统中的“克制玻璃”视觉真源，并增加自绘百分比进度条，需再次完成视觉和发布包验收。
- 2026-09-02 13:52–14:06：克制玻璃最终视觉复验通过，圆角黑边/锯齿已消除，动态进度显示正常；完整启动再次发现 17 条候选，Google/OAuth、US 出口和真实模型 OK 通过，Antigravity PID 23784 ready，language server PID 15048 建立 8 条 17897 连接，中文注入成功，7897 仍为 PID 8240。加入阶段内感知进度与 `✅` 成功符号后全部策略/UI/中文/隔离测试再次通过；最终 0.8.0 ZIP 为 75,616 字节，SHA-256 `B4294FA3545B8431605CECD79A42A1C44AE1EB06721A91F38EFEFA0D6CE0C77A`。
- 2026-09-02：发布前按用户反馈增加感知性能动画。百分比从 1% 快速起步，在每个真实阶段的安全上限内持续微增；只有候选发现、代理、网络、出口、模型、应用和 Loader 的新事件才能解锁后续区间，最终成功事件才允许 100%。
- 2026-09-02：成功步骤的视觉符号统一为 `✅` 并保留完整中文说明；进行中和等待继续使用 `●`/`○`，保证状态可快速扫读且不只依赖颜色。
- 2026-09-02：0.8.0 首轮 GitHub CI 的 UI 测试在 Windows PowerShell 5.1 解析中文字符串时失败；本机功能和构建通过，根因是新增 `launcher-ui.test.ps1` 缺少 UTF-8 BOM。测试脚本固定为 UTF-8 BOM，避免把编码失败误判为产品逻辑失败。
- 2026-09-02：修复编码后 GitHub CI `33597134492` 全部通过。从公开 v0.8.0 Release 重新下载 ZIP，SHA-256 与发布清单一致，19 个文件，不含 `agy.exe` 或日志；通过公开包 `Install.cmd` 安装成功，桌面唯一入口目标正确，已安装启动器 FileVersion 为 `0.8.0.0`。
- 2026-09-02 12:25–12:41：官方 `agy 1.1.24` 经官方 SHA-512 校验安装。基础 Google/OAuth/US 预检出现多次假阳性，真实模型门禁准确识别地区 400 与断流；候选 `E64D…3C7` 连续两次最小真实生成返回 `OK`，桌面端随后以 17897 启动，language server 建立专用连接，7897 保持原 PID 与规则模式。
- 2026-09-02：监督器 2.3.0 将真实生成门禁加入每个候选；LocationFailure 先复核活动候选，修复旧失败会话日志回放造成的误轮换。策略测试、Watcher 14 项策略测试、中文扩展测试、独立助手隔离测试和 Windows x64 构建全部通过。
- 2026-09-02：0.7.0 公开发布边界完成初审：仓库和历史未发现代理协议链接、订阅 Token、refresh token、client secret 或私钥；公开 ZIP 不包含 `agy.exe`、订阅缓存、生成配置、账号数据或日志。
- 2026-09-02：公开 ZIP 增加根目录双击安装入口 `Install.cmd` 后重新构建；AccountWatcher 14 项、17 候选故障转移、中文扩展和独立助手隔离测试全部通过。ZIP 共 19 个文件，包含 `Install.cmd`，不含 `agy.exe` 或日志；修复 Windows PowerShell 哈希和中文编码兼容问题后的 SHA-256 为 `F87528CE71849CF1AB32A7FFC2CE4DA4CF0CB29B528E533A80D6F3F4E175739D`。
- 2026-09-02：首次从公开 ZIP 真实运行 `Install.cmd` 发现系统 `powershell.exe` 不提供 `Get-FileHash`，安装在官方 `agy` 校验阶段退出 1。安装脚本随后改用 .NET SHA-512 实现，避免依赖 PowerShell 4+；必须重新构建并从公开 Release 复验双击路径后再收口。
- 2026-09-02：第二次公开 ZIP 双击验收通过哈希阶段后，在创建中文 `.lnk` 时触发 COM 路径扩展名错误；根因是 Windows PowerShell 将无 BOM UTF-8 脚本中的中文路径解码损坏。`install.ps1` 改为 UTF-8 BOM，`build-release.ps1` 增加 BOM 发布门禁。
- 2026-09-02 13:33–13:35：第三次从 GitHub Release 全新下载 ZIP，SHA-256 与 `F87528CE71849CF1AB32A7FFC2CE4DA4CF0CB29B528E533A80D6F3F4E175739D` 一致，19 个文件且不含 `agy.exe`/日志；Windows PowerShell 5.1 通过 `Install.cmd` 安装成功。桌面只有 `Antigravity 启动器.lnk`，目标为稳定安装目录；从该快捷方式启动后 17 候选发现、US 出口和官方 `agy` 真实生成门禁通过，Antigravity PID 30828 ready，language server PID 38964 建立 8 条 17897 连接，7897 仍为原 PID 8240。公开 CI `33595128036` 通过。

- 2026-09-02：连续真实请求再次出现 `FAILED_PRECONDITION 400: User location is not supported`，旧监督状态显示候选池仅 4 条且全部同源。安装 Clash Party 2.0.2 后逐卡更新 4 份有效订阅；一元机场订阅端点返回 HTTP 200 空内容，未导入。
- 2026-09-02：新增订阅的 6 条美国线路经隔离临时端口完成两轮 Google、OAuth 与 US 出口测试，6/6 通过。监督器 2.2.0 改为读取 Clash Verge 与 Clash Party 的全部本地订阅缓存，按完整节点定义去重、按订阅来源交叉排列，实机策略探测得到 17 个唯一美国候选，策略测试通过。
- 2026-09-02：0.9.1 源码策略与回归验证通过。当前索引和缓存发现 25 条有效候选（日本 12、美国 13）；过期缓存被排除，`subscription-report.json` 负责按来源输出脱敏统计。AccountWatcher 14 项、故障转移、启动器 UI、失败状态、候选容量、安装器契约、中文扩展和分享版隔离测试全部通过；尚未把本地源码安装到稳定目录，真实启动验收待下一步完成。
- 2026-09-02 17:50–17:55：本地旧 0.9.0 运行链真实失败。`supervisor-state.json` 为监督器 2.5.0、候选 32 条、23 条淘汰、剩余 9 条全部 `google_connectivity_failed`，17897 未监听；此后 Antigravity PID 31992 与 language server PID 31180 均不含 17897。该证据说明“窗口还在”不能代表代理已注入，必须以本次启动的端口、命令行和真实模型门禁验收。
- 2026-09-02 21:15–21:22：对照 Google 官方论坛同日地区误判报告后修正候选策略。旧策略把一次 `model_location` 永久淘汰并删除成功历史，与本机同一美国出口先 `OK`、紧接地区 400 的复现冲突。现改为美国优先、日本兜底；地区 400 冷却 20 分钟并保留历史，确定性配置/出口/非 OK 错误仍淘汰。旧状态先备份再迁移，恢复 38 条误淘汰记录。13 条美国候选均未连续两次通过；其中两条出现一次 `OK` 后紧接 400。第一个日本历史节点连续两次 `SUCCESS + OK`，随后 17897 ready、JP 出口、Antigravity PID 29460、language server PID 296 建立 8 条专用连接；7897 仍为 PID 8240。

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
- 2026-09-04 15:23–17:38：排查旧活跃节点（性价比机场 `us1.jiedian.stream` / 172.96.161.216），实测 Ping 285ms 且公网丢包率高达 50%，导致模型单次探针被拉长至 32s。
- 2026-09-04 17:37：用户新购入并导入【泡泡Dog】商业专线订阅（`RSVHslucZCQY.yaml`，45 个 Trojan 节点，到期 2026-10-04，88GB 配额）。监督器在 17:37:42 自动索引到 31 个全量候选（含泡泡Dog 16 个日美专线候选：8美8日）。
- 2026-09-04 19:54–19:55：性价比机场节点触发 `LocationFailure`（Google 地区风控断流），AccountWatcher 自动捕获并在后台拉起 Failover 自愈。因 `Get-OrderedCandidates` 的排序铁律优先选择已具有成功历史记录的节点（`VerifiedRank=0`），三毛机场的美国洛杉矶节点（`洛杉矶-1|联通优化`，`tj-us-1.aikunapp.com:6001`，IP `172.96.160.129`）率先通过 Google 204、US 归属与真实 Gemini 模型快速吐字门禁（`model_generation_fast_passed` 15.8s），无缝接管反重力 17897 端口（11 条专线连接），实现 0 人工干预全自动自愈。
- 2026-09-04 20:30：用户询问为何新购入的泡泡Dog未被优先选中，确认其根因是“VerifiedRank 历史信任分规则与最小中断原则”保护：老兵优先救火，网络一旦通畅即止损停止滥测，而非判定泡泡Dog不可用。已向用户明确：若需将泡泡Dog设为第一优先级，在 Clash Verge Rev 中将其设为当前激活配置即可（提升至 Priority 20）。

## 已知问题、技术债和风险

- Mihomo 路径和订阅缓存目录仍是本机值；当前默认策略为当前活动订阅中日本优先、美国兜底的候选，跨电脑安装前需自动发现 Clash 路径、订阅格式、账号和可用节点，不复制本机节点结论。
- 启动器按候选声明校验实际出口为 JP 或 US；若目标节点不可访问出口探针、出口不一致或真实模型不通过，会淘汰该候选并继续下一条。
- 真实模型验收优先使用 Computer Use 在明确授权下发送无工具、无文件修改的最小测试消息，再读取新日志判定；若平台不可用，则由用户发送。不得改用 CDP/本地接口伪造模型验收。
- `--load-extension` 是 Chromium/Electron 版本兼容边界；扩展若未加载，优先检查主进程命令行、`localization-extension_enabled` 日志和本地 UI协议，不要修改 `app.asar` 兜底。
- AccountWatcher 会常驻以处理真实切号和运行时代理绕过，但 Loader 与恢复启动器在完成后退出。监控器不得把普通 `accounts.json` 写入当作恢复条件；若日志出现同账号写入后的 `repair_started`，说明仍在运行旧版。
- 0.4.1 安装时没有强制重启已经打开的 Antigravity，因此当时运行窗口仍保留 0.3.1 汉化 marker；用户下次主动点击“Antigravity 中文版”时才应用 0.4.0 词库。这是“不打断当前工作”的预期行为，不是 watcher 修复失败。
- 自动候选的 Google/OAuth/US 预检只能证明链路候选可接管，不能证明 Google 模型资格；候选首次被真实使用后必须以新 `ResponseID` 验收，若产生新地区 400，0.5.1 会隔离并轮换。
- 监督器运行时的快捷方式自检偶发 `COMException`，但 2026-08-30 实际桌面与开始菜单快捷方式目标、工作目录和图标均已人工读取验证正确，且桌面双击完整启动通过。该非致命诊断噪声后续可改为逐快捷方式重试；不得因此覆盖或删除用户其他 Antigravity 快捷方式。

## 当前状态和下一步

- 2026-09-06：攻克 Cockpit Tools 原生自动切号在 Antigravity 2.12.x 环境下超时（APP_PATH_NOT_FOUND）与配额轮询盲区（10 分钟超长缓存）问题。
  - 核心架构创新：在启动器工具链内扩展 `antigravity_smart_switch.py`、`Invoke-AntigravitySmartSwitch.ps1` 与 `Antigravity-QuickSwitch.cmd`。
  - 注入“小老虎”专属切号规则：
    1. 触发阈值：有效额度 <= 5% 立即触发切号；
    2. 门禁一票否决：周额度耗尽 (<=5%) 或 5小时额度耗尽 (<=5%) 直接淘汰（周额度耗尽则整号瘫痪）；
    3. 5小时满血优先：>=95% 满血账号处于 Tier 1 随时可战梯队；
    4. 周恢复时间紧迫度优先：按周重置倒计时升序（快要到期重置者优先消化存量，1~2天 >> 5~6天）；
    5. 综合加权评分：在满额前提下，优先选择“周重置即将到来”且“周额度充沛”的账号。
  - 全流程闭环：向主窗口发送 Win32 `WM_CLOSE` 优雅退出（留出 3 秒保存并释放凭据锁）➔ 智能计算小老虎分选出最优健康号 ➔ 通过 WebSocket (`ws://127.0.0.1:19528`) 驱动 Cockpit 静默写入 `state.vscdb` 与系统凭据（Cockpit 配置 `"antigravity_launch_on_switch": false` 消除裸奔拉起冲突）➔ 唤醒桌面智能启动器（17897 专线代理 + 模型自愈 + 汉化 + 极速置顶）。
  - 桌面建立快捷方式 `Antigravity 一键切号.lnk`，实机验证 7 账号额度感知与小老虎优选算法 100% PASS。
- 2026-09-05 现场复核：三毛机场洛杉矶节点（IP 172.96.160.129）平稳运行中，17897 专线连接与 Gemini 握手正常；多订阅发现机制已成功将【泡泡Dog】45 节点纳管，全池候选扩展至 31 个。0.9.1/1.0.0 维护与交付状态持续受控。
- 状态：反重力专属代理自愈与多订阅容灾实测通过；智能切号与平滑启动工具链实测通过；新订阅泡泡Dog 已就绪，三毛机场洛杉矶节点为当前主承载。
- 私有仓库：`https://github.com/zwmopen/antigravity-windows-recovery-launcher-private`。
- 公开仓库：`https://github.com/zwmopen/Antigravity-Windows-Recovery-Launcher`；当前稳定 Release：`v0.9.0`，本轮目标为 `v0.9.1`。
- 下一步：若用户需体验泡泡Dog 专线，可在 Clash Verge Rev 中点击激活【泡泡Dog】；继续按计划维护本地恢复启动器与发布链路。
- 下一位维护者先读：`README.md` 和 `docs/DESIGN.md`。
- 禁止：删除登录态/会话、伪造账号地区、修改全局 7897、刷新全部订阅、改变 Clash 日常规则模式、修改 `app.asar`，或用 Google 204 冒充模型成功。

## 维护规则

架构、数据源、目录、持久化、发布流程、重要业务规则或已知风险变化时，必须同步更新本文档。

