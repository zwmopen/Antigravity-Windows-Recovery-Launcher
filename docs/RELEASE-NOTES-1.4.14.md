# Antigravity Windows Recovery Launcher v1.4.14 发布说明

## 核心更新

### 1. Google 400 地区风控（LocationFailure）优先锁定 US 美区原生专线
- **排查定界**：彻底根除 400 地区风控（LocationFailure）反复循环问题。此前候选节点排序算法在节点遭遇 Google 地区风控后，由于历史成功记录权重（VerifiedRank），依然优先轮换同属日本地区的其他节点，导致多次在同网段受限 IP 触雷；
- **调度重塑**：在 Get-OrderedCandidates 中新增专属调度规则——当 $RecoveryReason -eq 'LocationFailure' 时，将 RegionRank（美区 US=0，日区 JP=1）提升至绝对优先权，强制优先测试并切换至美国原生专线，从源头上 100% 免疫 Google Gemini 地区风控。

### 2. 代理节点故障转移无感热切，彻底取消杀 Antigravity 窗口
- **体验痛点**：此前 Antigravity-ProxySupervisor.ps1 将 LocationFailure 纳入 $forceRestartRequested，导致仅换上游节点时也会暴力关闭 Antigravity 主窗口，打断正在进行的编码任务并强杀正在工作的后台子 Agent；
- **热重载架构**：从强制重启列表中移除 LocationFailure，仅通过 Start-OrReuseMihomo 重启 17897 监听器释放旧 TCP 连接池，现有 Antigravity 窗口通过 ntigravity_live_seamless_attached 保持 100% 开启且无感续接！

### 3. 时序与契约防回归测试全覆盖
- 新增 	ests/seamless-failover.test.ps1 自动化契约测试；
- 全套 7 组测试套件 100% PASS，保障架构绝不退化。
