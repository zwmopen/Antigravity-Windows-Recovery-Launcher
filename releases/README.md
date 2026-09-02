# 发布包

只放可交付成品。大型安装包默认不进 Git，必须在 `manifest.json` 记录：

- 产品版本
- 文件名
- 对应 Git commit/tag
- SHA-256
- 构建日期
- 目标平台
- 已知限制

0.9.0 有两个正式 Windows x64 成品：推荐单文件 `Setup.exe`（中文向导、可粘贴/浏览安装路径、标准卸载），以及包含 `Install.cmd` 的透明 ZIP 备用包。两者都不携带官方 `agy.exe`、订阅、节点、Token 或日志；首次安装由 `install.ps1` 从官方清单下载并校验 `agy`。

只有被 `manifest.json` 登记的文件才算正式成品。

