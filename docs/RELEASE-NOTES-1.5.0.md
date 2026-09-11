# Antigravity Windows Recovery Launcher v1.5.0 正式稳定版 (Stable Release)

## 核心更新

### 1. 并行门禁淘汰机制 (Parallel Disqualification Gate)
- 对所有备选账号确立一票否决制：只要 gemini_weekly <= 1.0%（周额度见底）或 gemini_5h <= 5.0%（5小时限额耗尽），立即一票否决淘汰，严禁作为切号候选。
- 彻底根治了旧版本将仅剩 0.1%~0.5% 周额度的残血账号误判为有效额度 100% 并强行切换导致连续 429 崩溃死循环的严重隐患。

### 2. 彻底废除盲目 Fallback 兜底
- 彻底移除了选号逻辑中的低额度 fallback 兜底。无真正合格满血账号时，抛出明确异常并由外层门禁安全拦截，绝不降级盲切。

### 3. 全池耗尽 No-Kill 铁律 (No-Kill Rule)
- 当账号池中所有其他备选账号均无可用额度时，系统坚决禁止调用关闭反重力窗口，坚决禁止调用启动器重启。
- 原地保持当前编辑器会话完好运行，发送一条桌面气泡通知，引导用户直接在原窗口从下拉框切换到 Claude 3.7 / Claude 3.5 Sonnet / GPT-4o 等其他模型，工作心流零中断。

### 4. CDP 智能体自动续接引擎升级 (Agent Auto-Resume Engine)
- 适配 Antigravity Agent 智能体模式，新增对 Stop execution 停止执行按钮、Submit 提交按钮的深度识别与状态感知。
- 在派发输入时同步广播原生 InputEvent，确保 React/Lexical 状态机即时绑定，彻底根治此前偶发的 button_not_clickable 导致前排任务漏扣 1 的现象。

### 5. 专线调度与多节点自愈增强
- 遭遇 Google 地区风控（User location is not supported）时，自动触发跨节点高速探测并无感热重载至可用专线（如日本/美国高速线路）。
- 保持 17897 专线独立调度与进程脱壳双星互保。

### 6. 通知降噪收口
- 彻底关闭对【飞书牛马 CLI 私聊】的单聊推送，仅在切换重启成功后向【AI 额度与系统运维群】发送群体战报。

## 验证与稳定性

- 单元测试套件 tests/quota-pool-exhaustion.test.py 全覆盖通过：包含周额度归零短路、并行门禁一票否决淘汰、禁止 fallback 兜底、通知去重与恢复解禁等。
- 源码、构建目录与 %LOCALAPPDATA%\Antigravity\launcher\ 运行副本文件哈希完全一致。
- 经过实机多轮长时间真实并发生成与切号压力测试，定为长期稳定版（Stable Release）。
