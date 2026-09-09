# Antigravity Windows Recovery Launcher v1.4.15 发布说明

## 核心更新

### 1. 1.4.13 声称修复真实落入唯一真源
- **排查定界**：排查证实 1.4.13 CHANGELOG 声称的三处修复（握手超时 8000ms、TLS 预热、Get-MihomoPidSafe）此前未合入 src/，导致构建部署时发生回退。现已在 src/Antigravity-ProxySupervisor.ps1 正式合入；
- **全链路对齐**：src/、eleases/current/ 与 %LOCALAPPDATA%\Antigravity\launcher\ 字节级一致（SHA256: E59FE43B）。

### 2. 本地旧版本残留彻底清零
- 清理本地过时测试构建中间文件，全盘统一收拢至唯一官方真源。

### 3. 全量自动化回归测试
- 包含无感切换、启动时序、33 节点调度、14 项看门狗状态机在内的全套测试 100% PASS。
