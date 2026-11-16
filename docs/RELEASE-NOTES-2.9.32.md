# Google Antigravity 智能启动器与专线守护 - v2.9.32 正式稳定版发行说明

> **发布日期**：2026-11-16  
> **版本标号**：v2.9.32（彻底根除 CLI 权限误判 · 阻断全线连坐 · 胶囊取消静默退出 · 2.32 界面布局深度汉化）  
> **构建产物**：
> - 独立安装包：`Antigravity-Windows-Recovery-Setup-2.9.32-windows-x64.exe`
> - 绿色便携包：`Antigravity-Windows-Recovery-Launcher-2.9.32-windows-x64.zip`
> - 完整校验清单：`SHA256SUMS.json`

---

## 🎯 v2.9.32 重大升级亮点

### 1. ⚡ 彻底根治模型门禁 CLI 权限误判（彻底解除全线路误连坐瘫痪）
* **痛点根除**：启动器第 4 步“AI 模型验证”使用底层 CLI `agy.exe -p` 探测时，Google 返回 `Eligibility check failed: Your current account is not eligible for Antigravity, because it is not currently available in your location`；旧版正则将该账号端限制误判为物理节点的地区机房受限（`model_location`），并处以长达 12 小时的连坐封禁，导致所有优质专线（日本-3、2x专线日本-4、美国等）轮流被误判打入冷宫，直至全池枯竭抛出 `no_healthy_candidate_available`；
* **精准规则剥离**：全面排除 `Account ineligible` 与 `Eligibility check failed`，严禁再把账号端权限错误误判为代理节点物理出口限制；
* **语言服务活体直接放行**：新增 `Test-IsLanguageServerReady` 实时进程与日志探针，只要检测到反重力主程序语言服务（`language_server`）正在运行并活跃调用，直接判定模型门禁通过并秒进；
* **平滑降级验证**：CLI 遇账号端限制时，以底层 Google 204、Model API、CloudCode 200/404 真实连通为准放行。

### 2. 🛡️ 优化地区受限隔离期
* 将 `model_location` 的隔离期从极端的 720 分钟（12 小时）下调至合理的 15~30 分钟，杜绝突发偶发波动导致订阅池所有节点全军覆没。

### 3. 🛑 修复启动胶囊取消假成功弹窗 Bug
* 修复用户主动点击胶囊右上角关闭按钮或取消退出时 `ExitCode` 误置为 0，导致外层主程序误认为启动成功并弹出“未能打开反重力主窗口”具有误导性的报错弹窗；
* 增加 `UserCancelled` 状态守卫与专属退出码（`ExitCode = 2`），用户主动取消时静默优雅退出。

### 4. 🌐 反重力最新 2.32 界面布局深度汉化（`translation-core.js` v0.4.9）
* 完整汉化全新“界面布局（Interface Layout）”切换板块：
  - `Interface Layout` -> `界面布局`
  - `Knowledge Work` -> `知识工作`（面向研究、写作与日常任务的简化界面）
  - `Software Engineering` -> `软件工程`（面向编程、开发者工具与智能体管理的完整界面）

---

## 📦 安装与升级方式

1. **自动升级**：运行安装包 `Antigravity-Windows-Recovery-Setup-2.9.32-windows-x64.exe`，一键覆盖安装；
2. **绿色版解压**：解压 `Antigravity-Windows-Recovery-Launcher-2.9.32-windows-x64.zip` 后右键以管理员运行 `Install.cmd` 即可。
