# 踩坑与故障排查 (Troubleshooting Guide)

本文档记录 Antigravity 恢复启动器在真实高频生产环境中沉淀的关键踩坑记录、根因分析、修复方案与防回归原则。

---

## 1. 点击修复导致编辑器闪退与断续重启

- **现象**：用户在写代码时感觉网络卡顿，双击启动器点击修复，正在运行的 Antigravity 编辑器瞬间被杀死闪退，无法丝滑过渡；有时甚至出现短时间内多次反复重启。
- **根因**：
  1. **粗暴杀进程逻辑遗留**：旧版本在接收到前台点击信号时，将其归类为强力修复，调用了 `Stop-ExistingAntigravity`，强制终止了所有名为 `Antigravity` 的主进程；
  2. **日志游标回绕漏洞**：`Antigravity-AccountWatcher.cs` 内部记录语言服务日志偏移量的游标变量在特定异常截断时发生了重置回绕，导致其反复读取历史文件中曾经出现过的 `User location is not supported` 错误，陷入“检测到错误 -> 杀进程自愈 -> 再次回绕 -> 再次杀进程”的死循环。
- **修复**：
  1. **架构彻底重构为无感热接管**：在 `Antigravity-ProxySupervisor.ps1` 中实现 `antigravity_live_seamless_attached`。当检测到 Antigravity 编辑器已在运行时，**绝对不杀进程**，仅在 `127.0.0.1:17897` 代理内部热切换上游专线；按钮全面升级为 **`⚡ 切换最优专线`**；
  2. **修复日志游标逻辑**：在 Watcher 中增加健壮的游标校验与文件长度比对，杜绝循环触发。
- **验证**：自动化运行 `tests/run-failover-policy-tests.ps1` 与 `tests/run-account-watcher-tests.ps1`（14项全绿），实机在编辑器运行状态下双击点击切换专线，编辑器窗口保持常驻置顶，隧道毫秒级静默切换。
- **防回归**：任何前台交互或后台常规自愈均严禁调用 `Stop-ExistingAntigravity`，必须保证编辑器生命周期的连续性。
- **适用版本**：1.0.0+。

---

## 2. 设置面板点开后 1 秒翻页闪现感（英文跳变中文）

- **现象**：打开 Antigravity 设置面板时，界面先显示大约 1 秒钟的英文，然后突然瞬间“翻页”刷新成中文，视觉上有明显的卡顿和撕裂感。
- **根因**：汉化扩展为了防止 React 虚拟列表卡顿，对所有 DOM 变动统一施加了 `80ms` 尾部防抖与最大 `300ms` 等待时间。这导致设置面板首次挂载时，初始英文已被浏览器渲染管线绘制上屏，后续防抖回调触发时才被替换为中文，造成了肉眼可见的时钟延迟。
- **修复**：
  在 `src/localization-extension/content.js` 中引入**微任务前置同步直译机制**：
  1. 通过 `isSettingsSurface()` 精准判定当前变动是否属于设置面板或模态框；
  2. 通过 `isInstantUiNode()` 标记关键短标题、按钮与导航项目；
  3. 命中极速通道的节点在 `MutationObserver` 触发的微任务第一时钟周期内立即执行同步直译，跳过防抖等待，实现“首帧即中文”。
- **验证**：执行 `node tests/localization-extension.test.js` 全部测试通过，实机点击打开设置面板无任何英文闪现。
- **防回归**：极速直译通道仅对设置项与模态框短文本生效，必须严格保护代码编辑器、终端和用户会话内容。
- **适用版本**：1.0.0+。

---

## 3. 跨电脑或非 C 盘安装导致 Clash 订阅无法识别

- **现象**：把启动器打包给另一台电脑，或者用户的 Clash Verge 安装在 D 盘，启动器提示找不到节点。
- **根因**：传统脚本硬编码了 `C:\Program Files\Clash Verge` 或试图从程序运行目录查找配置文件。
- **修复**：
  1. **数据与路径解耦**：从规范的 `%APPDATA%`（如 `io.github.clash-verge-rev.clash-verge-rev\profiles.yaml`）读取订阅索引与缓存，无论软件装在哪个盘，该数据目录永远固定且权威；
  2. **内核三级雷达探测**：不仅搜寻默认路径，还动态穿透系统环境变量 PATH 与 Windows 注册表 `Uninstall` 卸载列表中的 `InstallLocation`，实现 100% 自动定位。
- **适用版本**：1.0.0+。

---

## 4. 专用端口正常但上游节点突然断流 (EOF / Timeout)

- **现象**：`17897` 仍监听、language server 仍有本地连接，但 Google/OAuth 请求超时或返回 `EOF`；同期日常 `7897` 正常。
- **根因**：本地分流和进程链健康，当前专用节点到 Google 的上游线路发生短时断流。
- **修复**：后台每 20 秒检查 Google 与 OAuth；连续 3 次失败才隔离当前候选 20 分钟，从当前活动订阅选择下一条日美候选并无感热切。
- **验证**：`account-watcher.log` 出现连续失败与自愈事件；`failover-state.json` 的 active ID 变化；`7897` 进程、模式和节点不变；编辑器不重启。
- **适用版本**：0.5.1 / 1.0.0+。

---

## 5. 历史地区 400 导致启动时误判

- **现象**：每次双击启动器都重新拉起 17897，界面短暂断开；Google 仍可能返回 `User location is not supported for the API use.`。
- **根因**：旧逻辑只读取语言服务日志最后 400 行，没有区分日志产生时间，把历史错误误当成本次代理故障。
- **修复**：不再用历史地区错误触发代理重启；仅依据专用 Mihomo 的进程归属、配置哈希和当前 Google 连通性修复。
- **验证**：连续启动时应出现 `proxy_reused`，而不是 `proxy_restart_requested_after_location_error`。
- **适用版本**：0.1.2 / 1.0.0+。

---

## 6. 冷启动模型验证卡在“等待 language server”

- **现象**：Google 204 和出口检查已经通过，但每条候选都固定多等 15 秒，随后记录 `model_transport`；整轮没有新的 `agy` 探针日志。
- **根因**：监督器 2.8.3 把“已有 language server 已就绪”当成 AGY 模型探针前置条件。冷启动时 Antigravity 尚未启动，这个条件永远不成立，导致 AGY 还没执行就被误判为传输失败。
- **修复**：2.8.4 不再进行阻塞式等待；若没有现成 language server，记录 `language_server_wait_skipped` 并让官方 `agy` 自行启动/复用其服务。候选临时端口只做网络和出口预检，正式 `17897` 才执行一次真实模型门禁。
- **验证**：应看到 `language_server_wait_skipped` 后紧接 AGY 的真实结果；`OK` 才算通过，400 地区限制、429 额度耗尽、403 账号资格和网络超时分别记录，不互相伪装。
- **防回归**：watchdog 按 `# Version:` 与 golden copy 比较，不扫描隔离探针的局部超时值；`tests/model-gate-cold-start.test.ps1` 和 `tests/watchdog-version-contract.test.ps1` 必须通过。
- **适用版本**：2.8.4 / 1.6.8+。

## 6.1. 客户端地区 400 触发专用端口反复重启

- **现象**：Antigravity 客户端反复出现 `User location is not supported`；日志随后出现 `proxyconnect ... 17897 ... actively refused`，看起来像节点一直坏掉。
- **根因**：旧 Watcher 把每个客户端地区 400 都当成新的代理故障。监督器即使已通过一次正式 `agy` 模型门禁，Watcher 仍会在冷却结束后再次重启 17897；重启窗口本身会主动断开已有连接，制造新的拒绝错误。
- **修复**：Watcher 0.6.0 对地区错误 30 秒合并后只做有界轮换，成功后观察 120 秒；15 分钟内重复恢复达到 2 次，或一次恢复周期耗尽，则暂停地区驱动的自动轮换。Google/OAuth 连续 3 次真实网络失败仍独立恢复。
- **验证**：应看到 `proxy_location_failure_observed` 后出现 `proxy_location_failure_observation_started` 或 `proxy_location_failure_circuit_open`；熔断期间只记录 `proxy_location_failure_suppressed`，不再产生 `health_recovery_started reason=proxy_location_failure`。日常 `7897` 不变。
- **边界**：这不能把 Google 的账号/出口资格限制伪装成网络已修复；最终业务可用仍需客户端新请求产生新的 `ResponseID` 且无新的地区 400。
- **适用版本**：Watcher 0.6.0 / 产品 1.6.8+。

---

## 7. “真源脱节与发布冲刷”惨剧：声称修复未入库导致构建回退旧版本

- **现象**：CHANGELOG 和交接文档声称已经修复了超时 bug（如 1.4.13），但某次重新构建部署后，实机再次爆发一模一样的超时误杀故障，陷入“修好了又坏、坏了又修”的死循环。
- **根因**：
  1. **真源脱节（文档 != 源码）**：此前仅在运行环境（`%LOCALAPPDATA%\Antigravity\launcher`）打了临时热补丁，或 Git 提交时漏掉了 `src/` 的核心修改，导致“声称修复”与“源码实况”严重脱节；
  2. **发布冲刷（旧源码覆盖热修复）**：新一轮构建发布（`build.ps1` $\rightarrow$ `install.ps1`）忠实地从 `src/` 提取旧源码编译，覆盖到实机目录，瞬间冲刷掉热修复，导致旧 bug 原地复活；
  3. **残留混乱**：本地残留大量旧版本 ZIP 与测试中间产物，极易被自动化脚本误用或造成认知偏差。
- **治理与防回归铁律**：
  1. **唯一真源落地（SSOT）**：任何改动第一步必须落在 `src/`，严禁在运行目录打临时补丁冒充最终交付；
  2. **全链路哈希一致性自证**：交付必须验证 `src/`、`releases/current/` 与 `%LOCALAPPDATA%` 实机文件的 SHA-256 哈希 100% 字节级对齐；
  3. **历史版本归档清零**：历史发布物统一由 GitHub Releases 托管归档，本地 `releases/public` 严格只保留当前唯一最新包，杜绝旧版本残留。
- **适用版本**：1.4.15+。

---

## 8. Windows PowerShell 5.1 编码吞噬：无 BOM UTF-8 在中文系统引发 ParserError 导致所有入口全灭

- **现象**：
  1. 自动切号时旧 Antigravity 正常关闭后，新实例迟迟无法启动，守护神日志持续报 `未能获取到新 Antigravity 页面的 WebSocket 调试地址`；
  2. 用户双击桌面的“Antigravity 稳”或“Antigravity 测”，启动器界面闪退或弹出报错，均无法启动应用；
  3. `launcher-error.log` 连续记录语法解析致命错误：
     ```text
     所在位置 ...\Antigravity-ProxySupervisor.ps1:2376 字符: 1
     + }
     + ~
     表达式中缺少紧跟在“}”后的操作数。
     CategoryInfo : ParserError: (:) [], ParentContainsErrorRecordException
     ```
- **根因分析**：
  1. **双入口同一核心架构**：桌面的“Antigravity 稳.lnk”与“Antigravity 测.lnk”底层调用的都是同一个二进制启动器 `Antigravity-Recovery-Launcher.exe`，该启动器在后台通过 Windows 系统自带的 `powershell.exe`（Windows PowerShell 5.1）去执行核心自愈脚本 `Antigravity-ProxySupervisor.ps1`。一旦该脚本发生语法或编码损坏，所有桌面入口连同后台自动切号全军覆没；
  2. **PowerShell 5.1 致命编码陷阱**：在简体中文 Windows（系统默认 ANSI 代码页为 936 / GBK）下，Windows PowerShell 5.1 读取脚本时，如果文件是**无 BOM 的普通 UTF-8**，它**不会**将其识别为 UTF-8，而是强制按系统的 **GBK** 编码进行解码！
  3. **多字节字符吞噬语法符号**：UTF-8 编码下每个中文字符占 3 个字节，而 GBK 每个字符占 2 个字节。当脚本中添加了包含中文的注释或字符串时，由于字节流错位，中文注释末尾的字节与后续代码中的英文冒号、花括号、换行符等发生字节粘连吞噬，导致 PowerShell 5.1 语法解析器把花括号 `{` 或 `}` 吞掉或破坏，最终在随后的某行抛出莫名其妙的 `ParserError: 缺少紧跟在“}”后的操作数` 并在脚本第一行解析阶段就立即暴毙（`exit=1`）。
- **治理与防回归铁律**：
  1. **构建链路强制 BOM 注入与 AST 语法预检**：在 `build.ps1` 中新增 `Copy-WithUtf8BomAndValidate` 门禁。所有 `.ps1` 脚本在构建时必须先通过 PowerShell 官方抽象语法树解析器（`[System.Management.Automation.Language.Parser]::ParseFile`）进行语法预检；预检通过后，一律使用 `New-Object System.Text.UTF8Encoding($true)`（强制带 BOM 的 UTF-8）输出；
  2. **严禁无 BOM 格式入库**：在 Windows PowerShell 5.1 运行环境中，带 BOM 是唯一能够免疫全球各种本地 ANSI 编码吞噬的工业级规范。
- **适用版本**：1.5.1+。
