# Antigravity Windows Recovery Launcher v1.4.12 发布说明

## 核心更新

### 1. Cockpit 驾驶舱状态热重绘跟随与四合一配置物理原子对齐
- **彻底根治视觉状态脱节**：排查证实外部 WebSocket 切号虽成功修改底层文件，但 Cockpit 的 Tauri 2.0 (Rust + WebView2) 架构未向打开的渲染进程广播 UI 重绘，且旧版 `antigravity_legacy_instances.json` 残留旧账号；
- **四合一配置原子对齐**：切号时强一致性原子写入 `accounts.json`、`current_account.json`、`instances.json` 与 `antigravity_legacy_instances.json`；
- **静默热刷新通知**：切号完成后通过 Win32 API 定位 Cockpit 的 Tauri / WRY_WEBVIEW 窗口句柄，派发静默 F5 刷新通知，界面高亮瞬间跟随切换至新账号。

### 2. 飞书通知“双轨制”体系建设与路由物理隔离
- **轨道 1：【AI 任务成果交付群】（`oc_6a5b6310fb73329b930002fa8b2f936b`）**：专属承载高价值业务启动、阶段里程碑交付汇报、制品直通下载链接，严格禁噪；
- **轨道 2：【AI 额度与系统运维群】（`oc_0bb71695ab63b056e1edcac80d31698e`）**：专收自动切号战报、Clash 节点自愈、429 限流熔断告警与每日配额排期看板，与业务群物理隔离；
- 飞书 Bot 通过开放平台 OpenAPI 自动完成双群创建、用户拉群（`zzz`）与首发欢迎声明派发；`feishu_config.json` 与切号流水线完成独立路由绑定。

### 3. 优雅退出宽限优化
- 将 `gracefully_exit_antigravity` 平滑关闭等待从 3.5s 提升至 5.0s，给 Electron/Antigravity 充分释放文件句柄并保存状态的时间，大幅降低强制 kill 突兀感。
