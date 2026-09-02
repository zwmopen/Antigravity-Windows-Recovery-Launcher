# Antigravity Windows Recovery Launcher 0.8.0

本版本把桌面启动入口升级为“克制玻璃”中文实时状态窗口，同时保留 0.7.0 已验证的独立代理、真实模型门禁、节点轮换、中文界面和 Cockpit 切号恢复。

## 新增体验

- 显示是否已建立 Antigravity 独立代理 `127.0.0.1:17897`。
- 显示当前电脑实际发现的候选线路数量，不写死节点数。
- 显示 Google/OAuth 连通、当前出口地区和真实模型 `OK` 验证结果。
- 显示中文翻译注入和 Antigravity/语言服务就绪状态。
- 自绘蓝色百分比进度条采用真实阶段上限和连续微进度，减少“卡住”的等待感；失败时给出中文原因。

## 安装

1. 安装并登录官方 Antigravity。
2. 安装 Clash Verge 或 Mihomo Party，并导入自己的合法订阅。
3. 完整解压本 Release ZIP。
4. 双击根目录的 `Install.cmd`。
5. 以后只双击桌面的 `Antigravity 启动器`。

工具不会附带订阅、节点、账号数据、`agy.exe` 或 Mihomo，也不会修改 Clash 的规则模式、系统代理 `7897` 或日常节点。
