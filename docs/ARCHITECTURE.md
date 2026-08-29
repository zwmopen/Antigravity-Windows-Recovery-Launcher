# 架构与数据流

## 系统边界

- 输入：桌面双击、Cockpit 当前账号变化、Antigravity 主进程命令行漂移。
- 输出：一个使用 `127.0.0.1:17897` 的健康 Antigravity 实例及脱敏状态日志。
- 外部依赖：Antigravity 2.11.0、Cockpit Tools、Clash Verge 内置 Mihomo、有效订阅节点。

## 目录和模块

| 路径 | 职责 | 是否权威真源 |
|---|---|---|
| `src/` | 功能源码 | 是 |
| `docs/` | 设计、架构、交接和排障 | 是 |
| `tests/` | 验证代码和验收用例 | 是 |
| `.work/` | 可删除中间产物 | 否 |

## 数据流

```text
桌面 EXE / 后台监控
→ PowerShell 监督器
→ 专用 Mihomo 17897
→ 关闭无代理或黑屏实例
→ 注入代理启动 Antigravity
→ language server 连接验证
→ supervisor-state.json
```

待按实际项目改写。

## 数据与持久化

- 本地数据：`%LOCALAPPDATA%\Antigravity\private-proxy` 中的 PID、状态和脱敏日志。
- 云端数据：无。
- 缓存：Mihomo 运行缓存，可重建。
- 备份和恢复：快捷方式和设置修改前带时间戳备份；不触碰用户会话数据。
- 迁移和兼容：源码使用环境目录解析；Mihomo 路径和目标节点目前仍是本机配置，跨电脑安装前需发现并配置。

## 安全和权限

仅监听回环地址 `127.0.0.1:17897`，不开 TUN、局域网和外部控制接口；日志对密码、Token、UUID、服务器与配置内容脱敏。

