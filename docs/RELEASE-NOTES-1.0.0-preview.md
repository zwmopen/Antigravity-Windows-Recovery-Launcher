# 1.0.0-preview 发布说明

1.0.0-preview 是 Antigravity 恢复启动器的重要架构演进版。该版本在保持专用 `127.0.0.1:17897` 独立代理与官方 `agy` 真实模型门禁的前提下，全面升级为自适应、可量化指标的智能调度架构，并支持与 0.9.1 稳定版双轨并行。

## 这版带来什么

### 1. Smart Pool 智能候选健康评分（`SmartScore` 0~1000）
* **多维综合加权**：融合门禁验证历史（+500）、当前活跃状态（+200）、地区偏好（美国+150 / 日本+80）、成功频次（最高+150）、24h/7d 时效衰减（+100/+50）以及 RTT 延迟加权（<=350ms +50）；
* **极速调度**：在轮询候选节点时优先测试历史上表现最好、延迟最低的节点，大幅减少因逐个测试带来的等待时间。

### 2. 全环境多客户端内核自适应探测
* 解除对特定客户端单一硬编码路径的依赖；
* 自动探测并兼容 Clash Verge Rev、Mihomo Party（包括主程序及内嵌 sidecar 内核）、Flclash、系统 PATH 环境变量及 Windows 注册表；
* 进程识别多态化：支持 `verge-mihomo`、`mihomo`、`mihomo-windows-amd64` 与 `clash-meta`。

### 3. 网络质量与 RTT 延迟实时呈现
* 在探针阶段集成 Stopwatch 高精度耗时统计，实时测算 Google 204 往返延迟并在克制玻璃状态窗口与日志中显示；
* `supervisor-state.json` 增加 `active_node_score` 与 `active_node_rtt_ms` 持久化字段，便于实时状态监控。

### 4. 桌面双轨并行与秒级复用
* 支持与 `v0.9.1 稳定版` 物理级隔离共存，桌面提供独立的 `Antigravity 启动器 (v1.0 体验版)` 快捷方式；
* 安装时秒级复用本地已验证的 188MB 官方探针组件，无需重复下载。

### 5. 节点中控台与启动器二合一原生合并（Dual-Mode Dispatch）
* **单一入口，拒绝割裂**：桌面仅保留一个 `Antigravity 启动器 (v1.0 体验版)` 主力快捷方式，移除孤立的单独中控台图标；
* **冷启动模式（软件未开时）**：双击启动器自动运行自适应探针、Smart Pool 优选并拉起 Antigravity；
* **热呼出模式（软件已开时）**：双击启动器绝不重启软件或打断代码编写，直接秒开「节点中控台」可视化面板；
* **无感热切换**：支持全量机场节点毫秒级并发测速与实时排序，双击任意优质专线即可在 17897 隧道无感热替换，且自动持久化为后续冷启动的首选记忆。

---

## 官方发布包校验和

| 文件名 | 类型 | SHA-256 |
| :--- | :---: | :--- |
| `Antigravity-Windows-Recovery-Setup-1.0.0-preview-windows-x64.exe` | Windows 安装程序 | `2AB8C6BDB1BEAD651C9637C13F5DC22105AA9F8513FF1B81C37040229ECD2149` |
| `Antigravity-Windows-Recovery-Launcher-1.0.0-preview-windows-x64.zip` | 绿色免安装压缩包 | `E5325602CEBD8F62FD3A2DE847A27DE231BBC57548158E8E0AEBB71AA16D4235` |

---

## 本地使用与部署

```powershell
Set-Location 'D:\AICode\工具开发\projects\antigravity-recovery-launcher'
& .\build.ps1
& .\install.ps1 -InstallRoot "$env:LOCALAPPDATA\Antigravity\launcher-v1.0"
```

---

## 质量与测试验收

* `candidate-cap-fairness.test.ps1`: PASS
* `supervisor-state-contract.test.ps1`: PASS
* `run-failover-policy-tests.ps1`: PASS
* `run-account-watcher-tests.ps1` (14 项): PASS
* `localization-extension.test.js`: PASS
* `shareable-assistant.test.js`: PASS

---

## 当前已知限制与边界说明

1. **上游节点质量依赖**：启动器能够最大化利用你的现有订阅并智能优选，但若机场所有日美节点的出口均被 Google 官方封禁或判定为未开放地区（连续返回 400），启动器将进入保护性冷却与退避，不会盲目强行启动导致后续卡顿。
2. **首次探针冷启动耗时**：如果当前网络波动导致前序高分节点暂时超时，启动器会自动顺延测试下一条候选，此过程需要约 10~20 秒进行完整的 Google 204、出口地区及真实模型三次握手门禁。
3. **前端 DOM 汉化依赖**：当前汉化采用 CDP Loader 注入，若未来 Google 官方发布重大架构更新重构了界面层，个别新增词条可能需要更新映射字典。
