# v2.9.26 免责声明/安全须知全自动穿透闭环与模型用量汉化发行版

- **登录与切号安全须知全自动穿透**：
  - 彻底解决新开应用或账号秒切后，界面弹出“安全须知与数据使用”（Security Notice & Data Use）或“服务条款”（Terms of Service）模态弹窗需要人工手动点击“确认并继续”的痛点。
  - 前端语言包扩展（`content.js`）双轨实时监听（MutationObserver + 极速轮询），毫秒级自动勾选许可复选框并模拟物理点击“确认并继续”/“接受并继续”/“开始使用”按钮，实现 100% 零人工干预。
  - 切号守护中枢（`antigravity_smart_switch.py`）在凭据热更新、热重启及 CDP 任务断点续接前，主动通过 CDP 执行安全弹窗穿透，确保后续断点任务无阻碍提交。
  - 严密安全作用域隔离：仅针对安全须知/服务条款/新手向导弹窗生效，绝不误触普通删除、取消、设置等业务交互对话框。
- **模型选择器与用量配额浮窗全量汉化交付**：
  - 模型状态徽标全量汉化：`Notice` ➔ `提示`，`Unavailable` ➔ `不可用`。
  - 配额分类与周期文案汉化：`5h limit` ➔ `5小时额度`。
  - 动态配额与倒计时智能转译：`X% left` ➔ `剩余 X%`，`Resets in Xd Xh` ➔ `X天 X小时后重置`。
  - Radix UI Popper 悬浮层容器全面纳入 UI 作用域白名单，弹窗交互秒级实时转译。
- **全量 82 个技能/插件双语标签与描述标准汉化**：
  - 规范化采用 `skill-id（中文说明）` 标准，全量覆盖 Science、Android、自媒体及工程工具集。
- **发布与安装交付**：
  - 包含独立一键安装程序（`Antigravity-Windows-Recovery-Setup-2.9.26-windows-x64.exe`）与离线压缩包（`Antigravity-Windows-Recovery-Launcher-2.9.26-windows-x64.zip`）。
