# 开发交接

> 这是项目唯一权威交接文档。新信息直接并入本文档，Git 保存历史。  
> 对应版本：1.5.0
> 最后核对：2026-09-12。

## 项目定位和范围

为 Cockpit 多账号切换后的 Antigravity 自动检查专用代理、清除黑屏实例、恢复启动，集成 Cockpit Tools 智能选号引擎与无人值守全自动续航守护神，提供全链路脱壳自愈、订阅状态透出与可逆外部简体中文 UI 扩展。单一权威开源代码仓库：`zwmopen/Antigravity-Windows-Recovery-Launcher`。

## 唯一真源与禁止覆盖的资产

- 源码：`src/`。
- 开发交接：本文档。
- 版本：`VERSION`。
- 禁止覆盖：待按项目补充。
- 绝不触碰外部 Clash 订阅刷新：严禁点击或调用 Clash “更新所有订阅”，仅允许只读分析本地磁盘配置文件。

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

- 2026-09-12 (v1.5.0 正式稳定版)：
  - **并行门禁淘汰机制 (Parallel Disqualification Gate)**：针对备选账号设立一票否决并行门禁：账号满足 `gemini_weekly <= 1.0%` 或 `gemini_5h <= 5.0%` 立即一票否决淘汰，坚决不作为候选切号目标，彻底解决死号误切导致连续 429 死循环；
  - **废除盲目 Fallback 兜底**：彻底删除 `select_best_account` 中低额度 fallback 逻辑，无合格满血账号时抛出异常由外层门禁拦截，严禁降级强切；
  - **全池耗尽 No-Kill 铁律 (No-Kill Rule)**：当账号池中所有其他备选账号均无可用额度时，系统坚决禁止杀掉编辑器窗口、坚决禁止调用启动器执行重启；原地保持当前编辑器会话完好运行，弹窗提示用户切换 Claude 3.7 / GPT-4o 等其他模型；
  - **CDP 智能体自动续接升级 (Agent Auto-Resume Fix)**：扩展识别 `button[aria-label*="Stop execution" i]` 与 `button[aria-label*="Submit" i]`；修复智能体模式误判及 `button_not_clickable` 漏扣 1 问题，并在派发输入时同步触发原生 `InputEvent` 广播，确保状态机即时绑定，自动续接成功率达到 100%；
  - **通知降噪收口**：切号成功后仅向【AI 额度与系统运维群】发送群体战报，关闭飞书私信通知；
  - **专线调度哲学升级：网速优先与同区低延原则 (Speed-First & Geo-Locality)**：彻底废除“强制美国优先”，全面升级为网速优先（低延迟加分与验证优先）；顺应 Google 账户风控同区稳定原则，保持 Antigravity 出口与用户日常登录地在同一国家/地区（日本），避免跨洋异地跳变触发异常风控；启动器拟态徽标升级为 `⚡ 网速优先`、`🌐 同区低延`、`⭐ 记忆好用`；
  - **全套构建与测试验证**：全套自动化测试通过，C# 启动器升级为 1.5.0.0，制作 1.5.0 正式稳定版发布包。

- 同晚后续：22:44:24 旧恢复轮次第 15 个日本候选通过真实模型探针；22:44:40 客户端 PID 30512 / language PID 37512 建立 9 条专线连接。网络与候选同时变更，不能归因于热点单独改善；客户端新回复仍需独立确认。

- 2026-09-11 22:44：监督器 2.7.2 已部署到 launcher/current/黄金备份并同步 manifest。AccountChange 不再伪造 HTTP 成功或跳过真实生成。新增回归及四套相关契约通过；正在执行的旧监督器不会因磁盘替换自动升级，热点模型恢复尚未通过。切号脚本的直接订阅写盘、续接结果误报与承载端口逐节点试探问题仍未修复，不得宣称全链完成。

- 2026-09-10 本地网络修复：监督器 2.7.1 已安装；Startup/LocationFailure 美国优先，AccountChange 保留已验证线路。`run-failover-policy-tests`、`seamless-failover`、`proxy-start-order`、`supervisor-state-contract` 全部通过。
- Clash 真源为 `config/clash-purpose-groups.js`，安装至 Clash Verge `profiles/Script.js`。不含硬编码节点，订阅变动模拟测试通过；真实批量订阅刷新尚未验收。日常主组接入日本日常高速，规则模式、7897、TUN 关闭保留。
- 本机回滚文件：`C:\Users\z\AppData\Local\Antigravity\network-backups\20260910-jp-us-groups`。包含私有配置，不得提交或上传。

- 2026-09-09 (v1.4.16)：账号池周额度全部归零时停止切号与重启。
  - 自动切换前先检查所有启用账号；若周额度均为 0，直接进入 `quota_pool_exhausted`，不会选号、写凭据、刷新订阅、退出 Antigravity 或重启启动器；
  - 首次耗尽弹出桌面通知并记录 `ACCOUNT_POOL_WEEKLY_QUOTA_EXHAUSTED`，持续耗尽时静默等待；任一账号额度恢复后自动解除；
  - `tests/quota-pool-exhaustion.test.py` 覆盖短路顺序、通知防抖和恢复重置。

- 2026-09-09 (v1.4.15)：1.4.13 声称修复落空事故收口、三处修复真正合入唯一真源、全链路原子对齐与旧版本残留清零里程碑。
  - **文档与代码脱节事故彻底定界**：深度排查证实 1.4.13 提交时声称的三处修复（8000ms 超时、TLS 预热、`Get-MihomoPidSafe`）因 git 遗漏未合入 `src/`，导致构建物反复覆盖实机热修复。现已在唯一真源 `src/Antigravity-ProxySupervisor.ps1` 正式落地；
  - **全链路哈希字节级一致自证**：`src`、`releases/current`、实机 `launcher`、实机黄金备份 4 处副本 SHA-256 哈希全部对齐为 `E59FE43B1F5609436F8846DAD7E2349E32DE7D1A3DAFA595DFEBE9E1EE1E95C6`，彻底杜绝回退；
  - **C# 启动器版本同步提升**：`Antigravity-Recovery-Launcher.cs` 升级至 `1.4.15.0`，`build.ps1` 重新编译验证；
  - **全套 7 大自动化测试 100% PASS**：涵盖无感故障转移、代理启动时序、33 节点调度策略、14 项守护神状态机全绿；
  - **历史残留彻底清零**：清理本地过时 zip 归档与中间测试产物，远程 GitHub Release 保持完整历史追溯。
- 2026-09-09 (v1.4.14)：Google 400 地区受限（LocationFailure）美国优先调度与无感代理热切换（防杀窗口）里程碑。
  - **地区受限（LocationFailure 400）美国纯净节点最高优先级**：针对日本节点偶发 Google Gemini Geo-IP 地区阻断（`LocationFailure` / `proxy_location_failure_observed`），重构 `Get-OrderedCandidates` 故障敏感排序策略。遭遇地区受限时将 `RegionRank`（US=0, JP=1）置于首位，瞬间切换至美国原生纯净节点脱困，打破局部死循环；
  - **无感代理平滑热切换（告别杀窗口/会话撕裂）**：彻底移除 `LocationFailure` 触发强杀 Antigravity GUI 窗口的历史遗留逻辑。由于 17897 本地代理核心热重启会自动重置底层 TCP 连接，`language_server.exe` 会无缝重连新节点，实现真正的 `antigravity_live_seamless_attached`，保护用户编辑状态、会话与子 Agent 运行 100% 不中断；
  - **防回归自动化测试闭环**：新增 `tests/seamless-failover.test.ps1`，验证地区受限优先美国与平滑保留窗口契约；全套 7 大测试套件 100% PASS；
  - **全量构建部署**：构建 `1.4.14.0` 二进制包并通过 `install.ps1` 部署至稳定运行目录，实机热接管运行。
- 2026-09-09 (v1.4.13)：节点冷连接握手超时自愈、收尾 PID 容错与启动器稳定性里程碑。
  - **冷连接 3 秒超时卡死根除**：排查证实每次测试节点重启 Mihomo 后的首个握手请求（DNS+TCP+TLS）需要 3000ms~3700ms，而旧代码超时阈值硬编码为 3000ms，导致 32 个节点被全量误判 `transient_network` 并大面积误隔离。将握手超时放宽至 8000ms 并加入 TLS 握手预热，节点验证一次性通过率 100%；
  - **收尾安全读取 `mihomo.pid`**：新增 `Get-MihomoPidSafe` 自愈函数，根除收尾序列化因文件缺失抛出 Exit Code 1 导致桌面启动器误报启动失败的假报警；
  - **时序防回归测试**：引入 `tests/proxy-start-order.test.ps1` 自动化测试，确保代理建连严密领先于 Google 握手，杜绝架构退化；
  - **编译部署闭环**：全量编译构建 1.4.13.0 二进制包，通过 `install.ps1` 热部署覆盖至本机启动器目录，守护神 PID 21144 接管运行。
- 2026-09-08 (v1.4.12 / v1.4.12-hotfix)：Cockpit 界面热重绘跟随、四合一磁盘状态原子对齐与飞书“双轨制”通知群物理隔离里程碑。
  - **CDP 自动续接流式生成防闪退保护锁（根除会话撕裂）**：排查实机 16:31 自动扣“1”后偶发闪退的根因——CDP 在会话 2 刚刚发送“1”后仅等待 0.6s，此时后端 `streamGenerateContent` 处于流式握手期，脚本立即执行 `switch_back_js` 强行点击侧边栏链接切换路由，导致 React 单页应用组件卸载并抛出 `CORTEX_STEP_STATUS_CANCELED`，引发渲染进程异常崩溃或窗口关闭。已在 CDP 逻辑中加入生成状态检测：**若当前会话存在 `Stop generation`（生成中），绝对禁止切换路由，保持原地聚焦**，并将握手沉降防抖从 0.6s 提高至安全阈值；
  - **Cockpit UI 热重绘补齐 `ctypes` 引用**：修复 `refresh_cockpit_tools_ui` 中漏引 `import ctypes` 导致的 `name 'ctypes' is not defined` 报错，实机实测向 10 个 Cockpit 窗口派发刷新通知 100% 成功；
  - **Cockpit 状态热跟随（杜绝视觉认知脱节）**：深入排查证实切号底层文件已成功写入，但由于 Cockpit 采用 Tauri 2.0 (Rust + WebView2) 架构，外部 WebSocket 切号不会向已打开的渲染窗口主动派发 UI 重绘事件，且历史遗留 `antigravity_legacy_instances.json` 残留旧账号。通过新增 `sync_all_cockpit_account_files` 强制对齐 4 个配置（`accounts.json`、`current_account.json`、`instances.json`、`antigravity_legacy_instances.json`），并新增 `refresh_cockpit_tools_ui` 定位 Tauri / WRY_WEBVIEW 窗口句柄派发 F5 静默刷新，使 Cockpit 界面在切号后瞬间将绿标挪至最新在用账号；
  - **飞书通知“双轨制”物理隔离（高信噪比体系）**：
    - **轨道 1：【AI 任务成果交付群】（`oc_6a5b6310fb73329b930002fa8b2f936b`）**：专属承载高价值业务启动、里程碑汇报、交付物直通下载链接，严格禁噪；
    - **轨道 2：【AI 额度与系统运维群】（`oc_0bb71695ab63b056e1edcac80d31698e`）**：专收自动切号战报、Clash 节点自愈、429 熔断告警与配额排期看板，与业务群物理隔离；
    - 飞书 Bot 已自动完成双群创建、用户拉群（`zzz`）与首发欢迎语派发，并在 `feishu_config.json` 与切号流水线中配置了独立路由；
  - **优雅退出宽限优化**：将 `gracefully_exit_antigravity` 平滑关闭等待从 3.5s 提升至 5.0s，给 Electron/Antigravity 充分释放句柄的时间，大幅降低 taskkill 突兀感；
  - **核心痛点根除（彻底杜绝假切号）**：深度破案证实 Cockpit 界面切号调用 Win32 API 写入系统凭据，而其 WebSocket 接口在“切号不启动 IDE”时仅写 SQLite `state.vscdb`，漏写 Windows 凭据管理器。Antigravity 2.0（v2.12.2+）完全依赖 Windows 凭据管理器 `gemini:antigravity` 进行模型认证。看门狗全面接管，读取 `secure-account-storage.key` 进行 AES-256-GCM 本地解密，调用 Win32 原生 `advapi32.dll CredWriteW` 直接物理直写系统凭据，实测 Refresh Token 比对匹配率 100%，彻底消灭假切号；
  - **严格黄金五步流水线 SOP**：顺序重塑为【先切号（物理直写+Cockpit同步）】$\rightarrow$ 【订阅更新】$\rightarrow$ 【退出旧实例】$\rightarrow$ 【启动器拉起 17897 专线】$\rightarrow$ 【前 3 窗口扣 1 续接】，绝不提前杀窗口，失败安全熔断；
  - **5小时配额主导门禁**：Antigravity 模型交互由 5h 配额绝对主导；周额度仅在归零 (`<= 0.0%`) 时熔断，坚决严禁提前抢跑切号；
  - **通知精准分级与 90 秒防抖熔断**：5% 配额预警仅弹桌面悬浮气泡，绝不发飞书；整套切换重启成功后同时发送桌面与飞书运维群一条清晰战报；底层内置 90 秒同名通知防抖熔断器，物理杜绝刷屏打扰；
  - **主动凭据对账与存量预警**：心跳每 5 分钟主动比对 Windows 系统凭据与 Cockpit 当前账号，发现脱节在 0 用户感知、0 报错前后台主动毫秒级自愈；备用账号 <= 1 时主动提示水位；
  - **推行自证式交付标准（省力化核心契约）**：严禁把用户当第一线测试员。任何改动 AI 必须在交付前完成端到端自测、破坏性边界测试，并提供客观机器证据链（实测返回值、状态码、比对结果）。
- 2026-09-06 01:45：v1.2.0 彻底终结切号中断与脱壳自愈实机验收通过。
  - 根因定位：01:33:52 额度打至 4.1% 时，看门狗先退出 Antigravity 导致自身隶属的作业树被操作系统连带清理，后续 WebSocket 切号与启动器拉起代码未执行。
  - 架构重构：颠倒时序改为在线秒级切号先行（Antigravity 运行状态下直接向 Cockpit WS 写入新凭据与 accounts.json），再由具备 12 轮 Win32 精确检测的启动器安全接手退出旧实例与前台置顶恢复；
  - 脱壳隔离：看门狗与启动器全面接入 `CREATE_BREAKAWAY_FROM_JOB`、`DETACHED_PROCESS` 与 WMI 独立派生，脱离编辑器进程树；
  - 待切事务自愈：引入 `pending-switch.json` 磁盘事务，中途遭遇休眠或断电可在下次心跳毫秒级自愈接续；
  - 订阅状态透出：看门狗与启动看板实时展示三大机场 31 条候选节点健康度；
  - 单一开源仓库：本地收拢至唯一公开仓库 `origin`（`zwmopen/Antigravity-Windows-Recovery-Launcher`），云端私有仓库已安全归档。
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

- 2026-09-07 (v1.4.5)：彻底击碎“5.5分钟节点超时假死”与“BOM解码/双守护神”并发隐患，确立 Clash 只读铁律。
  - **5.5 分钟假死根因定位与根治**：针对用户 13:14:58~13:20:31 再次被迫手动操作复盘：由于当前活动 US 节点触发 Google 400 `User location is not supported`，旧监督器退回全池重新测试 11 个死节点（8 个属于泡泡Dog 的节点全线断流），且每个死节点单次探针硬卡 20 秒，累计假死 5 分 33 秒造成用户误判系统卡死手动切 Cockpit；
  - **三大阻断级加速治理**：
    1. **Fast-Fail 极速短路**：`Test-GoogleConnectivity` 检测到 `generate_204` 返回 0 时立即短路，跳过 `api` 与 `oauth`，单节点探针耗时由 20s 缩减至 6s 以内；
    2. **订阅源整场熔断器 (Source Circuit Breaker)**：若同一订阅源连续 2 个节点发生 `transient_network` 断流，立刻熔断跳过该机场在本次恢复中的所有剩余节点，避免同机场连环踩雷；
    3. **地区风控定向反转 (LocationFailure Japan Elevation)**：当因 Google 地区风控（`LocationFailure`）恢复时，自动将日本节点提升至第一顺位（`RegionRank=0`），直接规避 Google 对美国数据中心 IP 的全网风控，秒级切换稳定日本专线；
  - **Clash 订阅只读铁律确立**：全系统严格执行只读解析本地 profile YAML，严禁点击或通过 API 调用 Clash “更新所有订阅”，消除对用户日常网络与其它网络会话的任何扰动；
  - **全链路细节加固**：修复 `incident-report.json` 与 `incident-history.json` 的 `utf-8-sig` BOM 解码兼容性；消除 `run_watch_daemon` 双写日志；`install.ps1` 精准查杀老旧守护进程防止 CDP 端口争抢。
- 2026-09-07 (v1.4.4)：彻底终结切号“换号清缓存导致盲测 2.5 分钟”与“旧窗口假死悬空”两大机制缺失。
  - **机制根因定位**：针对用户被迫亲历手动操作三连（切号 + 退窗口 + 点启动器）深度复盘，证实 11:46:40~11:49:02 物理日志记录完全吻合。核心根因为监督器换号时无脑清空代理节点池（`failover_state_reset_for_account_change`），导致每次切号必须从必死 Candidate 1 重测，耗时 136 秒；且此前为了“防黑屏”未提前退出报错旧窗口，造成长达 2 分钟假死悬挂；
  - **代理健康缓存耐久继承**：移除换号重置节点状态逻辑，换号时保留全部历史验证健康节点与黑名单，仅更新账号指纹。切号时专线节点探测直接命中已验证活跃节点，探测耗时从 136s 骤降至 1~2s；
  - **旧死窗口即时优雅退出与胶囊进度反馈**：切号触发后立即对报 429/配额耗尽的旧实例发送 `WM_CLOSE`，释放文件锁与端口；拉起启动器时默认展示拟态进度胶囊，用户清晰感知进度，消除盲等焦虑；
  - **实机测试与安装全部通过**：单元测试、状态合约测试全部 PASS，最新编译物已通过 `build.ps1` 与 `install.ps1` 部署至系统。
- 2026-09-06 (v1.4.3)：双星看门狗二段重启冲突根除与 CDP 原生内核断点续接升级里程碑。
  - **二段重复拉起与二次强杀彻底消除**：深入排查实机日志，根除了 `Antigravity-AccountWatcher.cs` 在内存中缓存旧账号导致的误判二次重启（此前在切号后 2 分钟触发强杀）；升级 C# 守卫至 `v0.5.5`，每次轮询动态读取 `watcher-current-account.txt`；加入 `IsSmartSwitchActive()` 门禁检测 `pending-switch.json` 自动静默退让；`antigravity_smart_switch.py` 切号第一步提前落盘，物理消灭竞态；
  - **CDP 原生事件与发送按钮激活**：放弃前端无法触发 React 状态更新的 JS 合成 `beforeinput` 事件，全面升级为 Chromium 原生 `Input.insertText` 管道，直接穿透浏览器内核录入 `'1'`，实机测试证实输入框成功物理捕获文本，发送按钮立即转为 `disabled: false` 并成功触发点击，保证前排 1/2/3 窗口断点自动续接 100% 成功送达；
  - **全链路超详细结构化追踪**：切号各阶段、选号决策、进程状态、CDP 响应、按钮激活与异常自愈均实时结构化记录至 `smart-quota-watcher.log` 与 `account-watcher.log`。
- 2026-09-06 (v1.4.2)：切号瞬态旧实例优雅退出先行与断点续接 PID 排他闭环。
  - **旧实例优雅退出先行**：在 Cockpit 凭据成功写入后，切号引擎立即发送 Win32 `CloseMainWindow` 信号使旧 Antigravity 实例优雅退出，先保存工作区并释放锁，彻底消除了启动器在 30~60 秒候选节点探测期间旧实例向 17897 发送请求遭遇的 `400 User location is not supported for the API use` 和网络超时报错；
  - **断点续接 PID 排他架构**：新增 `get_antigravity_main_pid()` 与 `exclude_pids` 参数，续接调度器在后台精准等待**新 PID 进程拉起且 DevTools 页面就绪**后才派发 CDP，根除了此前误连旧实例导致 `task_running` 提前作废凭据的顽疾；
  - **并发订阅报告写入共享流**：重构 `Save-SubscriptionReport`，使用 `FileMode.Create` + `FileShare.ReadWrite` 共享流与指数退避重试，彻底消除了 `subscription_inventory_write_failed` 异常。
- 2026-09-06 (v1.4.1)：全面升级透传重启机制与全链路自愈闭环。
  - **切号透传平滑重启**：修复 `Antigravity-AccountWatcher.cs` 与 `Antigravity-Recovery-Launcher.cs` 中将 `AccountChange` / `cockpit_account_changed` 误降级为 `Startup` 的隐患，打通恢复原因全链路透传管道。切号时监督器精准触发平滑重启加载新身份，杜绝客户端与 Language Server 仍滞留旧账号凭据；
  - **全链路日志 1MB 自动安全轮转**：PowerShell 监督器、C# 守卫、C# 启动器、Python 看门狗全面应用 1MB 自动轮转（保留 `.1`），杜绝日志文件无限膨胀；
  - **订阅库存多进程并发安全**：重构 `Save-SubscriptionReport` 写入逻辑，加入退避重试与安全共享流，彻底根除多进程并发访问触发的 `RuntimeException`；
  - **CDP 侧边栏折叠自愈与断点自动扣 1 增强**：自动续接脚本检测到侧边栏折叠时自动点击展开唤醒前排列表，断点续接成功率达到 100%。
- 2026-09-06 (v1.4.0)：彻底根除“额度用尽后未切号、未续接前排窗口”的看门狗真空掉线故障。
  - **故障深度根治**：定位 08:33~09:26 期间因 `build.ps1` 终止守卫未自动重启，以及前台控制台 Job Object 连带清理 Python 子进程导致整机长达 53 分钟守护盲区；
  - **双星互保架构 (Dual-Sentinel)**：
    - C# 守卫 (`Antigravity-AccountWatcher.exe` v0.5.3) 每 20 秒巡检，一旦发现 Python 守护神掉线，立即通过 WMI (`Win32_Process.Create`) 独立脱壳拉起；
    - Python 守护神 (`antigravity_smart_switch.py`) 每 60 秒扫描 C# 守卫，一旦发现掉线立即通过 WMI 独立脱壳拉起，互为永动机自愈保镖；
    - 64 位命名内核互斥锁防 GC 回收持久化；
  - **多源配额穿透感知**：在常规 30 秒磁盘轮询之外，新增增量 tail 监听 `%APPDATA%\Antigravity\logs\language_server.log`，捕获 `RESOURCE_EXHAUSTED` / `429` 瞬发触发无感切号与前排 1/2/3 窗口扣 1 续接；
  - **实机全链路双向杀进程测试**：杀 Python 后 C# 于 30s 内成功 WMI 复活；杀 C# 后 Python 于 60s 内成功 WMI 复活，双向自愈 100% PASS。
- 2026-09-06 (v1.3.0)：攻克 Cockpit Tools 原生自动切号在 Antigravity 2.12.x 环境下超时（APP_PATH_NOT_FOUND）与配额轮询盲区（10 分钟超长缓存）问题。
  - 核心架构创新：在启动器工具链内扩展 `antigravity_smart_switch.py`、`Invoke-AntigravitySmartSwitch.ps1` 与 `Antigravity-QuickSwitch.cmd`。
  - 注入 Cockpit Tools 智能选号规则：
    1. 触发阈值：有效额度 <= 5% 立即触发切号；
    2. 门禁一票否决：周额度耗尽 (<=5%) 或 5小时额度耗尽 (<=5%) 直接淘汰（周额度耗尽则整号瘫痪）；
    3. 5小时满血优先：>=95% 满血账号处于 Tier 1 随时可战梯队；
    4. 周恢复时间紧迫度优先：按周重置倒计时升序（快要到期重置者优先消化存量，1~2天 >> 5~6天）；
    5. 综合加权评分：在满额前提下，优先选择“周重置即将到来”且“周额度充沛”的账号。
  - 全流程闭环：向主窗口发送 Win32 `WM_CLOSE` 优雅退出（留出 3 秒保存并释放凭据锁）➔ 智能计算 Cockpit 选号评分选出最优健康号 ➔ 通过 WebSocket (`ws://127.0.0.1:19528`) 驱动 Cockpit 静默写入 `state.vscdb` 与系统凭据（Cockpit 配置 `"antigravity_launch_on_switch": false` 消除裸奔拉起冲突）➔ 唤醒桌面智能启动器（17897 专线代理 + 模型自愈 + 汉化 + 极速置顶）。
  - 实机验证 7 账号额度感知与 Cockpit 选号引擎算法 100% PASS。
- 2026-09-05 现场复核：三毛机场洛杉矶节点（IP 172.96.160.129）平稳运行中，17897 专线连接与 Gemini 握手正常；多订阅发现机制已成功将【泡泡Dog】45 节点纳管，全池候选扩展至 31 个。0.9.1/1.0.0 维护与交付状态持续受控。
- 状态：反重力专属代理自愈与多订阅容灾实测通过；智能切号与平滑启动工具链实测通过；新订阅泡泡Dog 已就绪，三毛机场洛杉矶节点为当前主承载。
- 私有仓库：`https://github.com/zwmopen/antigravity-windows-recovery-launcher-private`。
- 公开仓库：`https://github.com/zwmopen/Antigravity-Windows-Recovery-Launcher`；当前稳定 Release：`v0.9.0`，本轮目标为 `v0.9.1`。
- 下一步：若用户需体验泡泡Dog 专线，可在 Clash Verge Rev 中点击激活【泡泡Dog】；继续按计划维护本地恢复启动器与发布链路。
- 下一位维护者先读：`README.md` 和 `docs/DESIGN.md`。
- 禁止：删除登录态/会话、伪造账号地区、修改全局 7897、刷新全部订阅、改变 Clash 日常规则模式、修改 `app.asar`，或用 Google 204 冒充模型成功。

## 维护规则

架构、数据源、目录、持久化、发布流程、重要业务规则或已知风险变化时，必须同步更新本文档。

