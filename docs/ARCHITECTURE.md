# 架构与数据流

## 系统边界

- 输入：桌面双击、Cockpit 当前账号变化、Antigravity 主进程命令行漂移。
- 输出：一个使用 `127.0.0.1:17897` 的健康 Antigravity 实例、可选的本地中文 UI 扩展及脱敏状态日志。
- 外部依赖：Antigravity 2.11.0、Cockpit Tools、Clash Verge 内置 Mihomo、有效订阅节点。

## 目录和模块

| 路径 | 职责 | 是否权威真源 |
|---|---|---|
| `src/` | 功能源码 | 是 |
| `src/localization-extension/` | MV3 外部扩展、词库和 DOM 翻译逻辑 | 是 |
| `docs/` | 设计、架构、交接和排障 | 是 |
| `tests/` | 验证代码和验收用例 | 是 |
| `.work/` | 可删除中间产物 | 否 |
| `installer/` | Inno Setup 单文件安装器定义 | 是 |

## 数据流

```text
桌面 EXE / 后台监控
→ PowerShell 监督器
→ Clash Verge 与 Clash Party 本地订阅缓存中的跨来源粘性候选池
→ 专用 Mihomo 17897
→ Google/OAuth/JP 或 US 出口基础门禁
→ 官方 agy 最小真实模型门禁
→ 关闭无代理或黑屏实例
→ 注入代理并启动 Antigravity
→ CDP Loader 向本地页面注入词库与 content.js（MV3 参数保留为兼容回退）
→ content.js 监听本地 UI DOM，按文本/UI上下文选择词库并防抖替换
→ language server 连接验证
→ supervisor-state.json
```

## 安装、升级与卸载

```text
Setup.exe / ZIP Install.cmd
→ 同一份 install.ps1
→ 用户选择的安装目录（默认 %LOCALAPPDATA%\Antigravity\launcher）
→ 官方 agy 清单 + SHA-512 校验（不随安装包分发）
→ 桌面唯一入口 + 开始菜单 + HKCU Run Watcher
```

Inno Setup 使用固定 AppId、`PrivilegesRequired=lowest` 与 `UsePreviousAppDir=yes`，因此按当前用户注册卸载并复用旧目录。`uninstall.ps1` 只清理本项目进程、快捷方式、HKCU Run 和安装目录内可重建文件；Antigravity 用户数据、Clash 数据和 `%LOCALAPPDATA%\Antigravity\private-proxy` 位于安装目录之外并保留。

### 持续健康与故障转移

- AccountWatcher 0.5.2 只在存在合规 Antigravity 主进程时，每 20 秒经 `17897` 检查 Google 204 和 Google OAuth HTTP 响应。
- 单次或两次失败只计数；连续 3 次失败才以 `NetworkFailure` 后台启动监督器。语言日志新增 `User location is not supported` 时以 `LocationFailure` 立即轮换。
- 监督器从 Clash Verge 与 Clash Party 的本地订阅缓存解析日本和美国内联节点，兼容单引号、双引号和未加引号，按完整节点定义去重并按订阅来源交叉排列，最多保留 32 条；日本候选优先，美国候选兜底。
- 当前候选 ID 由来源、名称和定义的哈希组成，来源只保存短指纹，不保存订阅 URL、节点服务器、UUID、密码或完整配置。失败候选写入 `failover-state.json` 并冷却 20 分钟。
- 每个候选必须依次通过 Mihomo 配置测试、Google/API 连通、候选声明的 JP/US 出口和官方 CLI 最小真实生成检查才可接管；`/model`、Google 204 和 IP 地区不能代替真实生成。全部失败时停止，不修改 `7897` 或 Clash UI 状态。
- `agy.exe` 不进入源码仓库或发布 ZIP。安装脚本从 Google 官方更新清单下载并校验 SHA-512，安装到 `%LOCALAPPDATA%\Antigravity\launcher\tools\agy`。
- 新候选接管后 Antigravity 完整重启以清理旧长连接。后台恢复无窗口、最多 3 次退避；真实模型成功仍由后续正常对话的 `ResponseID` 证明。

英文恢复入口只创建 `localization-extension-disabled.flag`，监督器仍执行同一代理和健康检查，但不追加 `--load-extension`。中文入口删除该标记后重新启动。安装阶段会暂存 `localization-extension-pending.flag`，避免升级时强制关闭已有窗口；第一次显式语言启动或恢复启动会清除它。

### AccountWatcher 触发边界

- `accounts.json` 的修改时间只是“重新读取账号 ID”的信号，不是恢复信号。
- 只有稳定读取到的 `current_account_id` 与上次成功处理的 ID 不同，才允许账号切换恢复；相同 ID 的普通保存记录 `accounts_file_write_ignored` 后结束。
- 仍保留对运行中主进程缺少 `17897` 或应启用汉化时缺少 Loader/扩展钩子的连续检查，即 `runtime_proxy_bypass`。
- 命名互斥体、按实际路径的启动器运行检查和 `repairInProgress` 共同阻止并发修复；前台启动器遇到后台监督器占用时等待其结果，不把 `supervisor_run_busy` 误报为用户失败。每类失败最多尝试 3 次，间隔 10/20 秒后进行最后一次尝试；成功后冷却 30 秒，避免事件风暴。
- 账号修复耗尽后会抑制该账号 ID，直到观察到不同 ID；运行时修复耗尽后必须先恢复健康，才会重置尝试次数，因而不会无限重启。

### 汉化运行时边界

- `translation-core.js` 将完整句子与短 UI 标签分开。完整句子使用一次合并正则并按最长匹配处理；`Settings`、`On`、`Model`、`Rules` 等短词只在按钮、标题、标签、设置导航和属性上下文中启用。
- 动态规则覆盖权限请求、相对时间、额度刷新、模型名/档位、`See all (N)`、`Show N breakdown(s)`、技能数量和文件/搜索数量。
- `content.js` 保护 `data-testid="conversation-row-sidebar"` 中的用户对话标题，仍允许时间戳翻译；同时保护消息、Markdown、代码、终端、编辑器、可编辑区和输入值。`placeholder`、`title`、`aria-label` 等界面属性仍可翻译。
- 词库参考公开的 Antigravity-Hans 高价值文案并独立实现运行时；不复制其启动器、静态补丁或没有明确授权的完整源码。

## 数据与持久化

- 本地数据：`%LOCALAPPDATA%\Antigravity\private-proxy` 中的 PID、监督状态、候选冷却状态和脱敏日志。
- 云端数据：无。
- 缓存：Mihomo 运行缓存，可重建。
- 备份和恢复：快捷方式和设置修改前带时间戳备份；不触碰用户会话数据。
- 迁移和兼容：源码使用环境目录解析；Mihomo 路径和目标节点目前仍是本机配置，跨电脑安装前需发现并配置。

## 安全和权限

仅监听回环地址 `127.0.0.1:17897`，不开 TUN、局域网和外部控制接口；日志对密码、Token、UUID、服务器与配置内容脱敏。

