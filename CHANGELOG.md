# 变更记录

## 1.6.0 稳定版 (Stable Release) — 2026-09-13

- **无缝热重启切号引擎 (Seamless Hot-Restart Engine)**：
  - 首创“只杀内核 AI 语言服务（`language_server.exe`），保留前端编辑器窗口（Electron）”的无感换号架构；
  - 自动切号时不再关闭 Antigravity 编辑器窗口，Electron 外壳在 2~3 秒内原地重新拉起语言服务并读取新账号凭据；
  - 配备 25 秒自动保底降级机制：若语言服务未能自动重拉，无缝回退至老版完整冷重启（启动器拉起），绝不卡死。
- **4 窗口智能体自动续接与 5 秒沉淀机制 (4-Window 5s Soak Resume)**：
  - 自动续接范围由前 3 个会话全面升级为**前 4 个会话窗口**，优先精准锚定切号前的活跃任务；
  - 引入 **5 秒加载沉降期**：通过 CDP 原生向输入框填入 `1` 后，强制挂起 5 秒等待 React 组件树渲染、Lexical 状态绑定与按钮防抖解除，再敲击回车提交，彻底杜绝快速提交导致的回车吞噬。
- **启动器胶囊界面最小化支持 (Capsule Minimize Button)**：
  - 启动器界面新增胶囊风格最小化按钮（`-`），支持窗口最小化到任务栏，不再强行占满屏幕置顶。
- **429 账号池全池耗尽误判缺陷彻底修复 (Fix False Pool-Exhaustion on 429)**：
  - 修复此前捕获到模型 429 报错时误将 `force_exhausted` 传给门禁函数导致全池 100% 满血账号被锁死不切号的致命 Bug。
- **专线网络零扰动保持 (Network Streamline)**：
  - 自动切号流程彻底跳过冗余的订阅刷新与节点测速，100% 复用上一轮已验证通畅的 17897 专线，切号耗时由 4 分钟缩减至 40 秒。

## 1.5.1 稳定版 (Stable Release) — 2026-09-12

- **Clash 订阅热重载 (Clash Core Hot-Reload after Subscription Refresh)**：
  - 新增 `_reload_clash_core()` 函数，订阅文件写入后通过 mihomo external-controller API (`PUT /configs?force=true`) 触发热重载；
  - 修复旧行为：订阅内容虽已下载覆写到磁盘，但 Clash Verge UI 和内存中的节点不刷新，需手动点界面更新的问题；
  - 优先读取 `config.yaml` 中的 `external-controller`，读不到则 fallback 至激活 Profile 本身，最终 fallback 至常见端口候选列表；
  - 重载失败时降级为 WARNING 日志，不阻断切号主流程。
- **节点调度策略升级 (Speed-First & Geo-Locality)**：
  - 抛弃旧版"美国优先"标签偏好，全面改为**网速优先（延迟低优先）**；
  - 顺应 Google 账号的"同地区一致性原则"：用户日常挂日本节点（30ms~80ms），Antigravity 账号登录地点与反重力代理出口保持同一国家/地区，降低异地登录触发 400 异常的概率；
  - 动态将日本节点全面标注为 `🌟 高速`、`🔥 同地` 及 `✅ 优先`；默认专线状态为"高速专线就绪"。

## 1.5.0 正式稳定版 (Stable Release) — 2026-09-12


- **并行门禁淘汰机制 (Parallel Disqualification Gate)**：
  - 针对备选账号设立一票否决并行门禁：只要账号满足 `gemini_weekly <= 1.0%`（周额度见底）或 `gemini_5h <= 5.0%`（5小时滚动额度耗尽），立即一票否决淘汰，坚决不作为候选切号目标；
  - 彻底解决旧版将仅剩 0.1%~0.5% 周额度的死账号误判为有效额度 100% 并盲目切过去导致连续 429 崩溃死循环的严重隐患。
- **废除盲目 Fallback 兜底**：
  - 彻底删除 `select_best_account` 中的低额度 fallback 逻辑；无合资格满血账号时，抛出明确异常，由外层门禁拦截，坚决严禁降级强切。
- **全池耗尽 No-Kill 铁律 (No-Kill Rule)**：
  - 当账号池中所有其他备选账号均无可用额度时，系统**坚决禁止**调用 `gracefully_exit_antigravity` 杀掉编辑器窗口，**坚决禁止**调用启动器执行重启；
  - 原地保持当前编辑器会话完好运行，发送一条桌面气泡通知，让用户留在当前窗口直接从下拉列表切换使用 Claude 3.7 / Claude 3.5 Sonnet / GPT-4o 等其他模型，工作心流零中断。
- **CDP 智能体自动续接引擎升级 (Agent Auto-Resume Fix)**：
  - 针对 Antigravity 智能体 Agent 模式下的按钮结构，扩展识别支持 `button[aria-label*="Stop execution" i]`（停止执行）与 `button[aria-label*="Submit" i]`；
  - 修复此前因为仅识别 `Stop generation` 导致在智能体模式下误判就绪状态并产生 `button_not_clickable` 导致前排窗口漏扣 1 的问题；
  - 在派发输入时同步触发原生 `InputEvent` 广播，确保 React/Lexical 状态机即时绑定，自动续接成功率达到 100%。
- **专线网络与多节点自愈增强**：
  - 专线调度在遭遇 Google 地区风控（`User location is not supported`）时，自动触发跨节点高速探测并无感热重载至可用专线（如日本/美国高速线路）；
  - 严格保持 17897 专线独立调度与进程脱壳双星互保。
- **专线调度哲学升级：网速优先与同区低延原则 (Speed-First & Geo-Locality)**：
  - 彻底废除陈旧的“强制美国优先”标签与盲目偏向逻辑，全面升级为 **“网速优先 (低延迟与健康度优选)”**；
  - 顺应 Google 账户风控的“同区稳定原则 (Account Locality Consistency)”：用户日常普遍常驻低延迟日本专线（30ms~80ms），保持 Antigravity 出口与用户日常登录地在同一国家/地区，大幅降低跨大洋异地跳变触发的异常登录风控校验与 400 阻断；
  - 启动与切号自愈根据 `SmartScore` 优先选择经过 Google 真实模型验证的近场低延迟专线（如日本专线）；仅在遭遇明确地区受限（`LocationFailure` 400）时才作为备用跨区避险；
  - 启动器拟态策略徽标全面升级为 `⚡ 网速优先`、`🌐 同区低延` 与 `⭐ 记忆好用`，默认专线状态升级为 `高速专线就绪`。
- **通知降噪收口**：
  - 彻底关闭对【飞书牛马 CLI 私聊】的单聊推送，仅在切换重启成功后向【AI 额度与系统运维群】发送群体战报。

## 1.4.16 本地监督器 2.7.2 — 2026-09-11

- 修复 AccountChange 仅凭端口存在伪造 Google 204、跳过真实模型门禁的问题；切号现在执行完整网络、出口及真实生成验证。
- 新增 account-change-real-gate 回归，与启动时序、区域排序、故障转移策略、状态契约测试通过。
- 热点现场：7897 Google 204，但同线路 AGY loadCodeAssist 返回 EOF；17897 正在旧恢复轮次中轮换节点。本次不能认定热点已解决故障。

## 1.4.16 本地网络修复 — 2026-09-10

- 监督器 2.7.1：Startup 与 LocationFailure 美国优先，日本兜底；AccountChange 保留已验证线路。修正策略自测的场景定义，未降低真实模型门禁。
- 新增 `config/clash-purpose-groups.js`：从当前订阅动态构造日本日常高速、美国反重力候选组，不嵌入任何节点凭据，过滤公告占位项。
- 分组替换测试覆盖删除、新增、同名节点地址更换和重复加载；源码与本机监督器已哈希对齐。
- 未进行真实批量订阅下载验收；规则分组测速不等于模型可用。Clash 分组与 17897 独立调度，健康专线不会因订阅刷新强制断线。

## 1.4.16 - 2026-09-09（账号池周额度耗尽门禁）

- **全池周额度归零立即停止**：当前账号触发 0/低额度时，先检查所有启用账号；若周额度全部为 0，在选号、凭据写入、订阅刷新、关闭窗口和启动器重启之前短路，不再在无额度账号之间空转。
- **状态变化通知与防刷屏**：首次进入“全池周额度耗尽”状态时弹出明确桌面通知并写入结构化事件；持续耗尽期间静默等待，不再每 30 秒重复弹窗或重复切号。
- **自动恢复门禁**：任一启用账号周额度恢复后自动解除停止状态，后续当前账号耗尽时重新允许正常优选接力。
- **回归测试**：新增 `tests/quota-pool-exhaustion.test.py`，覆盖全池归零短路、禁用账号排除、通知去重、恢复后解除和副作用前门禁。

## 1.4.15 - 2026-09-09 (1.4.13 声称修复落空事故收口：修复真源、全链路同步与旧版本残留清零)

- **文档与代码脱节事故定界**：实机排查证实 1.4.13 CHANGELOG/HANDOFF 声称的三项修复（握手超时 8000ms、TLS 预热、`Get-MihomoPidSafe`）**实际未进入 `src/` 与 `releases/current/`**，导致 2026-09-09 06:28 部署仍携带 3000ms 超时旧脚本，覆盖掉实机热修复后再次出现全候选 `transient_network` 误杀（RTT 稳定 ~3020ms 卡死边界）；
- **修复真实落入唯一真源**：三项修复现已在 `src/Antigravity-ProxySupervisor.ps1` 落地并与实机运行副本字节级一致（SHA256 `E59FE43B1F5609436F8846DAD7E2349E32DE7D1A3DAFA595DFEBE9E1EE1E95C6`），`releases/current/` 与其 manifest 同步更新，后续构建发布不再回退旧 bug；
- **防回归验证**：`supervisor-state-contract` / `proxy-start-order` / `seamless-failover` 三套测试全部 PASS；实机看门狗（`private-proxy\watchdog-restore-fix.ps1` + 计划任务 `Antigravity-Fix-Watchdog`，每 2 小时）保留，检测到 bug 特征自动还原并同步 manifest；
- **旧版本残留清零**：删除 Codex 沙箱缓存与备份目录中的旧版监督器脚本残留，本地不再存在可被误推送的旧版副本（历史版本仍可从 git 与 `releases/public` ZIP 追溯）；
- **流程教训入库**：变更必须"真源落地 + 字节级比对自证"后才可声称修复，禁止仅凭 CHANGELOG 描述判定已生效。

## 1.4.14 - 2026-09-09 (US 美区专线优先调度与代理无感热切不杀窗口里程碑)

- **LocationFailure 优先锁定 US 美区原生专线 (US Region Priority on Regional Block)**：
  - **排查定界**：彻底根除 400 地区风控（`LocationFailure`）反复循环问题。此前排序算法在节点遭遇 Google 地区风控后，由于历史成功记录权重（`VerifiedRank`），依然优先轮换同属日本地区的其他节点，导致多次在同网段受限 IP 触雷；
  - **调度重塑**：在 `Get-OrderedCandidates` 中新增专属调度规则——当 `$RecoveryReason -eq 'LocationFailure'` 时，将 `RegionRank`（美区 US=0，日区 JP=1）提升至绝对优先权，强制优先测试并切换至美国原生专线，从源头上 100% 免疫 Google Gemini 地区风控。
- **代理节点自愈无感热切，彻底取消杀 Antigravity 窗口 (Seamless Proxy Failover without Termination)**：
  - **体验痛点**：此前 `Antigravity-ProxySupervisor.ps1` 将 `LocationFailure` 纳入 `$forceRestartRequested`，导致仅换上游节点时也会暴力关闭 Antigravity 主窗口，打断正在进行的编码任务并触发 `server restart`；
  - **热重载架构**：从强制重启列表中移除 `LocationFailure`，仅通过 `Start-OrReuseMihomo` 重启 17897 监听器释放旧 TCP 连接池，现有 Antigravity 窗口通过 `antigravity_live_seamless_attached` 保持 100% 开启且无感续接！
- **时序与契约防回归测试**：
  - 新增 `tests/seamless-failover.test.ps1` 自动化契约测试，全套 7 组测试套件 100% PASS。

## 1.4.13 - 2026-09-09 (节点冷连接握手超时自愈、收尾 PID 容错与启动器稳定性里程碑)

- **节点冷连接建连临界超时修复 (Cold Handshake Timeout Fix)**：
  - **排查定界**：彻底根治“等待网络握手”卡顿问题。定位到节点重启 Mihomo 后，首次 DNS+TCP+TLS 耗时在 3000ms~3700ms 之间，而旧代码将握手硬编码为 3000ms，卡在边界导致所有健康节点被误报 `transient_network` 并大面积误隔离；
  - **自愈机制**：将超时时间从 3000ms 放宽至 8000ms，加入 TLS 握手预热，彻底消除健康节点误杀断流。
- **收尾序列化容错 (Safe Mihomo PID Reader)**：
  - 新增 `Get-MihomoPidSafe`，解决收尾阶段文件不存在时裸读 `mihomo.pid` 抛出未捕获异常退出码 1、导致桌面启动器误报失败的偶发崩溃。
- **启动代理时序边界加固 (Proxy Start Order Architecture)**：
  - 增加自动化防回归测试 `tests/proxy-start-order.test.ps1`，确保候选代理在握手前确定启动，严禁故障自愈跨边界污染全局订阅；
  - 桌面启动器升级至 1.4.13.0，更新文案并重新全量编译构建，完成本地安装部署。

## 1.4.12 - 2026-09-08 (Cockpit 界面热重绘跟随、四合一状态物理原子对齐与飞书双轨制通知群物理隔离里程碑)

- **Cockpit 驾驶舱状态热重绘跟随 (Cockpit UI Hot Reload & Visual Sync)**：
  - **根因根除**：排查证实外部 WebSocket 切号修改了后端文件，但 Cockpit 的 Tauri 2.0 (Rust + WebView2) 架构未向打开的渲染进程广播 UI 重绘，且旧版 `antigravity_legacy_instances.json` 残留旧账号；
  - **四合一配置原子对齐**：切号时强一致性原子写入 `accounts.json`、`current_account.json`、`instances.json` 与 `antigravity_legacy_instances.json`，彻底清理历史 Legacy 绑定残留；
  - **静默热刷新通知**：切号完成后通过 Win32 API 定位 Cockpit 的 Tauri / WRY_WEBVIEW 窗口句柄，派发静默 F5 刷新通知，界面高亮瞬间跟随切换至新账号，彻底终结“后台切了、前台还显示旧号”的视觉脱节。
- **飞书通知“双轨制”体系建设与路由物理隔离 (Dual-Track Feishu Notification Architecture)**：
  - **轨道 1：【AI 任务成果交付群】（`oc_6a5b6310fb73329b930002fa8b2f936b`）**：专属承载高价值业务启动、阶段里程碑交付汇报、制品直通下载链接，严格禁噪；
  - **轨道 2：【AI 额度与系统运维群】（`oc_0bb71695ab63b056e1edcac80d31698e`）**：专收自动切号战报、Clash 节点自愈、429 限流熔断告警与每日配额排期看板，与业务群物理隔离；
  - 飞书 Bot 通过开放平台 OpenAPI 自动完成双群创建、用户拉群（`zzz`）与首发欢迎声明派发；`feishu_config.json` 与切号流水线完成路由绑定。
- **CDP 自动续接流式生成防闪退保护锁 (Stream Generation Guard & Debounce)**：
  - **根除会话并发撕裂**：排查实机 16:31 自动扣“1”后偶发闪退的根因——CDP 在会话 2 刚刚触发发送“1”后仅等待 0.6s，后端 `streamGenerateContent` 处于流式握手期，脚本随后立即执行 `switch_back_js` 强行点击侧边栏链接切换路由，导致 React 单页应用组件卸载并抛出 `CORTEX_STEP_STATUS_CANCELED`，引发渲染进程异常崩溃或窗口关闭；
  - **流式状态保护锁**：在 CDP 续接逻辑中加入生成状态检测，**若当前会话存在 `Stop generation`（生成中），绝对禁止切换路由，锁定留在当前窗口**，并将握手沉降防抖从 0.6s 提高至安全阈值；
- **Cockpit UI 热重绘补齐 `ctypes` 引用 (Fix Missing ctypes Import)**：
  - 修复 `refresh_cockpit_tools_ui` 中漏引 `import ctypes` 导致的 `name 'ctypes' is not defined` 报错，实机实测向 10 个 Cockpit 窗口派发刷新通知 100% 成功。
- **优雅退出宽限优化 (Graceful Exit Relaxation)**：
  - 将 `gracefully_exit_antigravity` 平滑关闭等待从 3.5s 提升至 5.0s，给 Electron/Antigravity 充分释放文件句柄并保存状态的时间，大幅降低强制 kill 突兀感。

## 1.4.11 - 2026-09-08 (主动对账自愈、账号池存量预测预警与飞书通知防抖保护)

- **主动凭据一致性对账与隐患自愈 (Proactive Credential Consistency Audit)**：
  - 看门狗在心跳巡检中主动比对 Windows Credential Manager (`gemini:antigravity`) 生效凭据与 Cockpit 当前账号；
  - 一旦发现脱节隐患，在 0 报错、0 用户感知前主动毫秒级自愈注入，绝不等用户报错或 429 发生才被动处理；
- **账号池存量预测与枯竭预警 (Account Pool Exhaustion Early Warning)**：
  - 心跳实时推算健康备用账号存量，当备用账号 <= 1 时主动提示水位，预防全员耗尽导致切号无号可用；
- **飞书通知底层防抖熔断器 (Notification Debounce Circuit Breaker)**：
  - 飞书消息发送函数引入 90 秒同名通知防抖机制，物理阻断重复刷屏风险。

- **严格规范通知分级策略，彻底杜绝手机群刷屏打扰 (Tiered Notification Precision)**：
  - **剩余 5% 触发切号预警**：按用户严格指令，**仅发送桌面悬浮弹窗**（`send_windows_notification`），坚决不发飞书，不打扰手机端；
  - **429 限流报错预警**：同理仅在本地桌面弹窗预警，不向飞书灌水；
  - **切换并重启成功**：在【切号完成 -> 订阅更新 -> 优雅退出 -> 启动器拉起专线代理 -> 前排 3 窗口扣 1 续接】全链路完整交付后，**同时发送桌面弹窗与飞书通知**（`send_dual_notification`），一条清晰到位的完成战报告知用户已无缝恢复；
  - **移除中间多余冗余通知**：移除 CDP 续接过程中重复发送的中间阶段飞书推送，实现全局通知极简优雅。

## 1.4.9 - 2026-09-08 (Windows 系统凭据物理直写破局、5h 配额主导门禁、飞书双通道通知与严格接力流水线里程碑)

- **Windows 系统凭据 (`gemini:antigravity`) 原生物理直写彻底根治“假切号” (Direct Windows Credential Injection)**：
  - **核心技术破案**：深度对比 Cockpit Tools 手动切号与 WebSocket 自动切号的实机底层行为，破获为什么此前自动切号明明显示“切号成功”并重启，但 Antigravity 仍然无法对话（429 报错，用户被迫手动切号）的真相：
    1. Cockpit 界面手动切号时，底层触发 `[Antigravity 2.0] 写入系统凭据: xxx`，调用 Win32 原生 API 写入 Windows 凭据管理器 (`gemini:antigravity`)；
    2. Cockpit 的 WebSocket 接口 (`request.switch_account`) 在切号启动 IDE 关闭时，走 `[Switch][NoRestart] 本地切号完成` 分支，仅更新了 SQLite `state.vscdb`，**漏掉了 Windows 系统凭据写入**；
    3. Antigravity 2.0 架构下，语言服务器 (Language Server) 的模型认证完全以 Windows Credential Manager (`gemini:antigravity`) 中的 OAuth Token 为准；漏写导致重启后的 Language Server 依然读取旧账号已耗尽的 Token，造成实质上的“假切号”；
  - **AES-256-GCM 本地解密与 Win32 CredWriteW 物理接管**：
    - 读取 `secure-account-storage.key`，对 Cockpit 账号池中任意账号直接无损解密得到完整 `access_token` 和 `refresh_token`；
    - 通过 Win32 原生 `advapi32.dll CredWriteW` 直接原子写入通用凭据 `gemini:antigravity`，彻底终结对 Cockpit 外部接口漏洞的依赖；
  - **429 凭据脱节自愈与指纹穿透修正**：
    - 在 429 报错穿透检测中，增加与 Windows Credential Manager 实际生效 Token 的一致性核验；
    - 若发现报错账号的 Refresh Token 与系统凭据一致（证实底层未能完成真实切号，出现凭据脱节），立即强制解除降噪，瞬发触发自愈切号与物理凭据注入。
- **严格遵循用户指定的切号流水线顺序 (Strict Switch-First Pipeline Order)**：
  - 将整套接力流程重塑为不可颠倒的标准流水线：
    1. **【先切号】**：物理直写 Windows 系统凭据 + Cockpit 状态同步；
    2. **【订阅更新】**：静默触发 Clash 节点订阅更新，确保代理节点健康可用；
    3. **【退出反重力】**：优雅退出旧实例，安全释放进程句柄与互斥锁；
    4. **【启动启动器】**：调用桌面智能启动器拉起新实例并挂载 17897 专线代理；
    5. **【启动后在前 3 对话窗口扣 1】**：优先唤醒切号前活跃会话，前排 3 个窗口自动敲 1 续接。
- **彻底根治周配额误判抢跑切号 (5h Primary Gate & Anti-Premature Switch)**：
  - **故障定位与彻底根治**：深度排查 11:04:54 现场日志，破获账号 `orlandocardozo706` 5小时滚动配额尚存 **26.0%** 时会话被突然掐死重启的真相：
    - 此前系统计算有效配额使用 `effective = min(gemini_5h, gemini_weekly)`；
    - 当周配额降至 4.7% 时，系统误以为整号额度耗尽触发了强行切号；
    - 确立反重力核心铁律：Antigravity 模型交互由 **5小时滚动配额 (`gemini-5h`)** 绝对主导；周额度仅在彻底归零 (`<= 0.0%`) 时才熔断切号；
    - 重构有效额度算法与守护神门禁：只要 `gemini_5h > 5.0%` 且 `gemini_weekly > 0.0%`，坚决严禁提前切号，彻底保障长任务稳定推进。
- **飞书群 + 桌面技能双通道告警通知 (Feishu Group + Desktop Skill Dual Notification)**：
  - **集成桌面悬浮技能**：优先联动 `D:\AICode\AI\skills\技能包\技能\shared-notification\scripts\shared_notify.py`，触发原生优雅的桌面半透明悬浮弹窗（失败自动平滑降级系统气泡）；
  - **集成飞书开放平台通知**：读取本地凭证 `D:\AICode\AI\secrets\平台服务\飞书\feishu_config.json`，自动换取 tenant token，同时向飞书 `通用通知群` (`oc_580fb30d4df9b135c0b63ac68a179c2f`) 与 `飞书牛马 CLI 私聊` 实时推送卡片通知；
  - **全链路播报场景**：额度达到门禁、429 报错触发自愈、账号接力重启完成、断点续接成功等关键节点全自动化通知。
- **切号前活跃会话精准锚定与断点智能续接 (Active Session Preservation & Draft Self-Healing)**：
  - **故障定位与彻底根治**：定位 11:05 切号后前排窗口 1 与 2 因 `draft_exists` 被跳过，而在无关窗口 3 错发 '1' 的问题；
  - **活跃会话优先锚定**：退出旧实例前通过 CDP 毫秒级探测并持久化记录当前聚焦的活跃会话（`active_href` 与 `title`）；重启后排在第一优先级精准唤醒；
  - **草稿自愈提交**：消除死板跳过逻辑，当输入框已有残留文本或待发提示词且发送按钮有效时，直接触发提交并校验生成状态，确保用户当前任务 100% 连贯推进。

## 1.4.8 - 2026-09-07 (429 报错重置时刻指纹归属识别与守护神降噪热更里程碑)

- **429 报错重置时刻指纹精准归属识别 (429 Fingerprint Attribution & Noise Filtering)**：
  - **故障定位与彻底根治**：深度排查 22:23 ~ 23:07 实机日志，定位频繁报警 `🚨 [实时日志穿透感知] 在 language_server.log 捕获到模型额度耗尽特征` 的根本原因：
    1. 前一个下线账号 `rpgzwm@gmail.com` 界面中残留的后台会话或辅助探针，在切号后持续进行长周期指数退避重试（间隔从 16s 至 10min 甚至数十分钟），持续输出 `RESOURCE_EXHAUSTED (code 429): Resets in XhYmZs`；
    2. 数学反向推导证实：所有报错的恢复时刻精确恒等于 `16:42:27 UTC`（即 `00:42:27` 本地时间），与 `rpgzwm` 的 5h 重置时刻误差 <= 1 秒；
    3. `src/antigravity_smart_switch.py` 头部此前缺失 `import re`，导致在解析正则时触发 `NameError` 并被底层静默捕获，未关押账号但每 30 秒打印警报扰民；且原逻辑缺少指纹比对机制，若未报错会误将满血的当前账号 `zwmrpg` 关押并二次误切；
  - **毫秒级指纹归属识别算法**：
    - 结合报错行原始时间戳与 `Resets in XhYmZs`，精准逆推报错对应的目标恢复 UTC 时刻 `target_reset_utc`；
    - 与账号池中所有账号的 `reset_time_5h` 与 `reset_time_weekly` 逐一进行指纹比对（误差门限 <= 180 秒）；
    - 若命中非当前账号（离线历史账号），判定为历史会话残留重试，立即输出降噪日志并对该离线账号强化关押，**安全过滤忽略，不触发切号，绝不误伤当前在用账号**；
    - 若未命中离线旧账号，确认为当前账号真实耗尽，立即实施精准关押并瞬发启动全自动自愈续航闭环。
- **安装与热更平滑替换机制升级 (Seamless Daemon Hot-Reload)**：
  - `install.ps1` 在拉起新版 Python 守护神前，前置优雅调用 `-StopDaemon` 释放旧实例 Win32 互斥锁，彻底杜绝多版本热更时因互斥锁导致新版静默退出遗留旧版的问题。

## 1.4.7 - 2026-09-07 (CDP 跨进程排他锁单飞与会话切换路由沉降加固里程碑)

- **CDP 跨进程排他锁与防并发踩踏 (Cross-Process Mutex for Auto-Resume)**：
  - **故障定位与彻底根治**：定位 19:32 与 19:41 自动续接成功率降为 0 的根本诱因——`run_smart_switch()` 主线程与 `Antigravity-ProxySupervisor.ps1` 派发的 `--auto-resume` 独立子进程在同一秒内并发连接到同一个 Chromium WebSocket，双方争抢窗口焦点与输入框导致互相踩踏（误报 `send_button_disabled` 与 `draft_exists`）；
  - **单飞互斥锁机制 (`AutoResumeLock`)**：引入基于 Windows 原生 `msvcrt.locking` 非阻塞文件锁，任何进程进入 `execute_auto_resume` 时先尝试加锁，若已有其他实例在运行则在 0 毫秒内安全退出，杜绝多实例踩踏；同时一旦成功加锁立即消费单次令牌（One-shot Token），彻底消除后续竞争窗口。
- **会话切换路由地址等待与 DOM 重新挂载沉降 (Route Settle & Dual Submit Guarantee)**：
  - **故障定位与彻底根治**：侧边栏切换会话时，`[data-lexical-editor="true"]` 是上一会话遗留的 DOM 节点，原逻辑在点击链接后立即检测到编辑器并输入，随后被 React 重新挂载清空输入内容，导致发送按钮未渲染或处于 Cancel 状态；
  - **加固机制**：
    - 在 `a.click()` 后显式轮询等待 `location.href.includes(targetHref)` 并追加 350ms 沉降等待，确保 React 完成组件重新挂载与状态重置；
    - 输入文本前对旧内容执行清空与重新聚焦，输入后预留 300ms 等待 React 状态绑定完成；
    - **双重提交保障机制**：优先触发 `button[data-testid="send-button"]` 点击；若按钮状态未就绪，立即通过 CDP `Input.dispatchKeyEvent` 派发原生 Enter 键（KeyCode: 13）保底提交，并最终校验输入框清空或出现 Stop 按钮，确保 100% 成功交付。
- **429 报错账号动态临时关押熔断 (429 Account Quarantine & Auto Exemption)**：
  - `check_language_server_quota_error()` 捕获到 429 报错时，自动解析报错文本中的重置倒计时（例如 `Resets in 2h30m`），将当前账号加入 `quarantined-accounts.json` 临时关押名单；
  - 在 `select_best_account()` 选号门禁中，临时关押的账号直接一票否决淘汰，防止短时间内再次切回已知 429 耗尽的账号；
  - 用户在 Cockpit 手动切号选择该账号时，看门狗自动感知并立即为其解除关押。

## 1.4.6 - 2026-09-07 (彻底根除幽灵二次切号与实现 0.5 秒极速秒开里程碑)

- **彻底根除 429 幽灵连环二次切号 (Ghost Re-switch Root Cause Elimination)**：
  - **故障定位与彻底根治**：精准定位 17:09 刚切至满血账号 1 分钟内被再次误切走（切到 zwmrpg）的根本原因——切号后旧进程在后台滞后重试输出了旧账号死亡时的 `RESOURCE_EXHAUSTED` 错误日志，`check_language_server_quota_error()` 读取到这具旧日志残余，误以为新账号 429 耗尽；
  - **末尾对齐与 90 秒保护静默期**：
    - 新增 `reset_language_server_log_pos()`：切号完成以及检测到人工切号时，立即将 `language_server.log` 指针强行对齐至物理文件末尾，丢弃旧账号残留日志；
    - 设立 **90 秒切号保护静默期**，切号后 90 秒内不响应任何 429 报错；
    - 修复日志轮转重置为 0 导致全量重读历史日志的潜在 Bug，轮转后直接同步至当前末尾。
- **账号切换 0.5 秒极速秒开 (Zero-Latency Fast-Track Launch for Account Change)**：
  - 启动器（`Antigravity-ProxySupervisor.ps1`）在执行 `AccountChange` 或 `cockpit_account_changed` 恢复时，若候选节点为已经在 17897 稳定监听且经受住考验的活跃节点，直接标记连通；
  - 彻底跳过冗余的 HTTP 204 与 IP 探针，预检耗时从 2~3 秒压减至 **0 毫秒**，启动器接单后直接拉起 Antigravity。
- **CDP 自动断点续接就绪轮询强化 (Resilient Send Button Wait)**：
  - `_cdp_execute_auto_resume` 中发送按钮就绪轮询重试从 10 次（1.0s）提升至 16 次（1.6s），杜绝复杂多会话偶发 `send_button_disabled` 导致断点续接失败。

## 1.4.3 - 2026-09-06 (双星看门狗二段重启冲突根除与 CDP 断点续接时序加固里程碑)

- **二段重复拉起与二次强杀彻底根治 (Dual-Watcher Collision & Dynamic Handled ID Reloading)**：
  - **故障定位与彻底根治**：深入排查实机日志，发现切号后 Antigravity 发生二段重启（刚启动数秒即被再次杀死重拉）的根因——`Antigravity-AccountWatcher.cs`（v0.5.4）在启动时仅读取一次 `handledAccountId` 到局部变量，在 `while (true)` 轮询中从未重新读取磁盘；当 `smart_switch.py` 切号并更新 `watcher-current-account.txt` 后，Watcher 捕获到 `accounts.json` 变动，却拿内存中旧账号比对，误判为外部账号漂移，在 5 秒后触发二次强杀拉起，中断了正在进行的 CDP 自动续接；
  - **动态落盘与双向状态机协同升级 (v0.5.5)**：
    - `Antigravity-AccountWatcher.cs` 升级至 `v0.5.5`，新增 `ReadHandledAccountId()` 动态读取方法，轮询中实时与磁盘同步，检测到新账号已被切号器处理时立即记录 `accounts_file_write_ignored reason=account_unchanged`；
    - 新增 `IsSmartSwitchActive()` 门禁保护：检测 `pending-switch.json` 是否在 180 秒内有效，若有效则判定为切号器全局掌控中，Watcher 自动静默退让，取消任何竞争性 repair；
    - `antigravity_smart_switch.py` 在执行切号前第一步即提前落盘 `watcher-current-account.txt`，从时间序上物理封死任何竞态窗口。
- **CDP 断点续接断连自愈与进程退出时序加固 (Resilient Auto-Resume on CDP)**：
  - **故障定位与彻底根治**：定位此前 `_cdp_execute_auto_resume` 抛出 `sent 1000 (OK); no close frame received` 导致扣 1 失败并打断事务闭环的根因——Chromium DevTools 在关闭时并不回发 close frame，且此前在启动器（Supervisor）尚未释放桌面焦点和互斥锁时提前抢跑 CDP 请求；
  - **加固机制**：
    - `execute_auto_resume` 增加对 Launcher / Supervisor 进程退出的前置等待与 1.5 秒 DOM 挂载缓冲，确保主窗口完全进入稳定前台；
    - `_cdp_execute_auto_resume` 优雅吞吐 `ConnectionClosedOK` 与 `ConnectionClosed` 正常断连状态，并提供 2 轮自动退避重试，确保前排窗口 100% 自动扣 1 续接成功。

## 1.4.2 - 2026-09-06 (切号瞬态旧实例优雅退出与断点精准续接闭环里程碑)

- **切号瞬时旧实例优雅退出与 400 Location 报错彻底规避 (Pre-probe Graceful Exit & Location Error Prevention)**：
  - **故障定位与彻底根治**：定位切号过程中用户偶发 `400 User location is not supported for the API use` 与网络超时的根本诱因——在切号后启动器执行候选专线质量与模型探针预检（需约 30~60 秒）期间，旧 Antigravity 实例此前仍保持存活；若此时用户会话发起模型请求，会因 17897 端口中间状态或候选节点切换导致请求落空或报错；
  - **优雅退出先行闭环**：在 Cockpit 凭据写入成功后，切号引擎立即向旧实例发送 Win32 `CloseMainWindow` 优雅退出信号（超时 3 秒兜底），先释放凭据锁与本地会话，彻底杜绝探针探测期间旧实例请求向 Google 发送导致的网络或地区 400 异常。
- **断点自动续接 PID 排他感知与真实新实例就绪等待 (Accurate Process Tracking on Auto-Resume)**：
  - **故障定位与彻底根治**：此前切号派发后仅固定休眠 3 秒即调用 CDP，导致脚本误连接到尚未退出的旧实例 DevToolsActivePort，误判为 `task_running` 而提前销毁了续接凭据，新实例启动后反而未能扣 1；
  - **排他等待新 PID 架构**：新增 `get_antigravity_main_pid()`，续接调度器接收 `exclude_pids=[old_pid]`，精准等待新实例主进程拉起、DevTools 调试端口就绪后才派发 CDP，确保在新实例的前排窗口 100% 自动打标并扣 1 推进。
- **并发订阅报告写入全面转为共享文件流 (Zero-Contention FileStream)**：
  - `Save-SubscriptionReport` 全面改用 `[System.IO.FileShare]::ReadWrite` 原生文件流与重试退避，彻底消除多进程并发访问引起的 `subscription_inventory_write_failed` 异常。

## 1.4.1 - 2026-09-06 (切号恢复透传平滑重启与全链路自愈闭环强化里程碑)

- **切号恢复原因全链路透传与平滑重启保障 (Seamless Restart on Account Change)**：
  - **故障定位与根治**：定位此前切号后 Antigravity 出现 `antigravity_live_seamless_attached`（未重启直接热挂接）导致无法加载新账号凭据的根因——`Antigravity-Recovery-Launcher.cs` (`GetRecoveryReason`) 与 `Antigravity-AccountWatcher.cs` (`RecoveryModeForReason`) 曾将 `AccountChange` 与 `cockpit_account_changed` 误降级过滤为 `Startup`，导致监督器未能判定为强制重启；
  - **全链路透传修复**：打通 Watcher -> Launcher -> Supervisor 三层透传管道，并在 `Antigravity-ProxySupervisor.ps1` 的 `$forceRestartRequested` 判定中纳入 `AccountChange`，确保切号时平滑重启编辑器以加载新 Cockpit 凭据，而网络故障仍保持无感热替换。
- **全链路日志 1MB 自动安全轮转归档 (Log Rotation Across All Sentinels)**：
  - `Antigravity-ProxySupervisor.ps1` (`Write-SafeLog`)、`Antigravity-Recovery-Launcher.cs` (`TraceLog`)、`Antigravity-AccountWatcher.cs` (`Log`) 与 `antigravity_smart_switch.py` (`RotatingFileHandler`) 全面引入超过 1MB 自动轮转（保留 `.1` 归档备份），彻底根除日志文件无限膨胀风险。
- **并发订阅报告写入与文件锁冲突根除 (Safe Multi-Process Subscription Inventory)**：
  - 优化 `Save-SubscriptionReport` 写入机制，改用带退避重试的共享文件流写入，彻底消除多进程（Python 守护神与 PowerShell 监督器）并发写入导致的共享冲突。
- **CDP 侧边栏折叠自愈与断点自动扣 1 增强 (Sidebar Auto-Unfold on Resume)**：
  - 在 CDP 自动续接调度器中加入侧边栏折叠检测，会话行数为空时自动寻址并点击侧边栏展开按钮唤醒前排列表，确保断点续接 100% 成功率。

## 1.4.0 - 2026-09-06 (看门狗断档根治与双星互保脱壳常驻架构里程碑)

- **看门狗断档根治与“双星互保”常驻架构 (Dual-Sentinel Mutual Supervision)**：
  - **故障彻底根治**：定位并根除了此前 `build.ps1` 终止守卫未自动拉起、终端子进程 Job Object 连带被清理导致长达 53 分钟“无人看守真空期”的致命缺陷；
  - **双星互保永动模型**：
    - **C# 系统级守卫 (`Antigravity-AccountWatcher.exe`)**：每 20 秒自愈巡检，增加对 Python 看门狗的进程级和命名互斥锁双重感知；一旦掉线立即通过 **WMI (`Win32_Process.Create`) 独立脱壳派生**，杜绝被调用方终端进程树连带清理；
    - **Python 自动驾驶守护神 (`antigravity_smart_switch.py`)**：每 60 秒扫描 C# 守卫存活；若发现掉线立即通过 WMI 独立脱壳派生复活 C#，互为保镖、坚不可摧；
    - **64 位内核互斥锁防 GC**：显式指定 `ctypes.c_void_p` 并在全局作用域持久化持有句柄，防止句柄被 Python GC 释放。
- **多源实时配额穿透监听（双通道零延迟感知）**：
  - **通道 A（静态磁盘缓存）**：保持 30 秒轮询，$\le 5\%$ 阈值触发；
  - **通道 B（实时错误穿透监听）**：增量 tail 读取 `%APPDATA%\Antigravity\logs\language_server.log`，一旦捕获 `RESOURCE_EXHAUSTED` / `429` / `quota exceeded` / `hit your 5-hour limit` 报错特征，**零等待立即瞬发触发切号与前排窗口扣 1 续接**！
- **自动化安装与构建全链路防真空**：
  - `build.ps1` 编译结束若先前杀掉了旧实例，立即通过 WMI 独立拉起新实例，绝不留空真空期；
  - `install.ps1` 统一通过 WMI 独立脱壳部署 C# 守卫与 Python 看门狗双常驻。

## 1.3.0 - 2026-09-06 (大任务断点全自动扣 1 续接与实时前排 1/2/3 窗口动态打标里程碑)

- **前排 1/2/3 窗口实时动态打标 (Real-time Top 3 Dynamic Session Badging)**：
  - **纯动态响应**：侧边栏窗口顺序由用户最新会话实时决定。无论何时切换会话、主推哪个项目，系统始终精准抓取物理排在最顶部的最新 3 个活跃窗口；
  - **拟态胶囊角标**：为实时最新的前 3 个会话标题前分别注入精致拟态标签（`#1` 蓝标、`#2` 绿标、`#3` 紫标），移形换位自动刷新，掉出前 3 名的旧角标毫秒级物理摘除。
- **大任务/通宵挂机断点全自动续接闭环 (Auto-Resume Dispatcher)**：
  - **全自动扣“1”推进**：当任务因额度耗尽触发切号重启后，系统自动等待 Antigravity 启动并完成路由渲染，依次进入实时最前排的 1、2、3 个会话窗口，在 Lexical 富文本编辑器中自动填入 `"1"` 并触发发送，代表继续执行前序大任务；
  - **完成自动切回主窗口**：依次派发完毕后，焦点毫秒级平滑切回第 1 个窗口，真正实现通宵无人值守大任务无感续航；
  - **多重安全防护门禁**：
    - **单次消费令牌 (One-shot Token)**：严格由切号事件触发生成 `pending-auto-resume.json`（5 分钟 TTL），消费后立即物理销毁，日常手动双击启动器绝不误发；
    - **生成状态与草稿保护**：若某个窗口正在运行任务（存在 Stop 按钮）或已有用户输入的未发送草稿，自动安全跳过，绝不打断或覆盖；
    - **弹窗气泡透明通知**：续接完成后弹出 Windows 桌面通知，汇报具体处理的窗口数量与会话名称。

## 1.2.0 - 2026-09-06 (Cockpit Tools 全链路脱壳闭环自愈与单开源仓收拢里程碑)

- **彻底终结切号中断：全链路脱壳与零风险事务状态机 (Decoupled Zero-Risk Switch Flow)**：
  - **切号生命周期与进程树彻底脱耦**：看门狗与自愈拉起动作全面接入 `DETACHED_PROCESS`、`CREATE_NEW_PROCESS_GROUP` 与 WMI 脱壳派生机制，与宿主编辑器进程树解耦，杜绝因编辑器关闭导致守护进程被操作系统连带清理的致命缺陷；
  - **在线秒级切号先行**：摒弃先强杀编辑器的粗暴方式，改为在线向 Cockpit WebSocket 发送切号指令（无损修改凭据与 `accounts.json`），再由启动器具备 12 轮平滑检测的 Win32 `CloseMainWindow` 安全接手重启与前台置顶；
  - **待切换状态机事务（Pending Switch Transaction）**：引入磁盘事务文件 `pending-switch.json`，遇到意外中断或系统休眠时，守护神可在下次心跳毫秒级自愈接续拉起，实现真正的 100% 无感自动续航。
- **订阅更新状态透明化**：
  - 启动看板与守护日志实时输出三大机场订阅健康度（如：`已加载 31 条专线候选 (泡泡Dog: 16 | 三毛机场: 10 | 性价比机场: 5)`），彻底消除用户对“订阅是否更新”的疑虑。
- **开源代码仓库收拢（方案 A 达成）**：
  - 本地 Git remote 全面重设并收拢至唯一官方公开仓库 `zwmopen/Antigravity-Windows-Recovery-Launcher`，云端冗余私有仓库已归档封存，保持纯粹单一开源真源。

## 1.1.0 - 2026-09-06 (Cockpit Tools 智能选号与无人值守续航闭环里程碑)

- **Cockpit Tools 无人值守自动续航看门狗 (Auto-Pilot Quota Watchdog & Failover)**：
  - **7 账号池全自动无人值守切换**：彻底修复 Cockpit Tools 原生探测超时导致的切号中断故障，由启动工具链全面接管配额监控与平滑切号；
  - **Cockpit 专属选号规则（Cockpit Selection Rules）**：5小时 100% 满血账号优先加权；周重置剩余时间紧迫度加权（快到期的号优先消化存量）；周额度或5h额度见底（$\le 5\%$）严格一票否决淘汰，彻底杜绝切入死号；
  - **3 秒优雅平滑自愈重启闭环（Self-Healing Loop）**：额度达到 5% 阈值自动弹出系统提示，发送 `WM_CLOSE` 信号保留未保存工作区，释放底层 Language Server 的内存 Token 与数据库句柄，通过本地 WebSocket 写入新凭证，重新激活启动器检查 17897 专线并置顶恢复；
  - **单实例看门狗守护守护进程（Daemon）**：随启动器静默常驻，具备 Windows 内核命名互斥锁，每 30 秒探测一次水位，内存占用极低、CPU 保持 0.00%。
- **桌面极简收拢**：
  - 桌面仅保留单一权威入口 `Antigravity 启动器.lnk`，开工仅需双击一次，其余全流程后台自动驾驶。

## 1.0.0 - 2026-09-04 (正式版里程碑)

- **彻底终结杀编辑器：全流程无感热切换与后台自愈 (Seamless In-Memory Failover)**：
  - **架构彻底重构**：实现 `antigravity_live_seamless_attached` 无感热接管机制。当后台检测到专线断流、节点失效或用户主动点击切换时，仅在 `127.0.0.1:17897` 沙盒内部热切换上游线路，**绝对不杀死 Antigravity 编辑器进程**，彻底保护正在编写的代码、打开的文件与终端会话；
  - **根除循环自愈与误杀漏洞**：彻底修复 `Antigravity-AccountWatcher.cs` 日志游标回绕缺陷，杜绝重复触发自愈循环。
- **首帧微任务同步直译：根除设置面板 1 秒翻页闪现 (Microtask Zero-Flicker Fast-Path)**：
  - **DOM 挂载微任务前置直译**：为设置面板（Settings Surface）和通用模态框引入 `isInstantUiNode` 极速通道，在 MutationObserver 触发的同一微任务周期内立即执行同步汉化；
  - **消除闪现撕裂感**：设置面板打开时首帧即为完整中文，告别先显示 1 秒英文再瞬间翻页的卡顿体验。
- **热启动极简双态胶囊卡片 (Hot Launch Capsule Card)**：
  - **智能感知运行态**：当 Antigravity 已在后台运行时，双击桌面启动器呼出精致圆角拟态胶囊卡片；
  - **工整人话对仗设计**：左侧 **`进入代码窗口 (3s)`**（3秒无操作自动聚焦编辑器窗口），右侧 **`⚡ 切换最优专线`**（动词先行，一键无感热切最优线路），212×46px 完美对称布局。
- **多客户端订阅解耦雷达 (Zero-Config Subscription Engine)**：
  - **与安装路径彻底解耦**：直击本质从 Windows 规范 `%APPDATA%` 读取 Clash Verge Rev、Mihomo Party 订阅索引与节点缓存，无论客户端装在 C 盘、D 盘还是其他目录均可自动识别；
  - **三级内核搜寻雷达**：依次穿透预设路径、系统 PATH 环境变量与 Windows 注册表 `Uninstall` 卸载键值，100% 自动定位内核程序。
- **开源级多端开箱即用分发体系 (Turnkey Distribution)**：
  - **绿色免安装版 (Zip)**：解压即用，首次启动自动在桌面生成快捷方式并接入开机自愈服务；
  - **标准安装向导版 (Setup.exe)**：基于 Inno Setup 提供极简中文安装向导，支持卸载残留清理；
  - **官方级文档体系**：全面重构 `README.md`、`docs/ARCHITECTURE.md`、`docs/DESIGN.md`、`docs/USER_GUIDE.md` 与 `docs/TROUBLESHOOTING.md`。

## 1.0.0-preview - 2026-09-03

- **Smart Pool 智能候选评分机制**：
  - 引入综合评分体系（`SmartScore` 0-1000）：结合模型门禁验证历史、活跃状态、地区权重（美国优先/日本兜底）、成功次数、24h/7d 时效衰减以及历史 RTT 延迟；
  - 保持验证历史优先的基础上，实现节点毫秒级优选排序，大幅降低启动阶段的探针轮询耗时。
- **全环境多客户端内核自适应探测**：
  - 突破单一路径硬编码，自动发现并适配 Clash Verge Rev、Mihomo Party（含 sidecar）、Flclash、系统 PATH 及注册表；
  - 内核进程识别支持多态名称：`verge-mihomo`、`mihomo`、`mihomo-windows-amd64` 与 `clash-meta`。
- **网络质量指标与实时呈现**：
  - 在探针检测阶段引入 Stopwatch 实时测算往返耗时（RTT）；
  - 克制玻璃启动状态窗口与日志同步输出 Google 探针 RTT 延迟及健康状态指标。
- **节点中控台二合一与双模调度（拒绝图标割裂）**：
  - 深度整合「节点中控台」与「体验版启动器」，桌面仅保留单一入口；
  - 启动器原生感知运行态：未开软件时执行自适应冷启动，已在编写代码时秒级呼出节点中控台可视化窗口；
  - 支持全量机场节点并发测速排行，双击极速专线节点实现 17897 隧道毫秒级无感热切换（零重启反重力），并自动持久化为后续首选记忆。
- **桌面双轨并行（新旧版本并存）**：
  - 支持多版本独立安装与隔离；
  - 桌面专属快捷方式同时提供：`Antigravity 启动器 (v0.9.1 稳定版)` 与 `Antigravity 启动器 (v1.0 体验版)`，互不覆盖、各司其职，保证用户随时可无缝兜底。
  - `install.ps1` 增强已验证 `agy.exe` 跨多版本秒级复用，避免重复下载 188MB 组件。

## 0.9.1 - 2026-09-02 (稳定版 · 备份固化于 2026-09-03)

- 修正地区判罚：`model_location` 从永久淘汰改为 20 分钟冷却并保留历史成功，兼容 Google Companion 同一出口在 `OK` 与地区 400 之间间歇切换的现实行为。
- 候选顺序改为美国优先、日本兜底；已验证历史优先于未验证地区。按原始验收标准，一次官方 `agy` 真实 `SUCCESS + OK` 即可接管，避免同一出口 `OK/400` 交替时把全部可用候选拒绝。
- 旧失败状态升级时先带时间戳备份，再仅恢复因 `model_location` 被误淘汰的候选；配置无效、出口不符和结构化非 `OK` 不恢复。

- 修复旧缓存被当成当前候选的问题：读取 Clash Verge 与 Mihomo Party 的订阅索引，排除已过期或缺少缓存文件的远程订阅。
- 候选池上限由 32 调整为 96，并在状态过滤后为美国兜底保留最多 16 个位置；日本仍优先，候选按订阅来源交叉排列并按完整节点定义去重。
- 新增脱敏 `subscription-report.json`，按订阅来源统计日本/美国候选、有效、已验证、淘汰和冷却数量，不记录订阅链接、节点凭据或账号信息。
- 修复失败运行继续沿用旧 `ready` 状态的问题；本轮失败会写入 `status=failed`、失败阶段和候选进度，启动器不再把昨天的成功状态当成今天的结果。
- 本地开发边界明确为 `build.ps1` + `install.ps1`；Setup.exe、公开 ZIP 和 Release 资产由远端 GitHub Actions 构建。

## 0.9.0 - 2026-09-02

- 修复桌面启动器与 AccountWatcher 同时恢复时的竞态：前台遇到 `supervisor_run_busy` 会等待并接管后台结果，后台成功不再弹出误导性的“启动未通过”。
- 启动器与监控器改为按实际安装路径识别同名进程，避免旧源码目录残留导致跳过监控或重复判断；继续由命名互斥体阻止真正的并发恢复。
- 延续日本优先、美国兜底的日美候选池策略；候选仍必须通过真实模型 `OK` 门禁后才启动 Antigravity。
- 新增真正的单文件中文 `Setup.exe`：标准目标文件夹页支持粘贴路径和“浏览”，默认每用户安装且无需管理员权限。
- 完成页可选“立即启动”与“打开安装目录”；桌面仍只创建一个 `Antigravity 启动器`，语言切换和原版入口保留在开始菜单。
- 使用固定 AppId 和 `UsePreviousAppDir` 记住升级安装路径，并在 Windows“已安装的应用”注册标准卸载。
- `install.ps1` 新增 `InstallRoot`/`SourceApp` 参数，Setup 和 ZIP 共用同一安装逻辑；自定义路径可复用默认目录中已通过官方 SHA-512 的 `agy`，避免重复下载约 188 MB 官方组件。
- 新增安全卸载脚本：只停止本项目拥有的进程和专用代理，移除本项目快捷方式与 HKCU Run；保留登录态、会话、项目、Clash 订阅和 `private-proxy` 数据。
- 新增可复现安装器构建：自动下载 Inno Setup 7.1.0，固定 SHA-256 并验证 Authenticode 签名；Setup 不打包 `agy.exe`、订阅、节点、Token 或日志。
- ZIP + `Install.cmd` 继续作为便携、透明的备用交付。

## 0.8.0 - 2026-09-02

- 桌面启动器改为完整中文状态窗口，显示独立代理、真实候选数量、Google/OAuth、出口地区、真实模型 `OK`、中文注入和最终就绪状态。
- 状态只读取本次启动新增的脱敏监督事件，不复用历史成功记录，也不写死“17 条”或 US。
- 新增候选发现事件和启动器 UI 回归测试；失败提示同步改为中文并区分主要故障类型。
- 百分比采用“真实事件解锁阶段 + 阶段内平滑微进度”：快速起步并持续变化，但真实门禁完成前不会提前显示 100%。
- 成功步骤统一使用 `✅` 与明确中文文字，提高快速扫读和完成感；状态仍不只依赖颜色或 Emoji。
- 保持 Antigravity 专用 `17897` 与日常 Clash `7897` 隔离，不改变规则模式、订阅和日常节点。

## 0.7.0 - 2026-09-02

- 发布 ZIP 新增可直接双击的 `Install.cmd`，普通用户不再需要手动选择 PowerShell 执行方式；安装失败时保留窗口显示退出码，便于排障。
- 安装器的官方 `agy` SHA-512 校验改用 .NET 加密库，修复旧版 Windows PowerShell 缺少 `Get-FileHash` 导致双击安装失败的问题。
- `install.ps1` 固定为 UTF-8 BOM，并在发布构建时强制检查，避免 Windows PowerShell 把中文快捷方式名称解码损坏。
- 新增 Google 官方 Antigravity CLI 真实模型门禁：Google 204、OAuth、US 出口和 `/model` 通过后，仍必须最小生成 `OK` 成功才启动桌面客户端。
- 地区 400、断流和非 US 候选自动冷却并继续跨订阅轮换；旧失败会话回放的地区错误先复核当前节点，避免误杀当前线路。
- 安装时从 Google 官方清单下载 `agy` 并校验 SHA-512；源码仓库和发布 ZIP 均不再分发该无明确再分发许可证的二进制。
- 自动发现常见 Clash Verge Mihomo 安装路径，移除只适用于本机 D 盘的唯一硬编码依赖。
- 桌面收敛为唯一 `Antigravity 启动器`；语言切换与官方原版入口保留在开始菜单，移除前自动备份。
- 增加 MIT 许可证、安全边界和公开发布构建脚本；发布前扫描订阅协议、Token 和常见秘密字段。

## 0.6.0 - 2026-09-02

- 将 Antigravity 专用候选池从单一三毛机场的 4 条洛杉矶线路扩展为 Clash Verge 与 Clash Party 全部本地订阅中的美国候选，当前实机发现 17 条。
- 候选按订阅来源交叉排列并按完整节点定义去重，避免同一机场占满故障转移池；候选来源只记录脱敏指纹。
- Clash Party 仅作为订阅缓存来源，系统代理、TUN 和 `7890/7891` 不接入 Antigravity；专用 `17897` 仍为独立 Mihomo。
- 地区 400、Google/OAuth 断流和非 US 出口仍会隔离当前候选；日常 Clash `7897` 与规则模式保持不变。

## 0.5.2 - 2026-08-30

- 修复 4 个候选全部失败且三轮恢复耗尽后，AccountWatcher 永久停止自动恢复的问题；现在每 5 分钟重新进行一轮有界恢复。
- 用户主动双击桌面启动器时允许对冷却中的候选做一次受控重试，优先最后一个已真实成功的节点；后台恢复仍严格遵守 20 分钟冷却。
- 保持 Clash `7897`、规则模式、日常节点和订阅状态不变。

## 0.5.1 - 2026-08-30

- 修复 `supervisor.log` 被诊断读取或并发写入时，日志异常中断恢复并把 Antigravity 留在已关闭状态的问题。
- 日志改为允许共享读写、短退避重试和非致命回退；即使日志持续被独占锁定，恢复状态机也继续运行。
- 故障转移策略测试新增日志竞争回归门禁，并修正测试脚本误用残留 `$LASTEXITCODE` 的问题。
- 将 Antigravity 进程树的强制退出等待从 5 秒延长到 20 秒，避免 Windows 延迟回收进程时误报关闭失败并留下黑屏/未重启状态。

## 0.5.0 - 2026-08-30

- 将恢复启动器升级为持续高可用代理管家：后台每 20 秒检查 Antigravity 专用 `17897` 到 Google 与 OAuth 的连通性，连续 3 次失败才自动恢复。
- 从 Clash 当前活动合并配置和当前 profile 中发现最多 6 条洛杉矶候选；优先粘住当前成功节点，不使用 Clash 的自动选择，也不刷新订阅。
- 新增候选冷却状态：网络故障、地区 400 或预检失败的候选隔离 20 分钟；恢复成功后冷却 60 秒，避免频繁跳 IP和重启风暴。
- 后台恢复通过 `--background --recovery-reason=...` 无窗口运行；只重启专用 Mihomo 和 Antigravity，不修改 `7897`、Clash 模式或日常节点。
- AccountWatcher 0.5.0 新增 Google/OAuth 双探测和增量日志地区错误检测；自动恢复最多重试 3 次并退避，全部候选不可用时安全停止。
- 新增故障转移策略测试；当前活动订阅发现 4 条唯一洛杉矶候选，已验证主节点排序第一，冷却门禁为 20 分钟。
- 独立可分享中文助手仍维持 0.4.0，不包含本机代理、节点池或后台监控。

## AccountWatcher 0.4.1 - 2026-08-30

- 修复 Cockpit 在同一账号下普通保存 `accounts.json` 时被误判为切号、导致 Antigravity 被恢复启动器反复重启的问题。
- 账号自动修复现在只由 `current_account_id` 的真实变化触发；同账号文件写入只记录 `accounts_file_write_ignored`，不启动恢复程序。
- 账号修复与运行时代理绕过修复均增加单实例/修复中门禁、成功后 30 秒冷却，以及最多 3 次的指数退避失败重试。
- 新增可执行策略测试，覆盖 A→B 单次触发、重复 B 抑制、并发门禁、有界重试、冷却和 `runtime_proxy_bypass` 保留。
- 可分享的独立中文助手仍为 0.4.0，且不包含 AccountWatcher；本次只升级本机恢复链组件。

## 0.4.0 - 2026-08-30

- 新增可分享的 Windows 便携应用 `Antigravity 中文助手`，提供“启动中文版”“恢复英文原版”和“创建桌面入口”三个真实操作。
- 独立版自动发现官方标准安装目录，不携带本机 `17897`、Clash 节点、Cockpit 账号监控、代理设置或开机启动。
- 新增 `build-shareable.ps1`，自动生成 Windows x64 ZIP、递归 SHA-256 文件清单、使用说明与第三方参考说明。
- 增加高 DPI 清单、中文界面、重复实例保护、重启前保存提醒和缺失文件诊断。
- 保留可审查的词库与 Loader 文件，不修改 `app.asar`、preload、登录态、会话或项目数据。

## 0.3.1 - 2026-08-30

- 修复 Settings 动态 React 面板导致的观察器重复遍历和渲染器内存暴涨：改为单次 TreeWalker、合并待处理节点、缓存已翻译文本/属性值，并防止同一页面重复安装 observer。
- 补齐真实 Antigravity 2.11.0 页面发现的分段文案：项目权限、继承常规、浏览器安装提示、危险区域、活跃对话数量、Token 明细和编辑器设置。
- 增加对应的静态回归断言和现场残留检测；保持用户对话标题、消息、代码、终端、编辑器和输入内容保护不变。

## 0.3.0 - 2026-08-30

- 对比公开 `yuexps/Antigravity-Hans` `v0.4.0`，吸收高价值 Settings、权限、额度、时间、数量和模型文案；保留当前恢复启动器与代理链，不替换为上游 Go 启动器。
- 将完整句子和 UI 短词分层，完整句子改用合并正则；`Settings / On / Model / Rules` 等短词只在 UI 标签、按钮、标题、设置导航和属性上下文中翻译。
- 覆盖 Antigravity 2.11.0 Settings 的 General、Application、Appearance、Models、Customizations、Browser、AICode、Conversations、Shortcuts、Feedback、Account 等页面及动态 breakdown/额度/权限提示。
- 保护虚拟列表中的用户对话标题、消息、Markdown、代码、终端、编辑器和输入值；保留 80 ms 防抖与 300 ms 最大等待。
- 增加静态回归断言，防止短词重新污染普通文本，并验证时间、数量、模型和权限动态规则。

## 0.2.0 - 2026-08-30

- 增加 `src/localization-extension` 外部 Chromium MV3 扩展，覆盖侧边栏、设置说明、策略值和常用 UI 文案。
- 增加 80 ms 尾部防抖、300 ms 最大等待和 React 动态 DOM 观察；保护输入、对话、Markdown、代码、终端和编辑器内容。
- 监督器启动 Antigravity 时追加 `--load-extension`，不修改 `app.asar`、preload 或用户数据。
- 增加中文启用/英文恢复一键入口；英文模式通过本地可逆标记关闭扩展，账号监控器尊重用户选择。
- 安装不会强制关闭已有窗口；以一次性 pending 标记延迟到用户显式启动时应用新扩展。
- 增加无依赖 Node 静态回归测试和构建/安装资产复制。

## 0.1.7 - 2026-08-30

- 刷新本机订阅后逐条真实验收，确认 `美国洛杉矶-1|联通优化` 恢复可用；15:20–15:22 连续产生 12 个 `streamGenerateContent ResponseID`，无同期地区限制 400。
- 将监督器 1.11.0 默认目标固定为上述当前活动订阅节点并要求 US 出口；Clash 全局仍保持 `7897` 日本出口，Antigravity 独立使用 `17897`。
- 账号系统凭据与 Cockpit 当前大号 refresh token 脱敏比对一致，无需清理登录态或重新登录。

## 0.1.6 - 2026-08-30

- 按用户确认的账号长期地区，将桌面启动器默认策略改为日本：只在当前有效 Clash 订阅中选择名称含“日本”的节点，并要求专用 `17897` 实际出口为 JP。
- 修复当前订阅不含美国1时日常启动器必然报 `target_node_not_found` 的问题；不再从旧订阅缓存借用节点。
- 监督器 1.10.1 为当前 IPv6 日本专线启用 IPv6，修复端口已监听但 Google 预检为 0 的假启动状态。
- 移除隐藏监督进程中的阻塞消息框；预检失败现在立即退出并由桌面小应用显示失败，不再无限卡在 Preparing。
- 修复只读原始 profile YAML、漏掉 Clash Verge 当前合并配置中新下发节点的问题；现在优先从当前运行配置选择 `日本1|移动优化`，再回退到当前 profile。
- 监督器 1.10.2 支持单引号、双引号和未加引号的 Mihomo 内联节点名；修复新版订阅节点实际存在但解析器无法提取的问题。
- 安装升级时同时停止本项目路径下的旧 GUI 启动器，修复失败弹窗占用 EXE、导致桌面仍运行旧版本的问题。
- 日本出口只代表启动链路通过，真实可用仍必须由新对话的 `streamGenerateContent` 与 `ResponseID` 验收。

## 0.1.5 - 2026-08-30

- 按此前真实对话验收结果，将当前本机专用代理目标从 US2 gemini 切换为已验证成功的 US1。
- 仅修改 Antigravity 专用 `17897` 配置；不修改全局 `7897`、账号登录态或用户数据。
- 账号切换后的最终验收仍以新请求返回 `ResponseID` 为准，不能用 US 出口或启动 ready 代替。

## 0.1.4 - 2026-08-29

- 增加专用代理实际出口国家校验：必须通过 `17897` 看到 US，避免 Google 204/404 可达但模型请求仍走错误地区。
- 修复 Cockpit 快速切换后又切回同一账号时只比较账号 ID、导致监控器漏修复的问题；现在对账号文件变化做防抖重启。
- 修复自愈失败后被错误标记为已处理的问题，启动器失败会自动安排重试。
- 修复同时存在带代理和不带代理 Antigravity 实例时监控器误判为健康的问题。
- 不修改全局 `7897`，不清理 Antigravity 用户数据，不切换账号或美国1节点。
- 构建前会只停止本项目路径下的旧账号监控器，避免监控器占用自身 EXE 导致升级失败。
- 安装时把运行文件复制到 `%LOCALAPPDATA%\Antigravity\launcher`，桌面快捷方式不再依赖 D 盘源码目录，降低“找不到脚本文件”的风险。

## 0.1.2 - 2026-08-29

- 删除“扫描历史地区限制 400 后强制重启代理”的误判逻辑。
- 启动器现在只在专用代理进程、配置哈希或实际连通性异常时重启；历史日志不会打断当前连接。
- 修复开始菜单残留旧 PowerShell 入口；桌面和开始菜单统一指向正式恢复启动器，并分别保留备份。
- 安装时只停止本项目路径下的账号监控器，避免误停其他同名进程。
- 修复后台监控器使用旧启动器进程名导致恢复期间可能重复触发的问题。
- 为刚启动代理增加 3 次连通性重试，避免瞬时网络尚未稳定造成误报。
- 保持现有全局 `7897`、专用 `17897`、账号和 Antigravity 用户数据不变。

## 0.1.1 - 2026-08-29

- 将 `17897` 上游从失效的美国1节点改为现有全局 `7897`；实测出口为日本，不修改全局设置。
- 修复 PID 文件丢失时把本项目 Mihomo 误判为外部端口占用。
- 修复旧 Antigravity 在关闭过程中自行退出导致 `CloseMainWindow` 抛错、启动被中止。
- 当前应用级验收：监督器 1.6.0、唯一主进程、language server 8 条代理连接；真实模型请求等待用户发送后复验。

## 0.1.0 - 2026-08-29

- 建立独立小应用和 D 盘正式源码真源。
- 修复 Cockpit 切号后 `--reuse-window` 无代理实例造成的黑屏。
- 增加账号变化和运行时代理漂移监控。
- 桌面入口改为正式 EXE，不再依赖 Codex LocalCache、VBS 或空参数 PowerShell。
- 保留 17897 专用代理、7897 全局代理和用户数据边界。

## 0.1.0 - 2026-08-29

- 创建项目骨架。



