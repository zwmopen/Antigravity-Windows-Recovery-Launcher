# 启动检查体验与真实状态契约（2026-11-11）

> 状态：源码已落地；Windows CI 与本机联网验收需要查看对应结果。此文档不表示实机检查已经通过。

## 目标

用户无需理解 Mihomo / OAuth / agy：默认只看到「账号 → 专线 → Google → AI → 工作区」五步。每步显示当前动作、真实检测结果或等待状态；不使用将时间推演伪装成实际完成比例的可见进度条。

## 实际执行与数据来源

| 界面步骤 | 权威数据来源 | 通过条件 / 限制 |
| --- | --- | --- |
| 当前账号 | Cockpit `accounts.json`、配额缓存与 `launch-account-status.json`；`preflight_account_check_*` | 初始化网络前运行本地门禁。5 小时 / 周额度均需大于 5%；异常账号会触发切换。界面必须标注「本地缓存」，不可宣称实时 Google 额度 |
| 本地专线 | Clash Verge / Mihomo Party 当前配置与有效订阅缓存；`candidate_discovery_completed`、`latency_probe_*`、`candidate_preflight_*` | 候选发现不代表已测速；仅对排序靠前的最多六条进行网络延迟预测速。正式候选序号由事件提供，测试通过才显示专线已就绪 |
| Google 通路 | `google_connectivity_started`、`google_probe_*`、`google_connectivity_passed`、`proxy_egress_country_passed` | 每个请求显示服务名和 HTTP 状态。非零状态证明端点回应，不代表 OAuth 登录成功或模型授权成功。出口国来自 Cloudflare trace |
| AI 模型验证 | `formal_model_gate_started`、`model_probe_waiting`、`model_generation_probe_passed` | 使用本地官方 `agy` CLI，要求真实生成 `OK`，成功条件含进程退出码与 JSON。单次运行硬超时 40 秒，可能消耗模型配额 |
| 启动工作区 | `antigravity_started`、`antigravity_ready`、`antigravity_live_seamless_attached` | 应用、语言服务完成检查才显示完成。预启动或汉化完成不代表工作区已经可用 |

## 状态显示约束

1. **待机**：灰色序号，文案「等待……」。
2. **运行**：蓝色高亮当前步骤，文案注明正在请求哪个服务或测速第几条；网络请求延迟一律标注为「请求延迟」，不得等同下载速率。
3. **通过**：绿色勾，仅由明确的后端成功事件置位；HTTP 响应不显示为「授权已通过」。
4. **失败**：保留当前原因（超时、地区限制、账号额度不足等），网络故障不归咎于模型/账号。
5. **候选数量**：发现 `N` 条只表示候选发现。**禁止**在首条 `candidate_preflight_started` 事件出现前显示「验证 1/N」。
6. **快速复用**：已有 17897 代理仅在本轮 Google 204、账号门禁和真实模型探针均通过后标记复用成功。
7. **隐私**：原始邮箱、Token、代理服务器与订阅 URL 不进入新的可见日志事件；完整认证数据仍仅留在本机安全状态文件。
8. **可见进度**：原有 `CapsuleProgress` 对象因兼容性保留但隐藏；不将预定百分比作为用户可见的检测进度。

## 本次代码范围

- `src/Antigravity-ProxySupervisor.ps1`：前移本地账号门禁；增加候选测速与 Google 各端点请求耗时、HTTP 状态事件。
- `src/antigravity_smart_switch.py`：给当前账号门禁回执补齐 PRO / FREE 套餐标记。
- `src/Antigravity-Recovery-Launcher.cs`：原生 GDI 五步卡片、运行态、完成态、真实延迟及模型用时。
- `tests/launcher-ui.test.ps1`：检查源码真实状态与账号检查顺序。
- `tests/capsule-progress.test.ps1`：基于编译后程序集测试状态解释；CI 在 Windows 构建后运行。

**未改动**：多账号实时配额刷新策略、原有节点优选排序与地区优先级、Windows Credential Manager 凭据格式、代理全局设置、自动续接逻辑及打包版本号。国家中立与 RTT 优先的既有排序不一致问题留在后续单独修复，避免同一批 UI 更新修改高风险分流策略。

## 验收指令（Windows）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\launcher-ui.test.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\tests\capsule-progress.test.ps1
```

随后在测试机启动冷启动卡片，观察：
- 先显示账号缓存，之后才开始扫描/测速节点；
- 正式开始测速前不出现伪造的 1/42 进度；
- Google 403/404 只显示端点响应，不能显示为登录成功；
- `agy` 真实生成成功前 AI 状态不标记通过；
- 编辑器与语言服务就绪后才结束启动卡片；
- 热启动和自愈仍能复用现有编辑器，不误杀进程。

运行日志：`%LOCALAPPDATA%\Antigravity\private-proxy\supervisor.log`。
