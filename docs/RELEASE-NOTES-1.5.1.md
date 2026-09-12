# Antigravity Windows Recovery Launcher v1.5.1 正式稳定版 (Stable Release)

## 核心更新

### 1. Clash 订阅自动热重载 (Clash Core Hot-Reload after Subscription Refresh)
- 新增 `_reload_clash_core()` 机制：在切号拉取并覆写各机场订阅 YAML 配置后，自动通过 Clash Verge / Mihomo 的 External Controller REST API (`PUT /configs?force=true`) 触发内核配置热重载。
- 彻底解决以往“订阅配置文件已成功下载覆写，但 Clash Verge 内存与图形界面仍驻留旧节点列表，必须手动点击刷新”的痛点，确保切号后立即可用最新节点池。
- 兼容多种 Controller 配置来源，具备多端口自动 Fallback 与超时安全降级保护，绝不阻塞切号主流程。

### 2. 网速优先与同地区一致性专线调度 (Speed-First & Geo-Locality)
- 全面落实“网速优先（低延高速优选）”调度哲学，废除陈旧的固定地区偏好。
- 顺应 Google 账号风控环境同区一致性原则：将 Antigravity 专线出口优先维持在与日常账号环境一致的高速低延节点（如日本 30ms~80ms 专线），显著降低跨洲异地跳变触发的 400 校验异常。

---

## 测试版功能特性 (v1.6.0-Beta / "Antigravity 测.lnk")

测试版现已支持独立桌面快捷方式（启动参数携带 `--beta`），包含三大高能特性：
1. **启动器界面最小化按钮**：双选卡片与胶囊自愈窗右上角新增微缩拟态最小化按钮（减号），点击即可降至任务栏，彻底解决置顶挡视线困扰。
2. **强制续接与卡顿自愈 (Force Auto-Resume)**：启动与切号后，无论窗口处于加载中、排队中或生成中，均强制键入并回车派发激活标记 `1`，激活卡顿会话，确保心流不中断。
3. **秒级快速切号 (Fast Account Switch)**：自动切号时，直接复用当前已验证健康运行的专线节点配置，跳过重复的网络测速与 Google 门禁多轮探测，重启耗时从 30~60 秒大幅缩短至 2~5 秒秒级直启。