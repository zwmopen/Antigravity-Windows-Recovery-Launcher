# 踩坑与故障排查

## 记录模板

### 问题名称

- 现象：
- 根因：
- 修复：
- 验证：
- 防回归：
- 适用版本：

### 桌面能打开但消息无回复，17897 没有监听

- 现象：Antigravity 窗口仍在，但新消息无响应；`127.0.0.1:7897` 正常，`127.0.0.1:17897` 没有监听，主进程或 language server 命令行不含 `17897`。
- 根因：桌面快捷方式或开机监控仍指向旧安装副本；旧监督器可能已经把本轮状态写成失败，但旧版应用窗口不会自动获得专用代理。
- 修复：在项目源码目录运行 `build.ps1`，再运行 `install.ps1`；安装脚本只更新稳定运行目录、桌面/开始菜单入口和 watcher，不清理 Antigravity 用户数据。
- 验证：重新从桌面唯一的 `Antigravity 启动器`启动；必须看到 17897 监听、主进程带 `--proxy-server=http://127.0.0.1:17897`、language server 有 17897 连接，并且官方 `agy` 门禁返回 `status=SUCCESS` 且正文为 `OK`。
- 防回归：不要直接点官方原版快捷方式作为可用性判断；不要用 Google 204、OAuth 或页面加载完成冒充模型成功。
- 适用版本：0.9.1。

### 订阅缓存过期或多个来源同名

- 现象：旧版本显示候选很多，但启动时逐条超时；更新后的报告数量变少，或同名订阅只保留部分来源。
- 根因：缓存目录会保留历史 YAML；仅按文件扫描会把过期订阅当成当前候选，同名来源也会让统计难以区分。
- 修复：0.9.1 先读取 Clash Verge / Mihomo Party 的订阅索引和有效期，再解析索引对应缓存；按完整节点定义去重，报告按来源名称统计。
- 验证：查看 `%LOCALAPPDATA%\Antigravity\private-proxy\subscription-report.json`，核对 `indexed_subscription_count`、`expired_subscription_count`、各来源的 `japan_count`/`united_states_count` 与候选总数。
- 防回归：不刷新全部订阅、不改变 Clash 规则/全局/直连模式；其他电脑必须重新发现本机索引和缓存，不能照搬本机节点 ID 或“某机场一定可用”的结论。
- 适用版本：0.9.1。

只保留会影响后续开发和运维的稳定经验。单次命令输出和完整日志不进入本文档。

### 专用端口正常但上游节点突然 EOF

- 现象：`17897` 仍监听、language server 仍有本地连接，但 Google/OAuth 请求超时或返回 `EOF`；同期日常 `7897` 正常。
- 根因：本地分流和进程链健康，当前专用节点到 Google 的上游线路发生短时断流。
- 修复：0.5.0 后台每 20 秒检查 Google 与 OAuth；连续 3 次失败才隔离当前候选 20 分钟，从当前活动订阅选择下一条日美候选并无窗口恢复。
- 验证：`account-watcher.log` 出现连续失败、`health_recovery_started` 和成功事件；`failover-state.json` 的 active ID 变化；`7897` 进程、模式和节点不变；最终新对话产生 `ResponseID`。
- 防回归：不以单次超时切换；不刷新全部订阅；不调用 Clash 自动选择；全部候选失败后最多重试 3 次并停止。
- 适用版本：0.5.1 / AccountWatcher 0.5.1 / 监督器 2.0.1。

### 历史地区 400 导致每次启动都重启代理

- 现象：每次双击启动器都重新拉起 17897，界面短暂断开；Google 仍可能返回 `User location is not supported for the API use.`。
- 根因：旧逻辑只读取语言服务日志最后 400 行，没有区分日志产生时间，把历史错误误当成本次代理故障。
- 修复：不再用历史地区错误触发代理重启；仅依据专用 Mihomo 的进程归属、配置哈希和当前 Google 连通性修复。
- 验证：连续启动时应出现 `proxy_reused`，而不是 `proxy_restart_requested_after_location_error`；真实模型结果仍需看本次新请求。
- 防回归：启动器测试必须检查旧 400 存在时仍复用健康的 17897。
- 适用版本：0.1.2 / 监督器 1.7.0。

### 全局日本出口导致模型请求地区限制

- 现象：Google 连通性正常，但新对话返回 `User location is not supported for the API use.`。
- 根因：此前 17897 只是转发全局 7897，连通性成功不代表模型 API 所需出口资格满足。
- 修复：从当前 Clash 订阅缓存精确提取美国2 gemini 节点给 17897；不改全局、不回退美国1。
- 验证：配置测试、17897 建立、Google 连通性通过后，再以真实新请求判断模型结果。
- 适用版本：0.1.3 / 监督器 1.8.0。

### 专用代理刚启动时连通性自检瞬时失败

- 现象：17897 已监听，但第一次启动自检记录 Google `0`，随后手工通过同一端口访问正常。
- 根因：端口先于代理上游连接稳定，单次 HTTP 自检过早执行。
- 修复：Google 与 Generative Language 连通性检查最多重试 3 次，每次间隔 2 秒。
- 验证：启动日志记录 `google_connectivity_passed`，并包含 `attempts`；持续失败才阻止启动。
- 适用版本：0.1.2 / 监督器 1.7.0。

### Google 可达但模型仍走错地区

- 现象：`17897` 能返回 Google `204` 和 Generative Language `404`，界面也显示 ready，但真实对话仍失败或返回地区限制。
- 根因：HTTP 可达只证明网络通，不证明请求经过目标国家出口；此前自检没有读取实际出口。
- 修复：当前版本在启动阶段通过 `17897` 请求出口探针，要求实际地区与候选声明的 `JP` 或 `US` 一致；其他地区或无法判定时淘汰该候选并继续下一条，全部失败才安全停止。
- 验证：`supervisor.log` 应出现 `proxy_egress_country_passed country=US`，状态文件记录 `egress_country=US`。
- 防回归：不要把 Google `204/404` 单独当作模型可用；仍需对当前账号发起一次真实对话验收。
- 适用版本：0.1.4 / 监督器 1.9.0。

### Cockpit 普通保存账号文件导致 Antigravity 反复重启

- 现象：用户没有切号，Cockpit 只是写入 `accounts.json`，日志却出现 `accounts_file_changed → repair_started`，Antigravity 被关闭再启动。
- 根因：0.1.4 为覆盖 A→B→A 特例，把任意文件写入直接升级为修复事件；Cockpit 的普通状态保存因此被误判。
- 修复：AccountWatcher 0.4.1 只比较稳定的 `current_account_id`。同账号写入记录 `accounts_file_write_ignored reason=account_unchanged`，不启动恢复程序；真实 A→B 仍修复一次。
- 验证：运行 `tests\run-account-watcher-tests.ps1`；实机观察同账号写入后 Antigravity PID 不变，日志没有新的 `repair_started`。
- 防回归：修复中不得并发启动；成功后冷却 30 秒；账号切换和 `runtime_proxy_bypass` 各自失败最多 3 次并退避，耗尽后停止。
- 适用版本：AccountWatcher 0.4.1。

### US2 出口正常但已验证账号仍被拒绝

- 现象：切回此前成功的大号后，`17897` 为 US、Google 连通性正常、主进程也带专用代理，但真实对话仍返回 `FAILED_PRECONDITION 400`。
- 根因：Google 的地区/API 资格判断同时受账号与节点/出口组合影响；本机 US2 不是此前成功组合。
- 修复：切换 Antigravity 专用代理目标为此前真实对话成功的 US1；不修改全局代理和账号数据。
- 验证：必须重新启动带 `17897` 的唯一主进程，并由当前账号发起新对话；出现新的 `streamGenerateContent`/`ResponseID` 才算通过。
- 防回归：其他电脑不得照搬 US1/US2 名称或结论，必须重新发现节点并做真实请求验收。
- 适用版本：0.1.5。

