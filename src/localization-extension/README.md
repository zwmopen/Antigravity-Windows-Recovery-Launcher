# Antigravity 简体中文外部扩展

这是一个无侵入的外部汉化词库与 DOM 运行时，同时保留 Chromium MV3 描述。它只在 Antigravity 的本地 UI 地址上运行，不修改 `app.asar`、预加载脚本、登录态、会话、项目数据或网络请求。

## 工作方式

- 当前 2.11.0 主要由外部 CDP Loader 注入；`--load-extension="localization-extension"` 保留为 Chromium 兼容回退。
- `translation-core.js` 保存可审查的中英词库和纯翻译函数。完整句子与 UI 短词分开；短词不会进入普通描述、技能文本或用户标题。
- 词库吸收公开 Antigravity-Hans 的高价值 Settings、权限、额度、时间、数量和模型文案，但没有复制其启动器或逐节点逐正则扫描实现。
- `content.js` 仅替换 UI 文本节点及常见无障碍属性，并保护虚拟列表对话标题、消息、Markdown、代码、终端、编辑器和输入值。
- `MutationObserver` 捕获 React 动态刷新，80 ms 尾部防抖并设置 300 ms 最大等待，避免高频渲染造成卡顿。
- 输入框内容、可编辑区域、对话消息、Markdown、代码块、终端/编辑器内容默认保护。

如果 Antigravity 改变本地 UI 域名或 Electron 禁止命令行扩展，扩展不会进入页面；原版程序仍可通过英文恢复入口启动。
