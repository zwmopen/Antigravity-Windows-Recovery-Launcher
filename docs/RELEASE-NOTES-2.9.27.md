# Google Antigravity 专线守护与智能切号系统 - v2.9.27 发行说明

> **发布日期**：2026-11-07  
> **版本标号**：v2.9.27 (稳定正式版)  
> **构建产物**：
> - 安装版：`Antigravity-Windows-Recovery-Setup-2.9.27-windows-x64.exe`
> - 便携版：`Antigravity-Windows-Recovery-Launcher-2.9.27-windows-x64.zip`
> - 校验清单：`SHA256SUMS.json`

---

## 🎯 本版本核心亮点与业务解决

### 1. Claude / 第三方单项模型限额隔离保护（防突发黑屏、防误切）
- **痛点根因彻底根除**：
  在之前的版本中，当用户使用 Claude 模型（如 Claude 3.5 Sonnet / 3.7 Sonnet）并将该模型的独立单项额度用尽时，底层语言服务抛出 `RESOURCE_EXHAUSTED (code 429): Individual quota reached`。守护进程盲目识别所有 429 报错，将当前账号误判为“配额彻底见底”，将原本 Gemini 核心额度尚有 100% 满血的宝贵账号强制加入隔离关押名单，并触发强行切号与热重启底层服务，导致前台编辑器界面出现突发黑屏重启、打断会话思路。
- **落实用户终极铁律**：
  > **“Claude 不参与这个 5% 的切号门禁；只要 Gemini 额度（机密零）还在，就算 Claude 归零了也坚决不切！”**
  - 新增 `is_claude_or_individual_model_error` 精准识别单项模型配额耗尽报错（`Individual quota reached`、`Claude`、`Anthropic`、`Sonnet`、`Opus`、`Haiku`、`GPT`、`3p` 等）；
  - **核心双保机制**：当捕获到此类单项限额报错时，系统首先核实当前账号的 Gemini 核心额度（5 小时限额 > 5.0% 且 周限额 > 1.0%）。
  - 若 Gemini 额度充足，**100% 拒绝切号、拒绝关押账号、绝不热重启语言服务**！编辑器主窗口与对话保持持续平稳运行，零黑屏零闪烁，用户可直接在模型菜单无缝切换至 Gemini 极速继续推进任务；
  - 仅当该账号的 Gemini 额度自身也低于警戒线（<= 5%）或全池配额见底时，才触发账号轮转。

### 2. 账号池优选算法平滑增强
- 账号调度优先保障 Gemini 生产力基准与 PRO 账号特权，坚持临期优先（即将周重置的优先消化）与高额度优先；
- Claude 剩余周限额作为同分辅助排序参考，有 Claude 额度优先给到用户，无 Claude 额度绝不影响 Gemini 正式生产。

### 3. 全套回归测试 100% 闭环
- 新增 `test_claude_individual_quota_reached_does_not_switch_when_gemini_healthy` 与 `test_claude_quota_reached_forces_switch_when_gemini_also_exhausted` 针对性测试用例；
- 包含 C# 策略回归、Python 配额门禁、子智能体自愈、多维优选评分在内的 4 大测试体系全部 100% 通过。

---

## 🚀 升级与使用指引

已安装用户无需任何手动操作，后台看门狗与热重载中枢已无感应用最新逻辑。  
如需全新安装或独立分发，可直接下载上方构建产物运行即可。
