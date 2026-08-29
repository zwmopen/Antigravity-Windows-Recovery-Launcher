# 发布包

只放可交付成品。大型安装包默认不进 Git，必须在 `manifest.json` 记录：

- 产品版本
- 文件名
- 对应 Git commit/tag
- SHA-256
- 构建日期
- 目标平台
- 已知限制

只有被 `manifest.json` 登记的文件才算正式成品。

