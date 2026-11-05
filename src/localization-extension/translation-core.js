(function (root) {
  'use strict';

  var VERSION = '0.4.6';

  // Full phrases are deliberately separate from exact UI labels. This
  // prevents words such as Settings, On, Model, and Rules from leaking
  // into ordinary descriptions, skill text, or user-authored titles.
  var PHRASE_PAIRS = Object.freeze([
    ["Ask a quick question without interrupting the main conversation.", "提出一个简短问题，不中断当前主对话。"],
    ["Run until the specified goal is completely finished.", "持续执行，直到指定目标全部完成。"],
    ["Compact the conversation now (summarize history to free up the context window).", "立即压缩对话（总结历史，释放上下文空间）。"],
    ["Run a prompt on a routine or one-time schedule.", "按固定周期或单次计划执行提示词。"],
    ["Plan carefully before executing on the user's request.", "先仔细规划，再执行用户请求。"],
    ["Interview me in depth about my idea.", "深入访谈，帮我梳理想法。"],
    ["Invoke a team of agents to autonomously tackle large, parallelizable projects.", "调用智能体团队，协作处理可并行的大型项目。"],
    ["Invoke a browser agent for web tasks.", "调用浏览器智能体处理网页任务。"],
  [
    "See our",
    "请查阅"
  ],
  [
    "See our ",
    "请查阅 "
  ],
  [
    "See our ",
    "请查阅 "
  ],
  [
    "troubleshooting guide",
    "故障排查指南"
  ],
  [
    "for more help.",
    "获取更多帮助。"
  ],
  [
    "Queued Messages",
    "已排队消息"
  ],
  [
    "Queued Message",
    "已排队消息"
  ],
  [
    "Queued",
    "已排队"
  ],
  [
    "Conversation Log",
    "会话记录"
  ],
  [
    "Load older messages",
    "加载更早消息"
  ],
  [
    "Agent terminated due to error",
    "智能体由于异常已终止"
  ],
  [
    "You can prompt the model to try again or start a",
    "您可以提示模型重试或发起"
  ],
  [
    "if the error persists.",
    "如果错误持续存在。"
  ],
  [
    "See our troubleshooting guide for more help.",
    "查看故障排除指南获取更多帮助。"
  ],
  [
    "Queued Messages",
    "已排队消息"
  ],
  [
    "Queued message",
    "已排队消息"
  ],
  [
    "Copy debug info",
    "复制调试信息"
  ],
  [
    "Learn more.",
    "了解更多。"
  ],
  [
    "Learn more about",
    "了解更多关于"
  ],
  [
    "Learn more",
    "了解更多"
  ],
  [
    "Comprehensive guide and reference for the Antigravity Customization System. Use to explain how customizations work, their loading priority, discovery mechanisms, and to guide the creation of skills, rules, plugins, hooks, and MCP servers.",
    "Google Antigravity 自定义系统的全面指南与参考。用于解释自定义项的工作原理、加载优先级、发现机制，并指导技能、规则、插件、钩子及 MCP 服务器的创建。"
  ],
  [
    "Show a floating notification card when background conversations need your input. Answer questions, approve commands, and grant permissions without leaving your current conversation. Share feedback at go/inline-actions-feedback.",
    "当后台对话需要您输入时显示浮动通知卡片。无需离开当前对话即可回答问题、批准命令和授予权限。可在 go/inline-actions-feedback 分享反馈。"
  ],
  [
    "When toggled on, Antigravity IDE will use your AI credits to fulfill model requests once you\\'re out of model quota. Antigravity IDE will always use your model quota first before using AI credits.",
    "开启后，当模型额度用完时，Antigravity IDE 将使用 AI 积分完成模型请求。Antigravity IDE 始终会先使用模型额度，再使用 AI 积分。"
  ],
  [
    "When toggled on, Antigravity IDE will use your AI credits to fulfill model requests once you're out of model quota. Antigravity IDE will always use your model quota first before using AI credits.",
    "开启后，当模型额度用完时，Antigravity IDE 将使用 AI 积分完成模型请求。Antigravity IDE 始终会先使用模型额度，再使用 AI 积分。"
  ],
  [
    "When toggled on, Antigravity will use your AI credits to fulfill model requests once you\\'re out of model quota. Antigravity will always use your model quota first before using AI credits.",
    "开启后，当模型额度用完时，Antigravity 将使用 AI 积分完成模型请求。Antigravity 始终会先使用模型额度，再使用 AI 积分。"
  ],
  [
    "Agent asks for permission before executing commands matched by a deny list entry. The deny list follows the same matching rules as the allow list and takes precedence over the allow list.",
    "在执行与拒绝列表条目匹配的命令前，智能体会先请求权限。拒绝列表遵循与允许列表相同的匹配规则，且优先级高于允许列表。"
  ],
  [
    "When toggled on, Antigravity will use your AI credits to fulfill model requests once you're out of model quota. Antigravity will always use your model quota first before using AI credits.",
    "开启后，当模型额度用完时，Antigravity 将使用 AI 积分完成模型请求。Antigravity 始终会先使用模型额度，再使用 AI 积分。"
  ],
  [
    "View your available model quota and AI credits. Model quota refreshes periodically based on your plan. Enable AI Credit Overages to continue using models when your quota is exhausted.",
    "查看可用的模型额度和 AI 积分。模型额度会根据你的套餐定期刷新。启用 AI 积分超额使用后，可在额度耗尽时继续使用模型。"
  ],
  [
    "The breakdown below shows token usage from customizations like skills, rules, and MCP. If the budget is exceeded, large customizations will be truncated automatically.",
    "下面的明细展示技能、规则和 MCP 等自定义内容的 Token 使用量。如果超出预算，较大的自定义内容会被自动截断。"
  ],
  [
    "Allow Tab to view and edit the files in .gitignore. Use with caution if your .gitignore lists files containing credentials, secrets, or other sensitive information.",
    "允许 Tab 键查看和编辑 .gitignore 中的文件。如果您的 .gitignore 列出了包含凭据、机密或其他敏感信息的文件，请谨慎使用。"
  ],
  [
    "Orchestrates Android development tasks including project creation, deployment, SDK management, and environment diagnostics using the `android` command-line tool.",
    "使用 android 命令行工具协调 Android 开发任务，包括项目创建、部署、SDK 管理和环境诊断。"
  ],
  [
    "Configure the browser subagent. It requires Google Chrome to be installed. The browser subagent can be invoked by typing /browser in the conversation input box.",
    "配置浏览器子智能体。它需要安装 Google Chrome。你可以在对话输入框中输入 /browser 来调用浏览器子智能体。"
  ],
  [
    "Please describe the issue in detail. The more actionable your feedback, the quicker our team can address your request. Some helpful information includes:",
    "请详细描述问题。您的反馈越具体，我们的团队就能越快处理您的请求。一些有用的信息包括："
  ],
  [
    "When enabled, the agent will be able to access its knowledge base to inform its responses and automatically generate knowledge items in the background.",
    "启用后，智能体将能够访问其知识库以辅助生成回复，并在后台自动生成知识项。"
  ],
  [
    "Automatically prompt you to restart the app when a new update is available. When disabled, you can check for updates manually from the app menu.",
    "当有新版本可用时，自动提示您重启应用。禁用后，您可以从应用菜单中手动检查更新。"
  ],
  [
    "Changes the base URL for marketplace search results. You must restart Antigravity IDE to use the new marketplace after changing this value.",
    "更改插件市场搜索结果的基准 URL。更改此值后，您必须重启 Antigravity IDE 才能使用新的插件市场。"
  ],
  [
    "Specifies Agent\\'s behavior when asking for review on artifacts, which are documents it creates to enable a richer conversation experience.",
    "指定智能体在请求审核产物时的行为。产物是智能体创建的文档，用于提供更丰富的对话体验。"
  ],
  [
    "Specifies Agent's behavior when asking for review on artifacts, which are documents it creates to enable a richer conversation experience.",
    "指定智能体在请求审核产物时的行为。产物是智能体创建的文档，用于提供更丰富的对话体验。"
  ],
  [
    "Note: A change to this setting will only apply to new messages sent to Agent. In-progress responses will use the previous setting value.",
    "注意：对此设置的更改将仅适用于发送给智能体的新消息。正在进行的回复将使用之前的设置值。"
  ],
  [
    "Changes the base URL for marketplace search results. You must restart Antigravity to use the new marketplace after changing this value.",
    "更改插件市场搜索结果的基准 URL。更改此值后，您必须重启 Antigravity 才能使用新的插件市场。"
  ],
  [
    "Changes the base URL on each extension page. You must restart Antigravity IDE to use the new marketplace after changing this value.",
    "更改每个插件页面的基准 URL。更改此值后，您必须重启 Antigravity IDE 才能使用新的插件市场。"
  ],
  [
    "Changes the base URL on each extension page. You must restart Antigravity to use the new marketplace after changing this value.",
    "更改每个插件页面的基准 URL。更改此值后，您必须重启 Antigravity 才能使用新的插件市场。"
  ],
  [
    "When enabled, Agent is given awareness of lint errors created by its edits and may fix them without explicit user prompting.",
    "启用后，智能体将感知到其编辑所导致的 Lint 错误，并可在不明确提示用户的情况下进行修复。"
  ],
  [
    "Choose a predefined security preset for the agent. This controls terminal auto-execution policy, and file access policy.",
    "为智能体选择预设安全策略。它会控制终端自动执行策略和文件访问策略。"
  ],
  [
    "Custom path for the browser user profile directory. Leave empty for default (~/.gemini/antigravity-browser-profile).",
    "浏览器用户资料目录的自定义路径。留空则使用默认路径（~/.gemini/antigravity-browser-profile）。"
  ],
  [
    "You currently don\\'t have any MCP Servers installed. Add an MCP server above or add a custom one via the MCP Config.",
    "您当前还没有安装任何 MCP 服务器。请在上方添加 MCP 服务器，或通过 MCP 配置文件添加自定义服务器。"
  ],
  [
    "When enabled, \\'Explain and Fix\\' actions will continue in the current conversation instead of starting a new one.",
    "启用后，“解释并修复”操作将在当前对话中继续，而不是开始新对话。"
  ],
  [
    "The app will be accessible from the menu bar and will keep running in the background when all windows are closed.",
    "应用可从菜单栏访问，并会在所有窗口关闭后继续在后台运行。"
  ],
  [
    "Reliable automation, in-depth debugging, and performance analysis in Chrome using Chrome DevTools and Puppeteer",
    "使用 Chrome DevTools 和 Puppeteer 在 Chrome 中进行可靠的自动化、深度调试和性能分析"
  ],
  [
    "We recommend attaching logs. Attaching logs will help the Antigravity team act on and prioritize your feedback.",
    "我们建议附上日志。附上日志将有助于 Antigravity 团队处理并优先解决您的反馈。"
  ],
  [
    "When enabled, the Changes Overview toolbar will automatically expand when Agent finishes generating a response.",
    "启用后，Changes Overview 工具栏将在智能体完成回复生成时自动展开。"
  ],
  [
    "Projects serve as your workspace where your agents work. Each project has its own file scope and permissions. ",
    "项目是智能体工作的工作区。每个项目都有自己的文件范围和权限。"
  ],
  [
    "Agents run in a secure sandbox that restricts access to external resources outside of your trusted folders.",
    "智能体会在安全沙盒中运行，限制其访问受信任文件夹之外的外部资源。"
  ],
  [
    "Prototype, build & run modern apps users love with Firebase\\'s backend, AI, and operational infrastructure.",
    "利用 Firebase 的后端、AI 和运营基础设施，原型设计、构建和运行深受用户喜爱的现代应用。"
  ],
  [
    "Terminal commands always require review and the agent cannot access files outside of its given workspaces.",
    "终端命令始终需要审核，且智能体无法访问其给定工作区之外的文件。"
  ],
  [
    "Developer-only tools. These settings are stored locally in this browser and do not affect other users.",
    "仅限开发者工具。这些设置保存在当前浏览器本地，不会影响其他用户。"
  ],
  [
    "to be installed. The browser subagent can be invoked by typing /browser in the conversation input box.",
    "安装 Google Chrome。您可以在对话输入框中输入 /browser 来调用浏览器子智能体。"
  ],
  [
    "When enabled, Agent will use IDE\\'s shell integration to detect and report terminal command execution.",
    "启用后，智能体将使用 IDE 的 Shell 集成来检测并报告终端命令的执行。"
  ],
  [
    "When enabled, Agent will show browser notifications when user action is needed or execution finishes.",
    "启用后，当需要用户操作或执行完成时，智能体将显示浏览器通知。"
  ],
  [
    "When toggled on, Antigravity IDE collects usage data to help Google enhance performance and features.",
    "开启后，Antigravity IDE 将收集使用数据，以帮助 Google 提升性能和功能。"
  ],
  [
    "Keep the app accessible from the menu bar and running in the background when all windows are closed.",
    "在所有窗口关闭后，保持应用可从菜单栏访问并在后台继续运行。"
  ],
  [
    "Modify scoped permissions, folders, and agent settings like Sandbox and Terminal Command Execution.",
    "修改作用域权限、文件夹，以及沙盒和终端命令执行等智能体设置。"
  ],
  [
    "Requires manual review for all terminal commands and file accesses outside of the working folders.",
    "对于所有工作文件夹之外的终端命令和文件访问，都需要手动审核。"
  ],
  [
    "When toggled on, Antigravity collects usage data to help Google enhance performance and features.",
    "开启后，Antigravity 会收集使用数据，帮助 Google 改进性能和功能。"
  ],
  [
    "Select one of the three options. Agent settings and permissions can be further customized below.",
    "选择以下三个选项之一。智能体设置和权限可在下方进一步自定义。"
  ],
  [
    "All terminal commands require review. The agent can read or write to any file in the machine.",
    "所有终端命令均需要审核。智能体可以读取或写入电脑上的任何文件。"
  ],
  [
    "Confirm the command is safe to run outside of the sandbox with full network and disk access.",
    "确认该命令可在沙盒外 safe 运行，并拥有完整网络和磁盘访问权限。"
  ],
  [
    "Port number for Chrome DevTools Protocol remote debugging. Leave empty for default (9222).",
    "Chrome DevTools Protocol 远程调试端口号。留空则使用默认值（9222）。"
  ],
  [
    "When enabled, the agent will be able to access past conversations to inform its responses.",
    "启用后，智能体将能够访问历史对话以辅助其生成回复。"
  ],
  [
    "Controls whether the agent can run custom JavaScript to automate complex browser actions.",
    "控制智能体是否可以运行自定义 JavaScript 来自动化复杂浏览器操作。"
  ],
  [
    "When enabled, Antigravity will play a sound when Agent finishes generating a response.",
    "启用后，Antigravity 会在智能体完成回复生成时播放提示音。"
  ],
  [
    "The browser subagent can be invoked by typing /browser in the conversation input box.",
    "可以在对话输入框中输入 /browser 来调用浏览器子智能体。"
  ],
  [
    "Receive product updates, tips, and promotions from Google Antigravity IDE via email.",
    "通过电子邮件接收来自 Google Antigravity IDE 的产品更新、技巧和促销活动。"
  ],
  [
    "Predict the location of your next edit and navigates you there with a tab keypress.",
    "预测您下一次编辑的位置，并在按下 Tab 键时导航至该处。"
  ],
  [
    "To modify notification settings, open your operating system\\'s system preferences.",
    "要修改通知设置，请打开操作系统的系统设置。"
  ],
  [
    "To modify notification settings, open your operating system's system preferences.",
    "要修改通知设置，请打开操作系统的系统设置。"
  ],
  [
    "Receive product updates, tips, and promotions from Google Antigravity via email.",
    "通过电子邮件接收 Google Antigravity 的产品更新、技巧和促销信息。"
  ],
  [
    "Configures how the agent tries to access files outside of its working folders.",
    "配置智能体如何访问工作文件夹之外的文件。"
  ],
  [
    "You can upgrade to a Google AI Ultra plan to receive the highest rate limits.",
    "你可以升级到 Google AI Ultra 套餐以获得最高速率限制。"
  ],
  [
    "Use Add MCP to browse the store, or add a custom server via the MCP config.",
    "使用“添加 MCP”浏览商店，或通过 MCP 配置文件添加自定义服务器。"
  ],
  [
    "Google3 chats will be regrouped into their workspaces in the sidebar. See",
    "Google3 聊天将在侧边栏中重新按其工作区分组。请参阅"
  ],
  [
    "Controls whether terminal commands require your approval before running.",
    "控制终端命令运行前是否需要你的批准。"
  ],
  [
    "Model must be available on the Gemini API and use the gemini-api scheme.",
    "模型必须可在 Gemini API 中使用，并使用 gemini-api 模式。"
  ],
  [
    "options. Agent settings and permissions can be further customized below.",
    "项之一。智能体设置和权限可在下方进一步自定义。"
  ],
  [
    "You can upgrade to a Google AI Ultra plan to receive higher rate limits.",
    "你可以升级到 Google AI Ultra 套餐以获得更高的速率限制。"
  ],
  [
    "Path to the Chrome/Chromium executable. Leave empty for auto-detection.",
    "Chrome/Chromium 可执行文件路径。留空则自动检测。"
  ],
  [
    "VCS used when generating a new workspace based off your initial prompt.",
    "根据您的初始提示词生成新工作区时使用的 VCS。"
  ],
  [
    "Inherits from global settings. Local permissions have higher priority.",
    "继承全局设置。本地权限优先级更高。"
  ],
  [
    "Jetski Chat configuration is not available in the current environment.",
    "当前环境中无法使用 Jetski Chat 配置。"
  ],
  [
    "Open in current window, Continue conversation in the current workspace",
    "在当前窗口打开，并在当前工作区继续对话"
  ],
  [
    "Agent settings and permissions for conversations outside of projects.",
    "为项目外对话配置智能体设置和权限。"
  ],
  [
    "Configure a chat bot so you can use Jetski directly from Google Chat.",
    "配置聊天机器人，以便直接从 Google Chat 使用 Jetski。"
  ],
  [
    "Google3 chats will be regrouped into their workspaces in the sidebar.",
    "Google3 聊天将在侧边栏中重新按其工作区分组。"
  ],
  [
    "Keep your coding agent up to date with the latest web best practices.",
    "让您的编码智能体始终与最新的 Web 最佳实践保持同步。"
  ],
  [
    "Configure agent execution, queued message delivery, and permissions.",
    "配置智能体执行、排队消息发送以及权限。"
  ],
  [
    "Allows the agent to access files outside of your current workspace.",
    "允许智能体访问当前工作区之外的文件。"
  ],
  [
    "External tools the agent can invoke via the Model Context Protocol.",
    "智能体可通过模型上下文协议 (MCP) 调用的外部工具。"
  ],
  [
    "To modify editor settings, open Settings within the editor window.",
    "要修改编辑器设置，请在编辑器窗口中打开设置。"
  ],
  [
    "Show \"Edit\" and \"Chat\" buttons when selecting text in the editor.",
    "在编辑器中选择文本时显示“编辑”和“聊天”按钮。"
  ],
  [
    "Add an MCP server above or add a custom one via the MCP Config.",
    "在上方添加 MCP 服务器，或通过 MCP 配置添加自定义服务器。"
  ],
  [
    "Agent settings and permissions can be further customized below.",
    "智能体设置和权限可在下方进一步自定义。"
  ],
  [
    "Agents have full access to your machine and external resources.",
    "智能体可完整访问你的电脑和外部资源。"
  ],
  [
    "Allow/deny agent write access to specific files or directories.",
    "允许或拒绝智能体写入指定文件或目录。"
  ],
  [
    "Configure allowed and denied URLs for browser action execution.",
    "配置允许和拒绝浏览器执行操作的 URL。"
  ],
  [
    "Configure tab completion, suggestions, and navigation behavior.",
    "配置 Tab 补全、建议和导航行为。"
  ],
  [
    "Highlight newly inserted text after accepting a Tab completion.",
    "在接受 Tab 补全后高亮显示新插入的文本。"
  ],
  [
    "Manage settings specific to Google CitC workspaces development.",
    "管理特定于 Google CitC 工作区开发的设置。"
  ],
  [
    "Allow/deny agent read access to specific files or directories.",
    "允许或拒绝智能体读取指定文件或目录。"
  ],
  [
    "Browse and enable plugins from the Build With Google catalog.",
    "从 Build With Google 目录中浏览并启用插件。"
  ],
  [
    "Configure allowed and denied paths for file reads and writes.",
    "配置允许和拒绝读写的文件路径。"
  ],
  [
    "External tools the agent can call via Model Context Protocol.",
    "智能体可通过 Model Context Protocol 调用的外部工具。"
  ],
  [
    "The agent will wait for you to install the browser extension.",
    "智能体会等待你安装浏览器扩展。"
  ],
  [
    "This migration may mess up your settings, chats, and sidebar.",
    "此迁移可能会影响您的设置、聊天记录和侧边栏。"
  ],
  [
    "Configure the agent\\'s visual theme and display preferences.",
    "配置智能体的视觉主题与显示偏好。"
  ],
  [
    "Prevent the computer from sleeping while the app is running.",
    "应用运行时防止电脑进入睡眠。"
  ],
  [
    "Allow/deny agent browser actuation access to specific URLs.",
    "允许或拒绝智能体对指定 URL 执行浏览器操作。"
  ],
  [
    "Configure the agent's visual theme and display preferences.",
    "配置智能体的视觉主题与显示偏好。"
  ],
  [
    "Manage how Best of N sets up the workspace its arms run in.",
    "管理 Best of N 如何配置其各分支运行所在的工作区。"
  ],
  [
    "Open files in the background if Agent creates or edits them",
    "当智能体创建或编辑文件时，在后台打开这些文件"
  ],
  [
    "Restricts agent tools to a secure, isolated local sandbox.",
    "将智能体工具限制在安全隔离的本地沙盒中。"
  ],
  [
    "Allow/deny agent read access to specific URLs or domains.",
    "允许或拒绝智能体读取指定 URL 或域名。"
  ],
  [
    "Configure global allowed and denied resource permissions.",
    "配置全局允许和拒绝的资源权限。"
  ],
  [
    "Configure allowed and denied URLs for browser actuation.",
    "配置允许和拒绝浏览器执行操作的 URL。"
  ],
  [
    "Allow/deny agent command execution outside the sandbox.",
    "允许或拒绝智能体在沙盒外执行命令。"
  ],
  [
    "Manage your plan, credentials, and general preferences.",
    "管理你的套餐、凭据和通用偏好设置。"
  ],
  [
    "Allow full browser script execution without prompting.",
    "允许完整的浏览器脚本执行而无需提示。"
  ],
  [
    "Configure the maximum width of the conversation panel.",
    "配置对话面板的最大宽度。"
  ],
  [
    "Sidebar after conversations are regrouped by workspace",
    "按工作区分组后的对话侧边栏"
  ],
  [
    "URLs the agent can perform actions on via the browser.",
    "智能体可以通过浏览器执行操作的 URL。"
  ],
  [
    "Configure default behaviors, skills, and MCP servers.",
    "配置默认行为、技能和 MCP 服务器。"
  ],
  [
    "Configure external tools via Model Context Protocol.",
    "配置通过模型上下文协议 (MCP) 使用的外部工具。"
  ],
  [
    "Keyboard shortcuts for quick navigation and control.",
    "用于快速导航和控制的键盘快捷键。"
  ],
  [
    "You currently don\\'t have any MCP Servers installed.",
    "您当前还没有安装任何 MCP 服务器。"
  ],
  [
    "Prompt for approval before running browser scripts.",
    "运行浏览器脚本前请求批准。"
  ],
  [
    "Quickly add and update imports with a tab keypress.",
    "按下 Tab 键快速添加和更新导入。"
  ],
  [
    "Search for MCP servers to add to your configuration",
    "搜索要添加到配置中的 MCP 服务器"
  ],
  [
    "Using the Antigravity Python SDK to build AI agents",
    "使用 Antigravity Python SDK 构建 AI 智能体"
  ],
  [
    "Configure editor-specific behaviors and shortcuts.",
    "配置编辑器特有的行为和快捷键。"
  ],
  [
    "New standalone conversation, outside of projects.",
    "新建独立对话，不属于任何项目。"
  ],
  [
    "Require review for all browser script execution.",
    "所有浏览器脚本执行都需要审核。"
  ],
  [
    "URLs the agent can actuate on using the browser.",
    "智能体可通过浏览器执行操作的 URL。"
  ],
  [
    "Commands the agent can run outside the sandbox.",
    "智能体可在沙盒外运行的命令。"
  ],
  [
    "Configure allowed commands outside the sandbox.",
    "配置允许在沙箱外运行的命令。"
  ],
  [
    "Curated collection of agent skills for science.",
    "为科学领域精心挑选的智能体技能集合。"
  ],
  [
    "Select light, dark, or inherit system settings.",
    "选择浅色、深色或继承系统设置。"
  ],
  [
    "URLs the agent can read or open in the browser.",
    "智能体可以在浏览器中读取或打开的 URL。"
  ],
  [
    "Configure allowed and denied URLs for reading.",
    "配置允许和拒绝读取的 URL。"
  ],
  [
    "Continue conversation in the current workspace",
    "在当前工作区继续对话"
  ],
  [
    "Agent needs permission to execute JavaScript",
    "智能体需要权限才能执行 JavaScript"
  ],
  [
    "Conversation copied as Markdown to clipboard",
    "对话已作为 Markdown 复制到剪贴板"
  ],
  [
    "Quickly add and update imports with Tab key.",
    "按下 Tab 键快速添加和更新导入。"
  ],
  [
    "Search conversations (by name or Cascade ID)",
    "搜索对话（按名称或 Cascade ID）"
  ],
  [
    "% of the customization budget is available.",
    "% 的自定义预算可用。"
  ],
  [
    "Configure the browser subagent. It requires",
    "配置浏览器子智能体。它需要"
  ],
  [
    "Configure when follow-up messages are sent.",
    "配置后续消息的发送时机。"
  ],
  [
    "No customizations found for this workspace.",
    "此工作区没有找到自定义内容。"
  ],
  [
    "Work with local agents from another device.",
    "从其他设备连接并使用本地智能体。"
  ],
  [
    "Antigravity would like to use the browser.",
    "Antigravity 想要使用浏览器。"
  ],
  [
    "Folder no longer exists or is unavailable.",
    "文件夹不再存在或不可用。"
  ],
  [
    "Show suggestions when typing in the editor",
    "在编辑器中输入时显示建议"
  ],
  [
    "Allow Tab to access .gitignore exclusions",
    "Tab 键访问 .gitignore 排除文件"
  ],
  [
    "Ask anything, @ to mention, / for actions",
    "想问什么都可以，@ 引用，/ 执行动作"
  ],
  [
    "Interrupt the agent and send immediately.",
    "打断智能体并立即发送。"
  ],
  [
    "Configure AI models and view your quota.",
    "配置 AI 模型并查看额度。"
  ],
  [
    "Terminal commands the agent can execute.",
    "智能体可执行的终端命令。"
  ],
  [
    "Block all browser JavaScript execution.",
    "阻止所有浏览器 JavaScript 执行。"
  ],
  [
    "Explain and Fix in Current Conversation",
    "在当前对话中解释并修复"
  ],
  [
    "GCP Project ID for enterprise features.",
    "适用于企业级功能的 GCP 项目 ID。"
  ],
  [
    "Local permissions have higher priority.",
    "本地权限优先级更高。"
  ],
  [
    "Manually customize individual settings.",
    "手动自定义各项设置。"
  ],
  [
    "Allow/deny specific terminal commands.",
    "允许或拒绝指定终端命令。"
  ],
  [
    "No (tell the agent what to do instead)",
    "否（告诉智能体改做什么）"
  ],
  [
    "Manage your notification preferences.",
    "管理您的通知偏好设置。"
  ],
  [
    "Outside of folders file access policy",
    "文件夹外访问策略"
  ],
  [
    "Select where to open the conversation",
    "选择在哪里打开对话"
  ],
  [
    "Configure allowed terminal commands.",
    "配置允许的终端命令。"
  ],
  [
    "Manage your model quota and credits.",
    "管理你的模型额度与积分。"
  ],
  [
    "(tell the agent what to do instead)",
    "（告诉智能体改做什么）"
  ],
  [
    "Browser Javascript Execution Policy",
    "浏览器 JavaScript 执行策略"
  ],
  [
    "Enter command (e.g., git, blaze)...",
    "输入命令（例如 git、blaze）..."
  ],
  [
    "Loading workspace customizations...",
    "正在加载工作区自定义项..."
  ],
  [
    "Queue until after the current turn.",
    "排队直到当前轮次结束后发送。"
  ],
  [
    "Set how fast Tab suggestions appear",
    "设置 Tab 建议的显示速度"
  ],
  [
    "Build with Antigravity IDE Plugins",
    "使用 Antigravity IDE 插件构建"
  ],
  [
    "Search for files in the project...",
    "在项目中搜索文件..."
  ],
  [
    "Initializing virtual environments",
    "正在初始化虚拟环境"
  ],
  [
    "Open Agent panel on window reload",
    "窗口重新加载时打开智能体面板"
  ],
  [
    "Manage Antigravity app settings.",
    "管理 Antigravity 应用设置。"
  ],
  [
    "Select one of the three options.",
    "选择以下三个选项之一。"
  ],
  [
    "Set the speed of tab suggestions",
    "设置 Tab 建议的显示速度"
  ],
  [
    "Agent Non-Workspace File Access",
    "智能体非工作区文件访问"
  ],
  [
    "Enter file or directory path...",
    "输入文件或目录路径..."
  ],
  [
    "Search by name or Cascade ID...",
    "按名称或 Cascade ID 搜索..."
  ],
  [
    "Terminal Command Auto Execution",
    "终端命令自动执行"
  ],
  [
    "Enable notifications for Agent",
    "为智能体启用通知"
  ],
  [
    "Getting started with a Project",
    "开始使用项目"
  ],
  [
    "Refresh quota and credits data",
    "刷新额度和积分数据"
  ],
  [
    "Terminal & Tooling Permissions",
    "终端与工具权限"
  ],
  [
    "Enable Sandbox Mode (Preview)",
    "启用沙盒模式（预览）"
  ],
  [
    "New Conversation in Workspace",
    "在工作区中新建对话"
  ],
  [
    "Allow List Terminal Commands",
    "终端命令允许列表"
  ],
  [
    "Manage application settings.",
    "管理应用设置。"
  ],
  [
    "Select Model to Send Message",
    "选择用于发送消息的模型"
  ],
  [
    "Allow running this command?",
    "允许运行此命令？"
  ],
  [
    "Confirm Browser Interaction",
    "确认浏览器交互"
  ],
  [
    "Deny List Terminal Commands",
    "终端命令拒绝列表"
  ],
  [
    "Enter avatar URL (optional)",
    "输入头像 URL（可选）"
  ],
  [
    "Generate CitC Workspace VCS",
    "生成 CitC 工作区 VCS"
  ],
  [
    "New Conversation in Project",
    "在项目中新建对话"
  ],
  [
    "Paths the agent can modify.",
    "智能体可修改的路径。"
  ],
  [
    "Agent Auto-Fix Lint Errors",
    "智能体自动修复 Lint 错误"
  ],
  [
    "Click to copy full command",
    "点击复制完整命令"
  ],
  [
    "Copy conversation markdown",
    "复制对话 Markdown"
  ],
  [
    "Copy full URL to clipboard",
    "复制完整 URL 到剪贴板"
  ],
  [
    "Search MCP servers by name",
    "按名称搜索 MCP 服务器"
  ],
  [
    "Archive this conversation",
    "归档此对话"
  ],
  [
    "Browser User Profile Path",
    "浏览器用户资料路径"
  ],
  [
    "Build With Google Plugins",
    "使用 Google 插件构建"
  ],
  [
    "Built with Google Plugins",
    "使用 Google 插件构建"
  ],
  [
    "Enable AI Credit Overages",
    "启用 AI 积分超额使用"
  ],
  [
    "Five Hour Limit Remaining",
    "剩余 5 小时限额"
  ],
  [
    "Open Conversation History",
    "打开对话历史"
  ],
  [
    "Paths the agent can read.",
    "智能体可读取的路径。"
  ],
  [
    "Project validation failed",
    "项目验证失败"
  ],
  [
    "Project-Specific Settings",
    "项目专属设置"
  ],
  [
    "Select Python Interpreter",
    "选择 Python 解释器"
  ],
  [
    "Toggle Agent (Ctrl+Alt+B)",
    "切换智能体 (Ctrl+Alt+B)"
  ],
  [
    "Commands Outside Sandbox",
    "沙盒外命令"
  ],
  [
    "Editor-Specific Settings",
    "编辑器专属设置"
  ],
  [
    "Import AI Studio Project",
    "导入 AI Studio 项目"
  ],
  [
    "Launching the browser...",
    "正在启动浏览器..."
  ],
  [
    "No MCP servers installed",
    "未安装 MCP 服务器"
  ],
  [
    "Open Conversation Picker",
    "打开对话选择器"
  ],
  [
    "Project name. E.g. Tasks",
    "项目名称，例如 Tasks"
  ],
  [
    "Workspace Command Access",
    "工作区命令访问"
  ],
  [
    "Your Plan: Google AI Pro",
    "你的套餐：Google AI Pro"
  ],
  [
    "Advanced Command Access",
    "高级命令访问"
  ],
  [
    "Automatic update checks",
    "自动检查更新"
  ],
  [
    "Browser Actuation Rules",
    "浏览器操作规则"
  ],
  [
    "Deny setting up browser",
    "拒绝设置浏览器"
  ],
  [
    "Edit Conversation Title",
    "编辑对话标题"
  ],
  [
    "Enable Sounds for Agent",
    "启用智能体提示音"
  ],
  [
    "Marketplace Gallery URL",
    "插件市场列表 URL"
  ],
  [
    "Open Keyboard Shortcuts",
    "打开键盘快捷键"
  ],
  [
    "Open System Preferences",
    "打开系统设置"
  ],
  [
    "Open Workspace Selector",
    "打开工作区选择器"
  ],
  [
    "Queued Message Delivery",
    "排队消息发送"
  ],
  [
    "Search conversations...",
    "搜索对话..."
  ],
  [
    "Standalone Conversation",
    "独立对话"
  ],
  [
    "Artifact Review Policy",
    "产物审核策略"
  ],
  [
    "Auto-Open Edited Files",
    "自动打开已编辑文件"
  ],
  [
    "Background Task Output",
    "后台任务输出"
  ],
  [
    "Edit permission target",
    "编辑权限目标"
  ],
  [
    "Highlight After Accept",
    "接受后高亮"
  ],
  [
    "Loading MCP servers...",
    "正在加载 MCP 服务器..."
  ],
  [
    "Loading token usage...",
    "正在加载 Token 用量..."
  ],
  [
    "Marketplace Search URL",
    "插件市场列表 URL"
  ],
  [
    "Model Context Protocol",
    "模型上下文协议 (MCP)"
  ],
  [
    "My Custom Gemini Model",
    "我的自定义 Gemini 模型"
  ],
  [
    "No more older messages",
    "没有更早的消息了"
  ],
  [
    "Open Browser (Preview)",
    "打开浏览器 (预览)"
  ],
  [
    "Opening URL in Browser",
    "正在浏览器中打开 URL"
  ],
  [
    "quota and credits data",
    "额度和积分数据"
  ],
  [
    "Search across files...",
    "跨文件搜索..."
  ],
  [
    "Show Selection Actions",
    "显示选择操作"
  ],
  [
    "Toggle Developer Tools",
    "切换开发者工具"
  ],
  [
    "Weekly Limit Remaining",
    "剩余周额度"
  ],
  [
    "Actuation Permissions",
    "操作权限"
  ],
  [
    "Allow in Conversation",
    "在本次对话中允许"
  ],
  [
    "Claude and GPT models",
    "Claude 和 GPT 模型"
  ],
  [
    "Installed MCP Servers",
    "已安装的 MCP 服务器"
  ],
  [
    "Model quota exhausted",
    "模型额度已耗尽"
  ],
  [
    "Notification Settings",
    "通知设置"
  ],
  [
    "Open project settings",
    "打开项目设置"
  ],
  [
    "Opened URL in Browser",
    "已在浏览器中打开 URL"
  ],
  [
    "Suggestions in Editor",
    "编辑器内联建议"
  ],
  [
    "Toggle Model Selector",
    "切换模型选择器"
  ],
  [
    "Workspace File Access",
    "工作区文件访问"
  ],
  [
    "[Dev] GCP Project ID",
    "[开发] GCP 项目 ID"
  ],
  [
    "Advanced File Access",
    "高级文件访问"
  ],
  [
    "Agent Auto-Fix Lints",
    "智能体自动修复 Lint 错误"
  ],
  [
    "Archive Conversation",
    "归档对话"
  ],
  [
    "Conversation History",
    "对话历史"
  ],
  [
    "Enable Browser Tools",
    "启用浏览器工具"
  ],
  [
    "Enter URL pattern...",
    "输入 URL 匹配模式..."
  ],
  [
    "Marketplace Item URL",
    "插件市场单项 URL"
  ],
  [
    "Network Access Rules",
    "网络访问规则"
  ],
  [
    "No conversations yet",
    "暂无对话"
  ],
  [
    "Open Agent on Reload",
    "重新加载时打开智能体"
  ],
  [
    "Open Command Palette",
    "打开命令面板"
  ],
  [
    "Pinned Conversations",
    "已固定对话"
  ],
  [
    "Restore Conversation",
    "恢复对话"
  ],
  [
    "Search all convos...",
    "搜索全部对话..."
  ],
  [
    "Tab Gitignore Access",
    "Tab 键访问 .gitignore 排除文件"
  ],
  [
    "Advanced Web Access",
    "高级网页访问"
  ],
  [
    "Agent security mode",
    "智能体安全模式"
  ],
  [
    "Conversation picker",
    "对话选择器"
  ],
  [
    "Delete Conversation",
    "删除对话"
  ],
  [
    "Model quota reached",
    "模型额度已达上限"
  ],
  [
    "Modern Web Guidance",
    "现代 Web 开发指南"
  ],
  [
    "Network Permissions",
    "网络权限"
  ],
  [
    "Open Project Picker",
    "打开项目选择器"
  ],
  [
    "Open System Browser",
    "在系统浏览器中打开"
  ],
  [
    "Other Conversations",
    "其他对话"
  ],
  [
    "Parent Conversation",
    "父对话"
  ],
  [
    "Pinned Conversation",
    "已固定对话"
  ],
  [
    "Any error messages",
    "任何错误信息"
  ],
  [
    "Best of N Settings",
    "Best of N 设置"
  ],
  [
    "Chrome Binary Path",
    "Chrome 可执行文件路径"
  ],
  [
    "Conversation Width",
    "对话宽度"
  ],
  [
    "Create New Project",
    "创建新项目"
  ],
  [
    "Creating a Project",
    "正在创建项目"
  ],
  [
    "Keyboard shortcuts",
    "键盘快捷键"
  ],
  [
    "Outside of Project",
    "项目外"
  ],
  [
    "Proceed in Sandbox",
    "在沙盒中继续"
  ],
  [
    "Search projects...",
    "搜索项目..."
  ],
  [
    "Sort Conversations",
    "排序对话"
  ],
  [
    "Unpin Conversation",
    "取消固定对话"
  ],
  [
    "Verbose agent chat",
    "详细智能体聊天"
  ],
  [
    "Workspace Settings",
    "工作区设置"
  ],
  [
    "Advanced Settings",
    "高级设置"
  ],
  [
    "Automatic updates",
    "自动检查更新"
  ],
  [
    "Check for Updates",
    "检查更新"
  ],
  [
    "Copy Project Name",
    "复制项目名称"
  ],
  [
    "Edit Custom Model",
    "编辑自定义模型"
  ],
  [
    "File Access Rules",
    "文件访问规则"
  ],
  [
    "No agents running",
    "没有正在运行的代理"
  ],
  [
    "No Model Selected",
    "未选择模型"
  ],
  [
    "No projects found",
    "未找到项目"
  ],
  [
    "Open Conversation",
    "打开对话"
  ],
  [
    "Previous Pane Tab",
    "上一个面板标签页"
  ],
  [
    "Select one of the",
    "选择以下"
  ],
  [
    "Setup Jetski Chat",
    "配置 Jetski 聊天"
  ],
  [
    "Sort Conversation",
    "排序对话"
  ],
  [
    "Terminal Commands",
    "终端命令"
  ],
  [
    "Add Custom Model",
    "添加自定义模型"
  ],
  [
    "Background Tasks",
    "后台任务"
  ],
  [
    "Best of N Models",
    "Best of N 模型"
  ],
  [
    "Browser CDP Port",
    "浏览器 CDP 端口"
  ],
  [
    "Create a Project",
    "创建项目"
  ],
  [
    "Enable Demo Mode",
    "启用演示模式"
  ],
  [
    "File Permissions",
    "文件权限"
  ],
  [
    "General Feedback",
    "一般反馈"
  ],
  [
    "Keep In Menu Bar",
    "保留在菜单栏"
  ],
  [
    "New Conversation",
    "新建对话"
  ],
  [
    "No conversations",
    "暂无对话"
  ],
  [
    "Open Preferences",
    "打开偏好设置"
  ],
  [
    "Pin Conversation",
    "固定对话"
  ],
  [
    "Project Detected",
    "检测到项目"
  ],
  [
    "Project Settings",
    "项目设置"
  ],
  [
    "Provide Feedback",
    "提供反馈"
  ],
  [
    "1 agent running",
    "1 个代理正在运行"
  ],
  [
    "Actuation Rules",
    "操作规则"
  ],
  [
    "Background Task",
    "后台任务"
  ],
  [
    "Code with Agent",
    "与智能体协作编码"
  ],
  [
    "Command Palette",
    "命令面板"
  ],
  [
    "Editor Settings",
    "编辑器设置"
  ],
  [
    "Five Hour Limit",
    "5 小时限额"
  ],
  [
    "global settings",
    "全局设置"
  ],
  [
    "Message history",
    "消息历史"
  ],
  [
    "Missing Folders",
    "缺失文件夹"
  ],
  [
    "Open MCP Config",
    "打开 MCP 配置"
  ],
  [
    "Project Folders",
    "项目文件夹"
  ],
  [
    "Project General",
    "项目常规"
  ],
  [
    "Queued Messages",
    "排队消息"
  ],
  [
    "Search files...",
    "搜索文件..."
  ],
  [
    "Search tasks...",
    "搜索任务..."
  ],
  [
    "Toggle Terminal",
    "切换终端"
  ],
  [
    "Scheduled Tasks",
    "定时任务"
  ],
  [
    "Skills & Customizations",
    "技能与自定义扩展"
  ],
  [
    "Implementation Plan",
    "方案实施规划书"
  ],
  [
    "Choose the active Gemini model",
    "选择当前会话使用的 Gemini 思考与推理模型"
  ],
  [
    "Controls whether terminal commands require approval before running",
    "设置 AI 在运行终端命令或脚本时是否需要用户审批"
  ],
  [
    "Run agent commands inside a restricted sandbox environment for added security",
    "在受限沙箱中运行命令，防止意外修改主机系统以提高安全性"
  ],
  [
    "Controls whether the agent can read or write files outside the current workspace root",
    "控制 AI 是否可以读取或写入当前项目工作区目录之外的文件"
  ],
  [
    "Controls whether the agent can make network requests",
    "控制 AI 是否可以通过网络发起外部 HTTP 请求或抓取网页"
  ],
  [
    "Define global allow/deny rules for specific files, commands, and URLs",
    "为特定的文件路径、终端命令及网址定义全局允许/拒绝规则"
  ],
  [
    "Keep computer awake during long-running tasks",
    "当有长时间任务在后台运行时，阻止电脑自动进入睡眠模式"
  ],
  [
    "Run in background when the window is closed",
    "关闭主窗口后保持在 Windows 系统托盘后台静默运行"
  ],
  [
    "Auto-check for updates",
    "自动检查版本更新"
  ],
  [
    "Display and preserve intermediate thinking steps.",
    "显示并保留中间思考步骤。"
  ],
  [
    "We recommend attaching logs. Attaching logs will help the Antigravity team act and prioritize your feedback.",
    "建议附上日志。附上日志将有助于 Antigravity 团队处理并优先解决您的反馈。"
  ],
  [
    "Try out early-stage features before they ship. These may change or be removed at any time.",
    "在正式发布前试用早期功能。这些功能可能随时更改或移除。"
  ],
  [
    "Follow the guide at",
    "请按照以下指南操作："
  ],
  [
    "to back up your data and run the migration.",
    "以备份数据并运行迁移。"
  ],
  [
    "By using this app, you agree to its",
    "使用此应用即表示您同意其"
  ],
  [
    "For help, visit",
    "如需帮助，请访问"
  ],
  [
    "Manage Project Folders, agent settings, and permissions.",
    "管理项目文件夹、智能体设置和权限。"
  ],
  [
    "Open Editor Settings",
    "打开编辑器设置"
  ]
  ,
  [
    "Enable inline actions for background tasks",
    "为后台任务启用浮动卡片"
  ]  ,
  [
    "Show a floating notification card when background tasks require review or input.",
    "当后台任务需要审核或输入时显示浮动通知卡片。"
  ]  ,
  [
    "Inline Actions feedback",
    "浮动通知卡片反馈"
  ]  ,
  [
    "Background task requires your approval",
    "后台任务需要您的审批"
  ]  ,
  [
    "Background task requires your input",
    "后台任务需要您的输入"
  ]  ,
  [
    "Allow execution in background",
    "允许在后台执行"
  ]  ,
  [
    "Approve command and continue",
    "批准命令并继续"
  ]  ,
  [
    "Deny command and pause",
    "拒绝命令并暂停"
  ]  ,
  [
    "Grant permissions for this task",
    "为此任务授予权限"
  ]  ,
  [
    "Run in background mode",
    "在后台模式运行"
  ]  ,
  [
    "Bring task to foreground",
    "将任务置于前台"
  ]  ,
  [
    "Task completed in background",
    "后台任务已完成"
  ]  ,
  [
    "Task failed in background",
    "后台任务失败"
  ]  ,
  [
    "Use AI credits when model quota is exhausted",
    "当模型配额耗尽时使用 AI 积分"
  ]  ,
  [
    "Remaining AI Credits",
    "剩余 AI 积分"
  ]  ,
  [
    "Monthly Quota Reset",
    "每月配额重置"
  ]  ,
  [
    "Quota usage breakdown",
    "配额用量明细"
  ]  ,
  [
    "Auto-refill credits",
    "自动充值积分"
  ]  ,
  [
    "Credit balance low",
    "积分余额不足"
  ]  ,
  [
    "Manage billing and subscription",
    "管理账单与订阅"
  ]  ,
  [
    "Billing details",
    "账单详情"
  ]  ,
  [
    "Current billing cycle",
    "当前账单周期"
  ]  ,
  [
    "Model usage limit reached",
    "已达到模型使用上限"
  ]  ,
  [
    "Rate limit exceeded. Please try again later.",
    "超出速率限制，请稍后重试。"
  ]  ,
  [
    "Credits remaining",
    "剩余积分"
  ]  ,
  [
    "Out of model quota",
    "模型配额已耗尽"
  ]  ,
  [
    "Model quota refreshed",
    "模型配额已刷新"
  ]  ,
  [
    "Reconnecting to server...",
    "正在重新连接到服务器…"
  ]  ,
  [
    "Disconnected from server. Attempting to reconnect...",
    "已与服务器断开连接。正在尝试重连…"
  ]  ,
  [
    "Connection restored.",
    "连接已恢复。"
  ]  ,
  [
    "Network connection lost. Please check your network settings.",
    "网络连接丢失，请检查您的网络设置。"
  ]  ,
  [
    "Failed to reach Google Generative AI endpoint.",
    "无法访问 Google 生成式 AI 服务端点。"
  ]  ,
  [
    "Deep thinking in progress...",
    "正在深度思考中…"
  ]  ,
  [
    "Searching codebase...",
    "正在检索代码库…"
  ]  ,
  [
    "Reading files...",
    "正在读取文件…"
  ]  ,
  [
    "Analyzing directory structure...",
    "正在分析目录结构…"
  ]  ,
  [
    "Executing terminal command...",
    "正在执行终端命令…"
  ]  ,
  [
    "Generating solution...",
    "正在生成解决方案…"
  ]  ,
  [
    "Verifying implementation...",
    "正在验证实现…"
  ]  ,
  [
    "Agent stopped by user",
    "智能体已被用户终止"
  ]  ,
  [
    "Agent paused by user",
    "智能体已被用户暂停"
  ]  ,
  [
    "Resume execution",
    "继续执行"
  ]  ,
  [
    "Cancel execution",
    "取消执行"
  ]  ,
  [
    "Workspace indexed successfully",
    "工作区索引构建成功"
  ]  ,
  [
    "Indexing workspace...",
    "正在为工作区构建索引…"
  ]  ,
  [
    "Re-index workspace",
    "重新构建工作区索引"
  ]  ,
  [
    "Artifact created",
    "方案产物已生成"
  ]  ,
  [
    "Artifact updated",
    "方案产物已更新"
  ]  ,
  [
    "View artifact",
    "查看方案产物"
  ]  ,
  [
    "Diff view",
    "代码差异对比"
  ]  ,
  [
    "Accept changes",
    "接受变更"
  ]  ,
  [
    "Reject changes",
    "拒绝变更"
  ]  ,
  [
    "Keep current changes",
    "保留当前变更"
  ]  ,
  [
    "Revert all changes",
    "还原所有更改"
  ]  ,
  [
    "Apply this change",
    "应用此变更"
  ]  ,
  [
    "Discard this change",
    "放弃此变更"
  ]  ,
  [
    "Show inline diff",
    "显示行内差异"
  ]  ,
  [
    "Show side-by-side diff",
    "显示双栏差异"
  ]  ,
  [
    "Review proposed modifications before applying",
    "在应用前审查提议的修改"
  ]  ,
  [
    "Allow once",
    "仅允许一次"
  ]  ,
  [
    "Always allow for this session",
    "本次会话始终允许"
  ]  ,
  [
    "Always deny",
    "始终拒绝"
  ]  ,
  [
    "View terminal output",
    "查看终端输出"
  ]  ,
  [
    "Clear terminal output",
    "清空终端输出"
  ],
  [
    "Are you sure you want to delete this conversation? This action cannot be undone.",
    "您确定要删除此对话吗？此操作无法撤销。"
  ],
  [
    "No groups yet",
    "暂无分组"
  ],
  [
    "Collapse queued messages",
    "折叠排队消息"
  ],
  [
    "Expand queued messages",
    "展开排队消息"
  ]
,
    ['AI coding agents are known to have certain security limitations. Users should be aware of potential risks, including data exfiltration and possible code execution. Avoid processing highly sensitive data and verify all the actions taken by the agent.', '已知 AI 编程智能体存在一定的安全限制。用户应了解潜在风险，包括数据外泄和可能的代码执行。避免处理高度敏感的数据，并核实智能体采取的所有操作。'],
    ['AI coding agents are known to have certain security risks, including autonomous code execution, data exfiltration, prompt injection and supply chain risks. Ensure that you monitor and verify all actions taken by the agent.', '已知 AI 编程智能体存在一定的安全风险，包括自主代码执行、数据外泄、提示词注入和供应链风险。请务必监控并核实智能体采取的所有操作。'],
    ['does not collect any of your prompts, content, or model responses but does collect general usage patterns such as feature adoption and active user counts (“product analytics”). Telemetry data will be handled in accordance with the Google Privacy Policy.', '不会收集您的任何提示词、内容或模型响应，但会收集常规使用模式，例如功能采用率和活跃用户数（“产品分析”）。遥测数据将根据 Google 隐私权政策进行处理。'],
    ['does not collect any of your prompts, content, or model responses but does collect general usage patterns such as feature adoption and active user counts ("product analytics"). Telemetry data will be handled in accordance with the Google Privacy Policy.', '不会收集您的任何提示词、内容或模型响应，但会收集常规使用模式，例如功能采用率和活跃用户数（“产品分析”）。遥测数据将根据 Google 隐私权政策进行处理。'],
    ['does not collect any of your prompts, content, or model responses but will still collect general usage patterns (e.g., feature adoption, active user counts).', '不会收集您的任何提示词、内容或模型响应，但仍会收集常规使用情况（例如功能采用率、活跃用户数）。'],
    ['Yes, I agree to help improve', '是的，我同意帮助改进'],
    ['by allowing Google to collect and use my Interactions data, subject to the', '允许 Google 收集并使用我的互动数据，并遵守'],
    ['I understand I can choose to opt out later whenever I want via my settings.', '我了解我随时可以在设置中选择退出。'],
    ['. I understand I can choose to opt out later whenever I want via my settings.', '；我了解我随时可以在设置中选择退出。'],
    ["Yes, I'd like to receive product updates, tips, and promotions from Google", '是的，我希望接收来自 Google 的产品更新、提示和优惠信息'],
    ['(excluding product analytics data)', '（不包括产品分析数据）'],
    ['Terms and Privacy:', '条款与隐私：'],
    ['Terms of Service & Data Use', '服务条款与数据使用'],
    ['Security Notice & Data Use', '安全须知与数据使用'],
    ['Accept and continue', '接受并继续'],
    ['Google Privacy Policy', 'Google 隐私权政策'],
    ['Getting started with Google Antigravity', '开始使用 Google Antigravity'],
    ["Here's how you and your agents work together", '了解您与智能体如何协同工作'],
    ['Build with one agent or a team', '与单个智能体或团队共同构建'],
    ['Describe what you want. Your agent plans and builds it, and brings in other agents when needed.', '描述您的需求。智能体将规划并构建实现，并在需要时引入其他智能体协同。'],
    ['Review plans and walkthroughs', '审核计划与演练指南'],
    ['Comment on the plan before your agent starts, and get a walkthrough when it finishes.', '在智能体开始之前对计划发表评论，并在完成后获取演练指南。'],
    ['Set the rules, define the boundaries.', '设定规则，明确边界。'],
    ['By default, agents work in folders you choose and ask before sensitive changes. Adjust this anytime in Settings.', '默认情况下，智能体在您选择的文件夹中工作，并在执行敏感更改前征求许可。您可随时在“设置”中调整。'],
    ['to switch to the Gemini app. Your agents keep working in the background.', '即可切换至 Gemini 应用。您的智能体将在后台继续工作。'],
    ['Telemetry is disabled in Settings', '遥测已在设置中禁用'],
    ['Telemetry is off for all conversations.', '所有对话的遥测均已关闭。'],
    ['Telemetry is off for this conversation.', '此对话的遥测已关闭。'],
    ['Telemetry is turned off in settings', '遥测已在设置中关闭'],
    ['Telemetry will be disabled for this conversation; click to enable.', '此对话的遥测将被禁用；点击启用。'],
    ['Telemetry will be enabled for this conversation; click to disable.', '此对话的遥测将被启用；点击禁用。'],
    ['Configure link opening and built-in browser preferences.', '配置链接打开方式与内置浏览器偏好设置。'],
    ['Choose where links open by default when clicked.', '选择点击链接时默认打开的位置。'],
    ['Folder where files downloaded in the built-in browser are saved.', '内置浏览器中下载文件的保存目录。'],
    ['Clear visited URLs and autocomplete suggestions from the built-in browser.', '清除内置浏览器中已访问的网址与自动补全建议。'],
    ['The voice used in Voice mode. Powered by Gemini Live.', '语音模式下使用的声音。由 Gemini Live 提供技术支持。'],
    ['Input device for voice mode and dictation.', '语音模式与语音输入的采集设备。'],
    ["How loud Antigravity's voice is.", 'Antigravity 朗读与语音回复的音量大小。'],
    ['Whatever the voice-engine-addr flag serves you.', '由 voice-engine-addr 启动参数指定的语音服务。'],
    ['Choose how much detail is shown during a conversation.', '选择在对话过程中显示多少执行细节。'],
    ['Settings for conversations outside of projects.', '未关联项目的独立对话通用设置。'],
    ['Choose the experience that fits how you work.', '选择适合您工作方式的界面体验。'],
    ['Choose between the Default and Project 4K experience.', '在默认经典体验与 Project 4K 沉浸体验之间进行切换。'],
    ['Show system notifications when your action is needed or the agent finishes.', '当需要您确认操作或智能体完成任务时，显示系统通知。'],
    ['Play a sound when your action is needed or the agent finishes.', '当需要您确认操作或智能体完成任务时，播放提示音。'],
    ['Set the volume of agent sounds.', '设置智能体提示音的音量大小。'],
    ['Scan the code to open this device in Remote Control, or', '扫描二维码在远程控制中打开此设备，或者'],
    ['A label for this computer when you connect from another device. Changing it reconnects.', '当您从其他设备连接时用于标识这台电脑的名称。修改后将重新连接。'],
    ['Run the app against a Linux environment. Connecting relaunches the app into the selected WSL distro.', '在 Linux 环境中运行应用。连接后将把应用重启并载入选定的 WSL 发行版中。'],
    ['This project was created for', '此项目专为以下任务创建：'],
    ['is managed by the', '由以下自动化任务管理：'],
    ['automation and can only be deleted by deleting that automation.', '自动化任务管理，且只能通过删除该自动化任务来进行删除。'],
    ['to ask for content changes for legal reasons.', '以出于法律原因申请内容变更。'],
    ['Comprehensive guide and reference for the Antigravity Customization System. Use to explain how customizations work, their loading priority, discovery mechanisms, and to guide the creation of skills, rules, plugins, hooks, and MCP servers.', 'Google Antigravity 自定义系统的全面指南与参考手册。用于了解自定义系统的运作机制、加载优先级、发现规则，并指导技能、规则、插件、钩子及 MCP 服务的创建。'],
    ['Provides a comprehensive guide, quick reference, and sitemap for Google Antigravity (AGY), including the Antigravity CLI (agy), Antigravity 2.0, Antigravity IDE, Python SDK, slash commands, keybindings, and customizations (skills, rules, MCP, sidecars). Activate this skill when the user asks questions about how to use, configure, or customize Antigravity, AGY, the agy CLI, the Antigravity IDE, or Antigravity 2.0.', '提供 Google Antigravity (AGY) 的全景开发指南、速查手册与系统导航，涵盖 CLI、Antigravity 2.0、IDE、Python SDK、快捷指令、键位映射与各项自定义扩展。'],
    ['Interactive guide to design and create a scheduled background automation. Use this skill when the user wants to create an automated or recurring scheduled task (e.g. "summarize my emails every morning", "every Monday send me a to-do list"). Also triggered by the /automation slash command.', '用于设计并创建计划后台自动化的交互向导。当用户希望创建定时自动化任务时激活此技能。'],
    ['How to render rich interactive HTML widgets inline in the chat or as standalone artifacts. Use this skill when you want to show the user diagrams, data visualizations, interactive controls, educational walkthroughs, or any rich visual content beyond plain text and markdown.', '在对话中以富交互 HTML 小组件或独立产物形式呈现图表、数据可视化、交互式控件与教程流程。'],
    ['Automatically migrate legacy workflows to modern skills across global and workspace configurations. Scans for existing workflows, creates target SKILL.md files, and safely archives old workflow files.', '自动将全局和工作区配置中的旧版工作流规范平滑迁移至现代技能体系，创建标准化 SKILL.md 并安全归档旧文件。'],
    ['Guidelines for interacting with GitHub and request permissions from the user when commands fail due to restrictions in the agent environment.', '与 GitHub 交互并处理 Agent 环境受限时向用户申请安全权限的操作指南与准则。'],
    ['How to manage and create plugins — namespaced bundles of skills, agents, rules, MCP servers and hooks that install, enable and disable as a single unit. Use this skill when the user wants to enable, disable, install or uninstall a plugin, when they want to create a new plugin, or when a new customization should be packaged into a plugin rather than left loose. Also triggered by the /plugin slash command. Don\'t use for the underlying customization system itself — discovery roots, loading priority, or authoring a standalone skill, agent, rule, hook or MCP server outside a plugin; see the customizations guide skill for those.', '管理与打包插件（技能、智能体、规则、MCP 服务与钩子的命名空间包）。用于安装、卸载、启用、禁用及发布自定义插件。'],
    ['How to write and run a dynamic workflow script with the `run_workflow` tool: a Python script that orchestrates many agents with `agent`, `parallel`, `pipeline`, and `phase`. Use when a task splits into many independent or staged pieces of agent work (fan out over files, modules, bugs, or review angles, then aggregate), or when the user asks for a workflow. Don\'t use for a single delegated task (use a subagent) or for legacy workflow files (see migrate-workflows).', '使用 run_workflow 工具编写并运行动态多智能体工作流脚本，通过 Python 脚本编排并行、管线与分阶段 Agent 协作。'],
    ['Discover UI plugin panels relevant to the current task and surface a one-click pill in chat to open (toggle) them in the side pane. Use when a running UI plugin\'s panel would help with what the user is doing, or right after the user enables a new UI plugin pane and a shortcut to open it is handy.', '自动发现与当前任务相关的 UI 插件面板，并在聊天中提供一键调起的交互胶囊链接，方便用户在侧边栏直接打开。'],
    ['Provides instructions for installing and using the `android` CLI. The `android` command-line tool is a critical tool for Android development and helps you create new Android projects, run Android apps on devices, manage and interact with Android virtual devices (including screenshots and UI inspection), manage Android SDK components, look up official Android documentation, and discover and install official Android skills.', '提供安装与使用 android CLI 的完整指南。支持创建 Android 工程、连接与管理真机/模拟器、截屏与 UI 探测、管理 Android SDK 以及安装官方 Android 技能。'],
    ['Instructions for working with the Android Device Hub sidecar, which lists, starts, stops, creates and removes Android Virtual Devices (AVDs), lists physical devices connected to adb, and lets the user mirror and control any of them (video, touch, keyboard, mouse wheel) in the Device Hub pane. Also explains how to inspect and interact with the screen the user is mirroring, with `android layout`, `android screen` and `adb`.', 'Android Device Hub 辅助面板操作指南。用于列出、启动、停止、创建与移除 Android 虚拟设备 (AVD)，列出 ADB 连接的物理设备，并实现低延迟画面镜像与键鼠触摸控制。'],
    ['Instructions for the Android Compose Preview sidecar, which renders Jetpack Compose @Preview functions with `android preview render` and shows them in the Android Compose Preview pane. Use it when the user wants to see a Compose preview, or to review the result of UI changes — re-render after changing the code so that the pane shows the result.', 'Android Compose 预览辅助面板操作指南。用于通过 android preview render 实时渲染 Jetpack Compose 的 @Preview 组件并在侧边栏直接交互预览。'],
    ['Retrieve and analyze AlphaFold predicted structures for a protein. Use when the user provides a specific UniProt Accession ID and wants structural confidence metrics (pLDDT), domain boundary analysis, or disorder assessment. Do not use if the user only has a protein name, gene name, or amino acid sequence — ask for a UniProt ID first.', '检索并分析蛋白质的 AlphaFold 预测 3D 结构。根据 UniProt 访问 ID 计算结构置信度度量 (pLDDT)、结构域边界分析及内在无序区评估。'],
    ['Constructs deep-links and URLs for the AlphaGenome Atlas website. Supports generating single-variant exploration links (1-based VCF-style coordinates), genomic locus views (1-based closed chr:start-end), candidate summary tables, and AlphaGenome reference vs. alternate predictions. Use when visualizing, exploring, charting, or linking genetic variants and genomic loci on the AlphaGenome Atlas, or when asked to inspect, view, or link predictions for a genomic variant. Don\'t use for computing raw AlphaGenome variant predictions directly without Atlas URLs (use alphagenome-single-variant-analysis or alphagenome-variant-impact-score).', '构建 AlphaGenome Atlas 网站的深度跳转链接。支持生成单变异位点探索链接、基因组基因座视图、候选变异摘要表及参考/突变预测比对。'],
    ['Analyzes genetic variant effects on gene expression (RNA-seq), chromatin accessibility (DNASE), histone marks (ChIP), and transcription factors using the AlphaGenome API. Use when the user asks about non-coding variant effects, pathogenicity, clinical significance, disease associations, functional effects, gene expression changes, splicing disruption, or regulatory effects in promoters and enhancers. Also use for resolving biological terms to tissue/cell-type ontologies (UBERON/CL) or analyzing variants in chr:pos:ref>alt format.', '利用 AlphaGenome API 分析遗传变异对基因表达 (RNA-seq)、染色质可及性 (DNASE)、组蛋白修饰 (ChIP) 及转录因子的功能影响。'],
    ['Score, annotate, and analyze the functional impact of genetic variants using AlphaGenome Variant Impact (AVI) scores. Query variants in chr:pos:ref>alt format, annotate VCF/tabular callsets, perform saturation mutagenesis window scans (1-based closed chr:start-end), and extract GENCODE v46 GTF gene/exon/junction coordinates all via the AlphaGenome Atlas API.', '使用 AlphaGenome 变异影响评分 (AVI) 评估和注释人类遗传变异的功能影响，支持饱和突变窗口扫描与 GENCODE 基因外显子坐标提取。'],
    ['Interactive 3D biomolecular structure viewer via Mol*. Renders 3D molecular structures from local workspace files (.cif, .mmcif, .pdb) or conversation artifacts, and manages user 3D annotations and highlighted residues. Use when the user asks to visualise a protein or nucleic acid, display a 3D structure, or asks about 3D biomolecular structure annotations and highlighted residues.', '基于 Mol* 的交互式 3D 生物分子结构查看器。渲染本地工作区或对话产物中的蛋白质与核酸分子三维模型，支持高亮残基与 3D 标注。'],
    ['Query the ChEMBL database for bioactive molecules, drug targets, bioactivity data, approved drugs, and chemical structures. Use when the user asks about compounds, targets, IC50/Ki values, drug mechanisms, or structure searches.', '查询 ChEMBL 数据库中的生物活性小分子、药物靶点、IC50/Ki 生物活性数据、获批上市药物及化学结构。'],
    ['Co-folds protein-ligand, protein-DNA/RNA, and covalent inhibitor complexes: prepares AlphaFold 3 JSON, Boltz-2 YAML, and Boltz API (boltz-2.1) inputs, extracts bound ligand poses from mmCIF/PDB, and computes 3D protein-ligand interaction fingerprints (PLIF) and pharmacophore overlaps.', '计算化学：协同折叠蛋白质-配体、蛋白质-DNA/RNA 以及共价抑制剂复合物，准备 AlphaFold 3 JSON 与 Boltz-2 输入并计算 3D 相互作用指纹 (PLIF)。'],
    ['Computes RDKit physicochemical descriptors (MW, cLogP, TPSA, CNS MPO, SA score), PAINS/Brenk structural alerts, pH 7.4 ionization, congeneric series curation, activity cliffs, combinatorial library enumeration, vendor pricing, and organometallic %V_bur sterics.', '计算化学核心：计算 RDKit 理化分子描述符（MW、cLogP、TPSA、CNS MPO、SA 评分）、PAINS/Brenk 结构警示物、pH 7.4 电离状态与组合化学库枚举。'],
    ['Extracts and curates validated chemical structures from patents, literature, synthesis procedures, and Markush core/R-group tables: resolves IUPAC names via OPSIN and PubChem, retrieves Google Patents full text and assay tables, and exports curated SDF/CSV.', '计算化学：从专利、学术文献与合成步骤中提取并验证化学结构，通过 OPSIN/PubChem 解析 IUPAC 命名并导出标准化 SDF/CSV 库。'],
    ['Trains, benchmarks, and evaluates predictive SAR and QSAR/ADMET models for chemical series: small-N regularized regressors, nested cross-validation, Tukey HSD model tiering, scaffold/temporal splitting, matched molecular pairs (MMPA), similarity attribution maps, model persistence, and candidate scoring.', '计算化学机器学习：训练、基准测试与评估针对化学分子序列的预测性 SAR 和 QSAR/ADMET 模型，支持小样本正则化、嵌套交叉验证与骨架分割。'],
    ['Simulates 3D molecular physics, conformer ensembles, and CADD workflows: pH-dependent ligand and receptor protonation, ETKDGv3 3D conformer generation, dihedral/relaxed PES torsion scans, AutoDock Vina/smina docking, conformational ligand strain energy, PROTAC/macrocycle 3D geometry, and OpenMM molecular dynamics.', '计算化学分子物理模拟：pH 依赖性受体/配体质子化、ETKDGv3 3D 构象系综生成、扭转角 PES 扫描、AutoDock Vina/smina 分子对接与 OpenMM 分子动力学模拟。'],
    ['Proposes and models organic reactions, retrosynthesis, multi-step synthesis routes, intramolecular cyclizations, and reaction SMARTS: checks experimental precedents first, validates atom conservation, prochirality (pro-R/pro-S, Re/Si), topicity, 1H/13C NMR equivalence, and stereogenesis, and renders 2D curved-arrow mechanisms.', '计算化学反应与逆合成：模拟有机化学反应、多步合成路线、分子内环化与反应 SMARTS，验证原子守恒与手性立体构型。'],
    ['Query ClinicalTrials.gov via APIv2. Use when you want to search for trials by condition, drug, location, status, or phase; retrieve trial details by NCT ID; check eligibility/inclusion criteria; count trials across conditions or time periods; identify a sponsor\'s trial portfolio; find recruiting trials for patient matching.', '通过 ClinicalTrials.gov API 查询全球临床试验，按病症、药物、地点、试验阶段检索试验详情与患者入组准入标准。'],
    ['Use when needing clinical significance, pathogenicity classifications (e.g., Pathogenic, Benign, VUS), clinical evidence rationales, or finding "hard positive" benchmark controls for human genomic variants.', '查询 NCBI ClinVar 数据库中人类基因组变异的临床意义、致病性分类（致病、良性、意义未明 VUS）与临床证据支持等级。'],
    ['Instructions for handling API keys and credentials safely, verifying their presence, and prompting the user to add them if missing using a safe protocol.', '安全处理 API 密钥与凭据验证，检测关键凭据状态并在缺失时引导用户通过安全协议添加凭证。'],
    ['Use when you want to look up, map, and search for short genetic variants (SNPs, indels) in NCBI\'s dbSNP database. Resolves between rsIDs, genomic coordinates in VCF format, and HGVS strings. For an rsID, returns variant type, gene associations, clinical significance, allele frequencies, and genomic coordinates (GRCh38).', '在 NCBI dbSNP 数据库中检索、映射和查找短遗传变异（SNP、插入缺失），在 rsID、GRCh38 染色体坐标与 HGVS 格式间互相转换。'],
    ['Query and search the EMBL-EBI Ontology Lookup Service (OLS) for biomedical ontology terms, definitions, and hierarchies across 250+ ontologies (e.g., GO, DOID, HP). Use when the user asks to search for terms, retrieve details, navigate hierarchies (parents, children, ancestors), look up properties and individuals, get autocomplete suggestions, or access ontology metadata and statistics.', '查询 EMBL-EBI 生物医学本体术语词汇库 (OLS)，检索包括 GO、DOID、HP 等 250+ 种生物学本体术语的定义、层级与上下级关系。'],
    ['Query the ENCODE Registry of cis-Regulatory Elements (cCREs) via the SCREEN GraphQL API, or make custom queries to the ENCODE Portal REST API for experiments and files (ChIP-seq peaks, etc.). Use when you want to query regulatory annotations or raw experimental data across human cell types.', '通过 SCREEN GraphQL 与 ENCODE Portal REST API 查询 ENCODE 人类顺式调控元件候选集 (cCRE) 及原始 ChIP-seq 峰图实验数据。'],
    ['Query the Ensembl database to resolve gene, transcript, and protein IDs, fetch genomic or protein sequences, retrieve gene structures (exons), and get variant consequence and effect predictions (VEP). Use this skill as a primary ID translator, genomic sequence database and variant effect prediction tool.', '查询 Ensembl 数据库以解析基因、转录本与蛋白质 ID，提取基因组序列与外显子结构，并进行变异效应预测 (VEP)。'],
    ['Performs 3D structural searches of proteins against various databases (PDB, AlphaFold, CATH, MGnify, etc.) using the Foldseek API. Use ONLY when the user provides a physical 3D coordinate file (.cif, .mmcif, or .pdb) and wants to find structurally similar proteins. Do NOT use if the user only provides a protein sequence, gene name, or UniProt ID.', '使用 Foldseek 针对 PDB、AlphaFold 等结构库执行蛋白质 3D 空间结构的极速相似性搜索。'],
    ['Query the Genome Aggregation Database (gnomAD). Use when determining the rarity or allele frequency of specific genetic variants, retrieving gene constraint metrics (pLI, LOEUF) to assess loss-of-function intolerance, finding variants in a genomic region or gene, or querying structural variants. Don\'t use for analyzing individual patient genomes, tracking somatic mutations in cancer (use COSMIC), or requesting raw sequencing reads (use ENA).', '查询人类基因组变异数据库 (gnomAD)，检索特定遗传变异在各大人群中的等位基因频率与基因功能丧失不耐受约束指标 (pLI, LOEUF)。'],
    ['Use when you want to retrieve quantitative RNA expression data and variant eQTL information from the GTEx (Genotype-Tissue Expression) Project across 54 non-diseased tissue sites.', '从基因型-组织表达项目 (GTEx) 中检索人体 54 种正常健康组织中的定量 RNA 表达量与表达数量性状位点 (eQTL) 关联数据。'],
    ['Use when you want to retrieve semi-quantitative protein expression and spatial localisation data from the Human Protein Atlas (HPA).', '从人类蛋白质图谱 (HPA) 检索人体各组织器官中的半定量蛋白质表达量以及显微亚细胞定位图谱数据。'],
    ['Identify domains, families, and sites in proteins; find all proteins in a family or sharing a domain; explore species distribution for a domain; annotate genomes with protein families and GO terms. InterPro combines 14 databases (e.g., Pfam, CDD) into one searchable resource. InterPro-N significantly expands annotation and sequence coverage with deep learning. Includes domain architecture (IDA) search.', '整合 14 个权威数据库识别蛋白质的家族、结构域与活性位点，支持蛋白质功能注释与结构域体系 (IDA) 分析。'],
    ['Query the JASPAR database for Transcription Factor (TF) binding profiles. Use when retrieving Position Frequency Matrices (PFMs) or Position Weight Matrices (PWMs) for specific TFs, resolving gene symbols to JASPAR Matrix IDs, or getting TF metadata. Supports multiple output formats (MEME, TRANSFAC, PFM, JASPAR, YAML).', '查询 JASPAR 转录因子结合基序数据库，获取特定转录因子在 DNA 上的位置频率矩阵 (PFM) 与位置加权矩阵 (PWM)。'],
    ['Search for scientific papers, preprints, and publications on arXiv. Extract metadata, abstracts, and download full-text PDFs or HTML versions of papers. Use when the user asks to find research papers, literature, or specific arXiv IDs.', '检索 arXiv 平台上的科学预印本文献，提取论文元数据、摘要并支持直接下载 PDF 与 HTML 论文正文。'],
    ['Browse, filter, and download life sciences, biology, and medical preprints from bioRxiv and medRxiv. Supports fetching paper metadata by DOI, and browsing by date range with category and keyword filters. Keyword filtering is local, so date ranges MUST be narrow (1-4 weeks) with a category to prevent timeouts.', '检索与过滤 bioRxiv 及 medRxiv 生命科学和医学领域的最新预印本文献并获取元数据与论文全文。'],
    ['Search Europe PMC for scientific literature and download open-access full texts and PDFs. Retrieve full-text XML/plain text by PMCID, get citation lists and bibliography.', '检索 Europe PMC 欧洲医学文献库中的学术论文，按 PMCID 下载开放获取全文 XML、纯文本与 PDF 文件。'],
    ['Query the OpenAlex scholarly database for research papers, authors, institutions, topics, sources, publishers, funders, geo-locations, and keywords. Use when searching academic papers, resolving DOIs, downloading open-access PDFs, finding an author\'s publications, aggregating bibliometric data (citation counts, h-index, impact factor), exploring the research taxonomies, or performing DOI lookups.', '查询 OpenAlex 全球学术图谱数据库，检索学术论文、作者、机构、期刊影响因子、引用次数及 DOI 解析。'],
    ['Retrieve protein and nucleotide sequences from NCBI databases using E-utilities. Supports direct accession lookup, CDS translation, gene+organism search, locus lookup, PubMed-linked sequences, patent protein extraction, and organism+length fallback search. Use when you need to fetch biological sequences by accession, gene name, locus tag, PubMed ID, or patent number.', '使用 E-utilities 从 NCBI 权威生物数据库提取蛋白质与核酸序列，支持按 Accession、基因名称、文献 PMID 查找序列。'],
    ['Query, search, and download data from the openFDA API for drugs, devices, foods, tobacco, cosmetics, animal and veterinary products, substances, and transparency data. Use for FDA adverse events, recalls, labeling, approvals, shortages, 510(k) clearances, NDC lookups, and any FDA safety or regulatory data query across all 28 API endpoints.', '查询美国食品药品监督管理局 (openFDA) 大数据库，检索药物不良事件、产品召回、药品标签说明书、上市批准与安全通报。'],
    ['Query Open Targets Platform for target-disease associations, drug target discovery, tractability/safety data, genetics/omics evidence, known drugs, for therapeutic target identification.', '查询 Open Targets 平台以进行药物靶点发现、靶点-疾病关联度分析、成药性评估及遗传学/组学证据链追踪。'],
    ['Use when you want to search for or download experimentally-determined 3D structures for biomolecules (proteins, nucleic acids, bound ligands). Supports searching by sequence similarity, structure similarity, chemical and other attributes. Also use to get metadata about biomolecular structure experiments.', '查询并下载蛋白质数据库 (PDB) 中实验测定的生物大分子（蛋白质、核酸、配体复合物）3D 空间三维结构与实验元数据。'],
    ['Ancient text restoration, attribution, dating, contextualization, and embedding via Aeneas (Latin) / Ithaca (Ancient Greek). Use when asked to "restore", "attribute", "date", "contextualize", "find parallels", "where was it written", "when was it written", "embed", or "analyze" an ancient text, inscription, or epigraphic document, or when the user mentions "Aeneas", or "Ithaca".', '基于 Aeneas 与 Ithaca 深度学习模型执行古代拉丁语与古希腊语文本文物修复、年代断代与地理起源地归属推断。'],
    ['Performs multiple sequence alignment of proteins with EBI Clustal Omega. Use when you need to align multiple sequences to assess similarity, domain conservation, or key residue conservation. Supports up to 4000 sequences and a maximum file size of 4 MB. Do not use to search for homologous proteins in a database (use MMseqs2, BLAST), align non-protein sequences (DNA, RNA), perform structural alignment (use Foldseek, PyMOL), or if you only have a single sequence.', '使用 EBI Clustal Omega 对多条蛋白质序列进行多重序列比对 (MSA)，评估序列保守性与关键活性残基演化。'],
    ['Searches for homologous protein sequences using MMseqs2 (fast, default) or BLAST (comprehensive, fallback). Trigger this whenever the user provides a protein sequence or FASTA file and asks to find homologues, sequence matches, or wants to infer protein function based on sequence similarity, but not when the user wants to infer protein function based on structural similarity.', '使用 MMseqs2 或 NCBI BLAST 检索与输入蛋白质序列高度同源的匹配序列并推断蛋白质功能。'],
    ['Query PubChem, search by name/CID/SMILES, retrieve properties, similarity/substructure searches, bioactivity, for cheminformatics. Use when a user asks about a specific chemical, drug, or molecule.', '查询 PubChem 权威化学数据库，支持通过名称、CID、SMILES 搜索小分子化合物的理化性质与生物活性数据。'],
    ['Search PubMed for scientific literature, including published clinical trials. Fetch abstracts and full text. Link published research to biological databases (gene, protein, nucleotide, PubChem) to discover associations between papers and specific compounds or genes. Verify medical spelling, match raw citations, and cache result sets for bulk processing. Interfaces NCBI E-utilities and PMC BioC APIs.', '检索 PubMed 全球医学与生命科学同行评审文献库，提取论文摘要、临床试验结论并关联生化物质与基因实体。'],
    ['Visualize, analyze, and render protein and molecular structures using PyMOL. Use when the user wants to create images of protein structures, perform structural alignments or superposition, measure distances or contacts, highlight binding sites or active site residues, color by B-factor/pLDDT, or analyze protein-ligand interactions. Do not use for docking, molecular dynamics, or sequence-only analysis.', '利用 PyMOL 生成蛋白质与分子三维结构的高清精美渲染图，支持空间叠合比对、结合口袋测量与 pLDDT 颜色映射。'],
    ['Query the QuickGO and Evidence & Conclusion Ontology (ECO) REST API. Use this when you need to map genes to biological processes, molecular functions, or cellular components, find genes associated with a specific pathway/GO term, or explore the Gene Ontology hierarchy. Do not use for querying drug targets (use OpenTargets) or mechanistic signaling pathway diagrams (use KEGG).', '查询 QuickGO 基因本体论 (GO) 与证据结论本体 (ECO)，将基因与生物学过程、分子功能及细胞组分进行映射分析。'],
    ['Generates 2D chemical structure depictions (PNG/SVG), interactive HTML compound grids, standalone chemical applications/visualizers, and ChemDraw (.cdxml/.cdx) documents using ACS 1996 publication styling; validates IUPAC/stereochemical nomenclature and provides shared RDKit version compatibility helpers.', '基于 RDKit 生成化学分子 2D 结构图 (PNG/SVG)、交互式化合物图谱网格并生成 ACS 1996 出版级 ChemDraw 矢量文档。'],
    ['Query the Reactome database (Analysis and Content Services). Use when the user asks about pathway analysis, gene list enrichment, retrieving results by token, finding unmapped or not-found identifiers, mapping identifiers, reaction participants (inputs, outputs), pathway hierarchy (including top-level pathways), diagram export, cross-reference mapping, or searching the knowledgebase.', '查询 Reactome 生物学通路数据库，执行基因列表通路富集分析、信号级联网络追踪与通路拓扑图导出。'],
    ['Query the STRING database for protein-protein interactions (PPIs), functional enrichment, and homology. Use when the user asks about interactions between specific proteins, interaction evidence, confidence scores, protein interaction partners, or pathway enrichments.', '查询 STRING 蛋白质相互作用网络数据库 (PPI)，分析蛋白结合配对证据、置信度得分与生物学功能富集。'],
    ['Fetch Evolutionary Conservation scores (phyloP, phastCons) and Transcription Factor Binding Sites (TFBS) from the UCSC Genome Browser. Use when analyzing whether genomic variants or regions are evolutionarily conserved, functionally important, or bounded by TF regulators across major projects (ENCODE, JASPAR, ReMap).', '从 UCSC 基因组浏览器获取进化保守性评分 (phyloP, phastCons) 以及转录因子结合位点 (TFBS) 数据。'],
    ['Queries the UniBind database for experimentally validated transcription factor (TF) binding sites. Use when retrieving direct TF-DNA interaction datasets, downloading binding site coordinates (BED/FASTA) for local analysis, or listing available datasets by species, cell line, or TF name. Don\'t use to query specific intervals, locations, genes, motif models or expression data.', '查询 UniBind 数据库中通过 ChIP-seq 实验直接验证的转录因子结合位点坐标与序列数据集。'],
    ['Access protein metadata, function, taxonomy, and sequences across UniProtKB, UniParc, and UniRef. Use when searching for proteins, mapping identifiers, or retrieving functional annotations and publications. Don\'t use for sequence alignment, protein folding, or sequence similarity search (use specialized skills for those tasks).', '查询 UniProt 权威蛋白质知识库（UniProtKB、UniParc、UniRef），获取全生命周期的蛋白质序列、功能注释与文献溯源。'],
    ['Checks whether the uv Python package manager is installed and installs it if missing. Ensures uv is on PATH. Use when another skill requires uv as a prerequisite.', '检查并管理现代极速 Python 包管理器 uv 的安装与运行环境，确保其在系统 PATH 中随时可用。'],
    ['Distills a completed user workflow or interaction into a reusable agent skill. Use when the user asks to turn their workflow, interaction, or multi-step process into a skill, or when they say "make this a skill", "create a skill from what we just did", "package this workflow" or similar. Do not use for creating skills from scratch without an existing workflow (use a generic skill-creator for that).', '将已完成的会话工作流提炼并封装为符合规范的 Agent 智能体技能 (Skill)。'],
    ['哈耶克 × 米塞斯 × Claude 三人对话。奥派经济学视角的多角色讨论。 触发方式：/chatroom-austrian、/奥派、「奥派聊天室」 Austrian economics chatroom. Hayek × Mises × Claude debate. Trigger: /chatroom-austrian, /奥派, "Austrian chat"', '奥派经济学多智能体研讨室。模拟米塞斯、哈耶克与罗斯巴德等多位学者，从第一性原理与人的行动学视角深度研讨经济命题。'],
    ['团建图文内容生产技能：基于《轮播母版迁移器 V4.8.8》五阶状态机与人机双轨标准，通过本地工作台API与云端CDP执行母版锁定、素材派发、显性计划审核、一键批量出图(回复1)、五版文案提取与成品落盘。', '全自动图文与短视频内容矩阵生产管线。支持多账号批量生成、文案排版、视觉出图与跨平台合规发布。'],
    ['dontbesilent 商业工具箱主入口，提供新手教程与单任务动态编排。用户第一次使用 dbskill、不知道该用哪个正式 Skill、带着真实任务寻求合适能力，或在一项任务完成后询问下一步时使用。', 'DontBeSilent 商业自媒体运营技能入口。提供商业模式诊断、对标拆解与私域流量转化的全套实操技能。'],
    ['用阿德勒心理学框架诊断执行阻滞。用户知道该做什么却迟迟不做、反复拖延或行动中断时使用。', 'DontBeSilent 商业行动力突破与执行引擎。克服拖延与不确定性，将复杂商业目标拆解为即可落地的最小行动单元。'],
    ['用五重过滤法寻找值得模仿的对标，并排除主体差异造成的噪音。用户要求找对标、选择模仿对象或分析竞争参照时使用。', 'DontBeSilent 商业对标账号与爆款模型拆解。精准提取行业头部竞品的内容模式、变现路径与数据飞轮。'],
    ['诊断如何把已经确定的选题做成好内容。用户要求设计内容、检查文案或改善内容表达时使用。', 'DontBeSilent 商业私域内容生产与转化脚本。设计高转化朋友圈、私信话术与长效商业文案。'],
    ['用维特根斯坦与奥派经济学方法拆解模糊的商业概念。用户要求解释一个词、澄清概念边界或识别概念混用时使用。', 'DontBeSilent 商业认知与第一性原理深度拆解。剖析商业痛点背后的底层逻辑与价值交换规律。'],
    ['自动识别用户是在解决具体商业问题，还是希望全面检查商业模式，并进入对应诊断流程。用户希望拆解业务、检查商业模式或消解具体商业困境时使用。', 'DontBeSilent 商业模式全局诊断。针对业务全链路进行系统体检，定位瓶颈并输出优化方案。'],
    ['诊断短视频开头的问题并生成优化方案。用户要求修改开头、提高开场吸引力或降低开头流失时使用。', 'DontBeSilent 短视频黄金 3 秒 Hook 优化引擎。针对视频开头设计高抓人抓眼球的话题引子，大幅提升完播率。'],
    ['Helps users discover and install agent skills when they ask questions like "how do I do X", "find a skill for X", "is there a skill that can...", or express interest in extending capabilities. This skill should be used when the user is looking for functionality that might exist as an installable skill.', '根据用户当前的业务场景与开发需求，自动检索并推荐最适用的 Agent 技能并提供一键安装与配置建议。'],
    ['去除文本中的 AI 生成痕迹。适用于编辑或审阅文本，使其听起来更自然、更像人类书写。 基于维基百科的"AI 写作特征"综合指南。检测并修复以下模式：夸大的象征意义、 宣传性语言、以 -ing 结尾的肤浅分析、模糊的归因、破折号过度使用、三段式法则、 AI 词汇、否定式排比、过多的连接性短语。', '中文文本深度去味与拟真引擎。消除机械的 AI 翻译腔与套话，生成自然、地道、富有人情味的真实表达。'],
    ['Surfaces relevant instincts during work. Use when starting a task to check if any learned behaviors apply.', '在开工与会话接手时智能加载沉淀的工程本能与业务规范，保持团队协同与产出质量的高度一致。'],
    ['Complete API for Google NotebookLM - full programmatic access including features not in the web UI. Create notebooks, add sources, generate all artifact types, download in multiple formats. Activates on explicit /notebooklm or intent like "create a podcast about X"', 'Google NotebookLM 全功能逆向与官方 API 接口。支持源文档上传、知识库检索与语音播客深度生成。'],
    ['Set reminders using natural language. Automatically creates one-time cron jobs and logs to markdown.', '使用自然语言设置智能定时提醒。自动创建一次性或周期性计划任务并在指定时间唤醒推送。'],
    ['会话记忆技能索引。跳转到 .AI/skills/技能包/会话记忆技能/', '跨端跨会话记忆与长效上下文管理。沉淀关键项目决策与开发断点，实现全平台多端协同无缝接力。'],
    ['Save important project knowledge to memory. Use when user wants to preserve architectural decisions, significant bug fixes, design patterns, or important implementation details for team reference.', '核心项目资产与工程经验一键归档存储。自动提炼架构要点与业务规则并持久化至第二大脑真源层。'],
    ['Search your coding memory. Use when user asks about past work, previous sessions, how something was implemented, what they worked on before, or wants to recall information from earlier sessions.', '历史会话与编码记忆智能精准搜索。极速检索历史沉淀的代码片段、排错方案与项目资产。'],

]);

  var UI_PAIRS = Object.freeze([
    // Independently translated from the current application UI.
    ["Give Feedback", "提供反馈"],
    ["Permission Settings", "权限设置"],
    ["Global Permissions", "全局权限"],
    ["when working", "工作时"],
    ["in this project", "在此项目中"],
    ["Permission Preset", "权限预设"],
    ["Inherit Global", "继承全局设置"],
    ["Plan Review Policy", "计划审核策略"],
    ["Type", "输入"],
    ["and select", "并选择"],
    ["to have the agent generate a plan.", "让智能体生成计划。"],
    ["tokens (", "个 Token（"],
    ["Other Customizations", "其他自定义扩展"],
    ["The breakdown below shows token usage from customizations like rules, skills, and MCP. If a budget is exceeded, large rules are demoted to path pointers and large customizations are excluded automatically.", "下方明细显示规则、技能和 MCP 等自定义扩展的 Token 用量。超出预算时，大型规则会改为路径引用，大型自定义扩展会自动排除。"],

    // Supplemental exact UI labels adapted from good9527 (MIT); see THIRD-PARTY-NOTICES.
    ["Untitled", "未命名"],
    ["See all conversations", "查看全部对话"],
    ["All conversations", "全部对话"],
    ["Recent Conversations", "近期对话"],
    ["Active Conversations", "活跃对话"],
    ["Archived Conversations", "归档对话"],
    ["Clear Conversations", "清除对话记录"],
    ["Clear History", "清除历史记录"],
    ["Clear All", "清除全部"],
    ["Clear all history", "清除全部历史记录"],
    ["Delete All Conversations", "删除所有对话"],
    ["Export Conversation", "导出对话"],
    ["Import Conversation", "导入对话"],
    ["Pin to top", "置顶到顶部"],
    ["Unpin from top", "取消置顶"],
    ["Collapse All", "全部折叠"],
    ["Expand All", "全部展开"],
    ["Collapse sidebar", "折叠侧边栏"],
    ["Expand sidebar", "展开侧边栏"],
    ["Toggle History", "切换历史面板"],
    ["Toggle File Tree", "切换文件树"],
    ["Toggle Artifacts", "切换产物面板"],
    ["Search history...", "搜索历史..."],
    ["Filter by project", "按项目筛选"],
    ["Filter by date", "按日期筛选"],
    ["Sort by Date", "按日期排序"],
    ["Sort by Name", "按名称排序"],
    ["Close Conversation", "关闭对话"],
    ["Rename Conversation", "重命名对话"],
    ["Duplicate Conversation", "复制对话"],
    ["Copy conversation link", "复制对话链接"],
    ["Active Tasks", "进行中任务"],
    ["Completed Tasks", "已完成任务"],
    ["Failed Tasks", "已失败任务"],
    ["Task Details", "任务详情"],
    ["Task Output", "任务输出"],
    ["Task History", "任务历史"],
    ["Task Logs", "任务日志"],
    ["Stop Task", "停止任务"],
    ["Kill Task", "终止任务"],
    ["Running Tasks", "运行中任务"],
    ["No subagents running", "暂无运行中的子智能体"],
    ["No files changed yet", "暂无修改的文件"],
    ["No artifacts generated", "暂无生成的产物"],
    ["No uploads found", "暂无上传文件"],
    ["Artifact Preview", "产物预览"],
    ["Artifact History", "产物历史"],
    ["Download Artifact", "下载产物"],
    ["Open Artifact", "打开产物"],
    ["Save Artifact", "保存产物"],
    ["Copy Artifact", "复制产物"],
    ["View Raw Artifact", "查看原始产物"],
    ["File Changes", "文件变更"],
    ["Split Diff", "分栏差异"],
    ["Unified Diff", "统一差异"],
    ["Inline Diff", "行内差异"],
    ["Next Change", "下一个变更"],
    ["Previous Change", "上一个变更"],
    ["Revert File", "还原文件"],
    ["Revert All Files", "还原全部文件"],
    ["Accept All Changes", "接受全部更改"],
    ["Reject All Changes", "拒绝全部更改"],
    ["MCP Servers", "MCP 服务"],
    ["Add MCP Servers", "添加 MCP 服务"],
    ["Add MCP Server", "添加 MCP 服务"],
    ["Configure MCP Server", "配置 MCP 服务"],
    ["Edit MCP Server", "编辑 MCP 服务"],
    ["Remove MCP Server", "移除 MCP 服务"],
    ["Enable MCP Server", "启用 MCP 服务"],
    ["Disable MCP Server", "禁用 MCP 服务"],
    ["MCP Server Status", "MCP 服务状态"],
    ["MCP Server Settings", "MCP 服务设置"],
    ["MCP Resources", "MCP 资源"],
    ["MCP Prompts", "MCP 提示词模板"],
    ["MCP Error", "MCP 异常"],
    ["No MCP servers configured", "未配置任何 MCP 服务"],
    ["Server Name", "服务名称"],
    ["Server Command", "启动命令"],
    ["Server Arguments", "启动参数"],
    ["Server Environment Variables", "环境变量"],
    ["Server Transport", "传输协议"],
    ["Stdio Transport", "标准输入输出 (Stdio)"],
    ["SSE Transport", "服务端推送事件 (SSE)"],
    ["Server URL", "服务地址 (URL)"],
    ["Connect MCP Server", "连接 MCP 服务"],
    ["Disconnect MCP Server", "断开 MCP 服务"],
    ["Reconnect MCP Server", "重新连接 MCP 服务"],
    ["MCP Server Connected", "MCP 服务已连接"],
    ["MCP Server Disconnected", "MCP 服务已断开"],
    ["MCP Server Connecting...", "MCP 服务连接中..."],
    ["MCP Server Failed", "MCP 服务启动失败"],
    ["Tool Approval Policy", "工具调用审批策略"],
    ["Always Approve Tool", "始终批准该工具"],
    ["Ask Before Executing Tool", "执行工具前询问"],
    ["Block Tool Execution", "阻止该工具执行"],
    ["Tool Call Parameters", "工具调用参数"],
    ["Tool Call Result", "工具调用返回结果"],
    ["Tool Execution Timeout", "工具执行超时"],
    ["Tool Execution Error", "工具执行报错"],
    ["Open Project", "打开项目"],
    ["Add Workspace", "添加工作区"],
    ["Add Folder to Workspace", "添加文件夹到工作区"],
    ["Remove Folder from Workspace", "从工作区移除文件夹"],
    ["Workspace Root", "工作区根目录"],
    ["Multi-Folder Workspace", "多文件夹工作区"],
    ["In Project", "当前项目"],
    ["Switch Project", "切换项目"],
    ["Close Project", "关闭项目"],
    ["Open File", "打开文件"],
    ["Reveal in File Explorer", "在资源管理器中显示"],
    ["Reveal in Finder", "在访达中显示"],
    ["Copy Relative Path", "复制相对路径"],
    ["Refresh File Tree", "刷新文件树"],
    ["New File", "新建文件"],
    ["New Folder", "新建文件夹"],
    ["Rename File", "重命名文件"],
    ["Delete File", "删除文件"],
    ["Save File", "保存文件"],
    ["Save All Files", "保存所有文件"],
    ["Open in Terminal", "在终端中打开"],
    ["Open in External Editor", "在外部编辑器中打开"],
    ["Open in VS Code", "在 VS Code 中打开"],
    ["Open in Antigravity IDE", "在 Antigravity IDE 中打开"],
    ["All models", "全部模型"],
    ["Selected Model", "当前选中模型"],
    ["Switch Model", "切换模型"],
    ["Select a model", "选择一个模型"],
    ["Delete Custom Model", "删除自定义模型"],
    ["Model Parameters", "模型参数配置"],
    ["Model Configuration", "模型配置"],
    ["Temperature", "温度参数"],
    ["Top P", "Top P 采样"],
    ["Top K", "候选数量 (Top K)"],
    ["Max Tokens", "最大 Token 数"],
    ["Max Output Tokens", "最大输出 Token 数"],
    ["Context Window", "上下文窗口"],
    ["Prompt Tokens", "提示词 Token 数"],
    ["Completion Tokens", "补全 Token 数"],
    ["Total Tokens", "总 Token 数"],
    ["Quota Exceeded", "配额已用尽"],
    ["Daily Quota Exceeded", "每日配额已用尽"],
    ["Monthly Quota Exceeded", "每月配额已用尽"],
    ["Rate Limit Reached", "已达到速率限制"],
    ["Please try again later", "请稍后再试"],
    ["Credits Balance", "账户点数余额"],
    ["Available AI Credits", "可用 AI 点数"],
    ["Available AI Credits:", "可用 AI 点数："],
    ["Get More AI Credits", "获取更多 AI 点数"],
    ["Purchase Credits", "购买点数"],
    ["Daily Quota", "每日免费配额"],
    ["Monthly Quota", "每月配额"],
    ["Unlimited", "无限制"],
    ["Refreshes in", "重置倒计时"],
    ["Refreshes daily", "每日重置"],
    ["Refreshes monthly", "每月重置"],
    ["Upgrade Plan", "升级订阅计划"],
    ["Manage Subscription", "管理订阅"],
    ["Disable AI Credit Overages", "关闭点数超额扣费"],
    ["You can upgrade to a Google AI Ultra plan to receive the highest rate limits", "您可以升级至 Google AI Ultra 套餐，获得更高的速率限制。"],
    ["High demand: rate limits currently lowered", "当前请求量较大：速率限制已临时下调"],
    ["Agent Security Settings", "智能体安全设置"],
    ["Agent Team", "智能体协作团队"],
    ["Strict Mode", "严格安全模式"],
    ["Standard Mode", "标准安全模式"],
    ["Permissive Mode", "宽松信任模式"],
    ["Agent always asks for review.", "智能体将始终请求审核。"],
    ["Agent cannot modify files outside of the workspace in strict mode.", "在严格模式下，智能体无法修改工作区外的文件。"],
    ["Agent will always ask to review in strict mode.", "在严格模式下，智能体将始终请求审核。"],
    ["Agent settings and permissions for conversations outside of projects", "适用于非项目对话的智能体全局设置与权限"],
    ["A shell setup script run before every command the agent executes.", "在智能体执行每条命令前运行的 Shell 初始化脚本。"],
    ["Agent Script Command Configuration", "智能体脚本与命令配置"],
    ["Terminal Command Execution Policy", "终端命令执行策略"],
    ["Terminal Execution Policy", "终端执行策略"],
    ["Requires confirmation for dangerous operations", "危险操作需要用户二次确认"],
    ["File Access Policy", "文件访问策略"],
    ["Network Access Policy", "网络访问策略"],
    ["Read-only mode", "只读模式"],
    ["Read and Write", "读写模式"],
    ["Restricted Access", "受限访问"],
    ["Blocked by Policy", "已被安全策略拦截"],
    ["Allow", "允许"],
    ["Deny", "拒绝"],
    ["Ask before running", "运行前询问"],
    ["Ask every time", "每次都询问"],
    ["Never ask", "从不询问"],
    ["Confirm Command Execution", "确认命令执行"],
    ["Do you want to run this command?", "您确定要执行此终端命令吗？"],
    ["Dangerous Command Detected", "检测到高危命令"],
    ["This command may modify system files or execute external binaries.", "此命令可能会修改系统文件或执行外部二进制程序，请谨慎核对。"],
    ["Theme Mode", "配色主题模式"],
    ["Follow System Theme", "跟随系统主题"],
    ["Follow System", "跟随系统"],
    ["High Contrast Theme", "高对比度主题"],
    ["Color Theme", "颜色主题"],
    ["Font Family", "界面字体"],
    ["Font Size", "字号大小"],
    ["Editor Font Size", "编辑器字号"],
    ["Terminal Font Size", "终端字号"],
    ["Line Height", "行高"],
    ["Zoom Factor", "缩放比例"],
    ["Custom CSS", "自定义样式表 (CSS)"],
    ["Keybindings", "按键绑定"],
    ["Open Documentation", "打开官方文档"],
    ["Open Logs Folder", "打开日志目录"],
    ["Restart Language Server", "重启语言服务端"],
    ["Toggle Full Screen", "切换全屏"],
    ["Keep Computer Awake", "防止计算机休眠"],
    ["Run in Background", "在后台保持运行"],
    ["Minimize to Tray", "最小化到系统托盘"],
    ["Close to Tray", "关闭时最小化到托盘"],
    ["Start at Login", "开机自启动"],
    ["Describe your feature request...", "请详细描述您期待的新功能或改进建议..."],
    ["Attach Screenshots", "附加截图"],
    ["Attach Diagnostic Logs", "附带诊断日志"],
    ["Submit Feedback", "提交反馈"],
    ["Thank you for your feedback!", "感谢您的宝贵反馈！"],
    ["Report an Issue", "报告问题"],
    ["Community Discord", "加入 Discord 社区"],
    ["Privacy Policy", "隐私政策"],
    ["About Antigravity", "关于 Antigravity"],
    ["Documentation", "官方文档"],
    ["Docs", "官方文档"],
    ["Version", "客户端版本"],
    ["Setting up...", "正在初始化设置..."],
    ["Welcome to Antigravity", "欢迎使用 Antigravity"],
    ["Antigravity has been redesigned to put agents first with new capabilities. If you'd still like a code editor, you can download it as a separate app named Antigravity IDE.", "Antigravity 现已全面升级为以智能体为核心的全新架构。如果您仍需传统的代码编辑功能，可以单独下载名为 Antigravity IDE 的配套编辑器。"],
    ["Installing IDE...", "正在安装 IDE..."],
    ["IDE Installation Complete", "IDE 安装完成"],
    ["IDE Installation Failed", "IDE 安装失败"],
    ["Launch IDE", "启动 IDE"],
    ["Skip for now", "暂时跳过"],
    ["Finish", "完成"],
    ["Continue", "继续"],
    ["New Window", "新建窗口"],
    ["Close Window", "关闭窗口"],
    ["Zoom", "缩放"],
    ["Bring All to Front", "前置全部窗口"],
    ["Cut", "剪切"],
    ["Paste", "粘贴"],
    ["Paste and Match Style", "粘贴并匹配样式"],
    ["Select All", "全选"],
    ["Undo", "撤销"],
    ["Redo", "重做"],
    ["Speech", "语音"],
    ["Start Dictation", "开始听写"],
    ["Emoji & Symbols", "表情与特殊符号"],
    ["Hide Antigravity", "隐藏 Antigravity"],
    ["Hide Others", "隐藏其他应用"],
    ["Quit Antigravity", "退出 Antigravity"],
    ["Exit", "退出"],
    ["Restart", "重启"],
    ["Restart Antigravity", "重启 Antigravity"],
    ["Updates", "软件更新"],
    ["Checking for Updates...", "正在检查更新..."],
    ["Downloading Update...", "正在下载更新..."],
    ["Update Available", "发现新版本"],
    ["Update Downloaded", "更新已就绪"],
    ["Restart to Update", "重启以完成更新"],
    ["Up to date", "已是最新版本"],
    ["No updates available", "当前已是最新版本，暂无可用更新"],
    ["Enable Desktop Notifications", "启用桌面系统通知"],
    ["Sound Effects", "操作音效"],
    ["No agent running", "暂无运行中的智能体"],
    ["agents running", "个智能体正在运行"],
    ["Review this code", "审核此代码"],
    ["Review my design", "审核我的设计"],
    ["Review Step", "审核步骤"],
    ["Accept", "接受"],
    ["Reject", "拒绝"],
    ["Accept Step", "接受步骤"],
    ["Reject Step", "拒绝步骤"],
    ["Accept All", "接受全部"],
    ["Reject All", "拒绝全部"],
    ["Action Required", "需要操作"],
    ["User Approval Required", "需要用户确认审批"],
    ["Apply Changes", "应用更改"],
    ["Discard", "放弃"],
    ["Discard Changes", "放弃更改"],
    ["Revert", "还原"],
    ["Revert Changes", "撤销更改"],
    ["Keep Changes", "保留更改"],
    ["Compare Changes", "对比差异"],
    ["Modified", "已修改"],
    ["Created", "已新建"],
    ["Renamed", "已重命名"],
    ["Pending Review", "等待审核中"],
    ["Approved", "已批准"],
    ["Rejected", "已拒绝"],
    ["Thinking...", "思考中..."],
    ["Planning...", "规划中..."],
    ["Executing...", "执行中..."],
    ["Searching...", "搜索中..."],
    ["Writing files...", "写入文件中..."],
    ["Running command...", "执行命令中..."],
    ["Agent finished", "智能体已完成"],
    ["Agent finished.", "智能体已完成。"],
    ["Agent execution finished", "智能体执行完成"],
    ["Agent execution failed", "智能体执行失败"],
    ["Agent execution failed.", "智能体执行失败。"],
    ["Agent paused", "智能体已暂停"],
    ["Agent stopped", "智能体已停止"],
    ["Stop generating", "停止生成"],
    ["Regenerate", "重新生成"],
    ["Regenerate Response", "重新生成回复"],
    ["Try Again", "再次尝试"],
    ["Copied!", "已复制！"],
    ["Copied to clipboard", "已复制到剪贴板"],
    ["Copy code", "复制代码"],
    ["Copy message", "复制消息"],
    ["Ask a question or provide instructions...", "请输入您的问题或具体指令..."],
    ["Type a message...", "输入消息..."],
    ["Type / for commands...", "输入 / 查看可用命令..."],
    ["Add to Chat", "添加到对话"],
    ["Add files to context", "添加文件到上下文"],
    ["Mention file or folder", "提及文件或文件夹"],
    ["Attach File", "附加文件"],
    ["Attach Image", "附加图片"],
    ["Drop files here to upload", "拖拽文件至此处上传"],
    ["Upload File", "上传文件"],
    ["Upload Folder", "上传文件夹"],
    ["New Task", "新建任务"],
    ["Reset", "重置"],
    ["OK", "确定"],
    ["Confirm", "确认"],
    ["Done", "完成"],
    ["Success", "成功"],
    ["Error", "错误"],
    ["Warning", "警告"],
    ["Info", "提示"],
    ["Details", "详细信息"],
    ["Show Details", "显示详情"],
    ["Hide Details", "隐藏详情"],
    ["Absolute path to the Chrome/Chromium executable", "Chrome/Chromium 可执行文件的绝对路径"],
    ["Receive product updates, tips, and promotions from Google Antigravity via email", "通过电子邮件接收来自 Google Antigravity 的产品更新、使用技巧与优惠信息"],
    ["Model List", "模型列表"],
    ["Browser Assistant", "浏览器助手"],
    ["Always Continue", "始终继续"],
    ["Device Name", "设备名称"],
    ["Scan the code to open this device in Remote Control, or copy link.", "扫描二维码以在远程控制中打开此设备，或复制链接。"],
    ["System Theme", "跟随系统主题"],
    ["Add MCP +", "添加 MCP +"],
    ["Gemini 3.5 Flash will be taken down soon", "Gemini 3.5 Flash 即将下线"],
    ["Update and switch to Gemini 3.7 Flash for even better performance and efficiency!", "请更新并切换至 Gemini 3.7 Flash，以获得更高的性能与效率！"],
    ["MCP Disconnected", "MCP 已断开"],
    ["MCP Connected", "MCP 已连接"],
    ["Model Selection", "模型选择"],
    ["Available Models", "可用模型"],
    ["Custom Model", "自定义模型"],
    ["API Key", "API 密钥"],
    ["Enter API Key", "输入 API 密钥"],
    ["API Key is valid", "API 密钥有效"],
    ["API Key is invalid", "API 密钥无效"],
    ["Save API Key", "保存 API 密钥"],
    ["Token Count", "Token 计数"],
    ["Tokens Used", "已用 Token"],
    ["Frequency Penalty", "频率惩罚"],
    ["Presence Penalty", "存在惩罚"],
    ["System Prompt", "系统提示词"],
    ["System Instructions", "系统指令"],
    ["User Prompt", "用户提示词"],
    ["Controls the actions the agent can take.", "控制智能体可执行的操作。"],
    ["Tool Permissions", "工具权限"],
    ["Modify permissions for file, terminal, and MCP tools.", "修改文件、终端与 MCP 工具的访问权限。"],
    ["Whether the agent asks you to review its documents.", "智能体是否要求您审核其生成的产物文档。"],
    ["allowed commands outside the sandbox.", "允许在沙箱外部执行的命令。"],
    ["allowed and denied URLs for browser actuation.", "允许和禁止浏览器执行自动化操作的 URL 地址。"],
    ["Browser settings have moved", "浏览器设置已迁移"],
    ["Browser settings have moved to the Browser section of General settings. Go to General settings", "浏览器设置现已迁移至“常规设置”中的“浏览器”区域。前往常规设置"],
    ["Browser settings have moved to the Browser section of General settings.", "浏览器设置现已迁移至“常规设置”中的“浏览器”区域。"],
    ["Go to General settings", "前往常规设置"],
    ["Preferences", "首选项"],
    ["Reload", "重新加载"],
    ["Force Reload", "强制重新加载"],
    ["Actual Size", "实际大小"],
    ["Indexing codebase...", "代码库索引中..."],
    ["Thinking Process", "思考过程"],
    ["View changes", "查看代码变更"],
    ["Close Tab", "关闭标签页"],
    ["Split Editor Right", "向右拆分编辑器"],
    ["Split Editor Down", "向下拆分编辑器"],
    ["Antigravity will always use your model quota first before using AI credits.", "Antigravity 始终会优先消耗模型配额，然后再使用 AI 点数。"],
    ["Enable credits overage", "开启点数超额扣费"],
    ["AI credits", "AI 点数"],
    ["your model quota and credits.", "您的模型配额与点数。"],
    ["your model quota and credits", "您的模型配额与点数"],
    ["You can upgrade to a Google AI Pro plan to receive higher rate limits.", "您可以升级至 Google AI Pro 套餐以获取更高的速率限制。"],
    ["You have used some of your weekly limit, it will fully refresh in", "已使用部分每周配额，将在"],
    ["You have used all of your weekly limit, it will fully refresh in", "每周配额已全部用尽，将在"],
    ["You have used some of your 5-hour limit, it will fully refresh in", "已使用部分 5 小时配额，将在"],
    ["You have used all of your 5-hour limit, it will fully refresh in", "5 小时配额已全部用尽，将在"],
    ["You have used some of your daily limit, it will fully refresh in", "已使用部分每日配额，将在"],
    ["You have used all of your daily limit, it will fully refresh in", "每日配额已全部用尽，将在"],
    ["Choose a predefined security preset for the agent.", "为智能体选择预设的安全策略。"],
    ["This controls terminal auto-execution policy, and file access policy.", "该选项控制终端自动执行策略以及文件访问权限。"],
    ["Configure allowed commands outside the sandbox", "配置允许在沙箱环境外部执行的命令列表"],
    ["allowed commands outside the sandbox", "允许在沙箱外部执行的命令"],
    ["Configure allowed and denied paths for file reads and writes", "配置文件读取和写入的允许与拒绝路径"],
    ["allowed and denied paths for file reads and writes.", "文件读取和写入的允许与拒绝路径。"],
    ["allowed and denied paths for file reads and writes", "文件读取和写入的允许与拒绝路径"],
    ["Configure allowed and denied URLs for reading", "配置允许和禁止读取的网络 URL 地址"],
    ["allowed and denied URLs for reading.", "允许和禁止读取的网络 URL 地址。"],
    ["allowed and denied URLs for reading", "允许和禁止读取的网络 URL 地址"],
    ["Configure allowed and denied URLs for browser actuation", "配置允许和禁止浏览器执行自动化操作的 URL 地址"],
    ["allowed and denied URLs for browser actuation", "允许和禁止浏览器执行自动化操作的 URL 地址"],
    ["Waiting for input", "等待输入"],
    ["Waiting for input...", "等待输入中..."],
    ["Running task", "正在执行任务"],
    ["Running task...", "正在执行任务..."],
    ["Executing command", "正在执行命令"],
    ["Executing command...", "正在执行命令..."],
    ["Running subagent", "正在运行子智能体"],
    ["Running subagent...", "正在运行子智能体..."],
    ["Terminals 0", "终端 0"],
    ["Ask anything, @ to mention files, / for actions", "问我任何问题，用 @ 提及文件，用 / 执行动作"],
    ["Ask a quick question without interrupting the main conversation", "快速提问一个简短问题，无需中断主对话"],
    ["Run until the specified goal is completely finished", "持续执行，直到指定目标全部完成"],
    ["Compact the conversation now (summarize history to free up the context window)", "立即压缩上下文（总结对话历史以释放上下文窗口）"],
    ["Run an instruction on a recurring schedule or as a one-time timer.", "按定时周期（Cron）或单次计时器执行指定指令。"],
    ["Run an instruction on a recurring schedule or as a one-time timer", "按定时周期（Cron）或单次计时器执行指定指令"],
    ["Invoke a browser agent for web tasks", "调用浏览器智能体处理网页任务"],
    ["Plan carefully before executing a task.", "在执行复杂任务前，进行严密细致的分步规划。"],
    ["Plan carefully before executing a task", "在执行复杂任务前，进行严密细致的分步规划"],
    ["Interview me to align on a plan.", "对我进行交互式提问访谈，对齐并完善设计方案。"],
    ["Interview me to align on a plan", "对我进行交互式提问访谈，对齐并完善设计方案"],
    ["Invoke a team of agents to autonomously tackle large projects.", "调用智能体团队，自主协作处理大型项目。"],
    ["Invoke a team of agents to autonomously tackle large projects", "调用智能体团队，自主协作处理大型项目"],
    ["Reflect on recent successes or corrections to capture reusable skills or rules.", "反思近期成功经验或纠正记录，沉淀为可复用的技能或规则。"],
    ["Reflect on recent successes or corrections to capture reusable skills or rules", "反思近期成功经验或纠正记录，沉淀为可复用的技能或规则"],
    ["Invoke the Boost multi-agent orchestrator for complex tasks.", "调用 Boost 多智能体编排器处理复杂任务。"],
    ["Invoke the Boost multi-agent orchestrator for complex tasks", "调用 Boost 多智能体编排器处理复杂任务"],
    ["Interactive guide to design and create a scheduled background automation.", "交互式引导设计并创建计划后台自动化任务。"],
    ["Interactive guide to design and create a scheduled background automation", "交互式引导设计并创建计划后台自动化任务"],
    ["How to manage and create plugins — namespaced bundles of skills, agents, rules, MCP servers and hooks that install, enable and disable as a single unit.", "管理与创建插件——包含技能、智能体、规则、MCP 服务与钩子的集成包。"],
    ["How to manage and create plugins — namespaced bundles of skills, agents, rules, MCP servers and hooks that install, enable and disable as a single unit", "管理与创建插件——包含技能、智能体、规则、MCP 服务与钩子的集成包"],
    ["Commands", "命令"],
    ["Slash Commands", "快捷斜杠命令"],

    ["Automations", "自动化任务"],
  [
    "Inherit General",
    "继承常规设置"
  ],
  [
    "Local Permissions",
    "本地权限"
  ],
  [
    "Also includes",
    "在此项目中工作时还包括"
  ],
  [
    "when working in this project.",
    "。"
  ],
  [
    "to be installed.",
    "才能运行。"
  ],
  [
    "Danger Zone",
    "危险区域"
  ],
  [
    "Permanently delete",
    "永久删除"
  ],
  [
    "including",
    "包括"
  ],
  [
    "tokens)",
    "个 Token）"
  ],
  [
    ".",
    "。"
  ],
  [
    "Display and preserve intermediate thinking steps",
    "显示并保留中间思考步骤"
  ],
  [
    "Import feature is not available in this context.",
    "当前上下文中无法使用导入功能。"
  ],
  [
    "Require review for all browser script execution.",
    "所有浏览器脚本执行都需要审核。"
  ],
  [
    "URLs the agent can actuate on using the browser.",
    "智能体可通过浏览器执行操作的 URL。"
  ],
  [
    "Commands the agent can run outside the sandbox.",
    "智能体可在沙盒外运行的命令。"
  ],
  [
    "Configure allowed commands outside the sandbox.",
    "配置允许在沙盒外运行的命令。"
  ],
  [
    "Curated collection of agent skills for science.",
    "为科学领域精心挑选的智能体技能集合。"
  ],
  [
    "Select light, dark, or inherit system settings.",
    "选择浅色、深色或继承系统设置。"
  ],
  [
    "URLs the agent can read or open in the browser.",
    "智能体可以在浏览器中读取或打开的 URL。"
  ],
  [
    "Configure allowed and denied URLs for reading.",
    "配置允许和拒绝读取的 URL。"
  ],
  [
    "Continue conversation in the current workspace",
    "在当前工作区继续对话"
  ],
  [
    "Agent needs permission to execute JavaScript",
    "智能体需要权限才能执行 JavaScript"
  ],
  [
    "Conversation copied as Markdown to clipboard",
    "对话已作为 Markdown 复制到剪贴板"
  ],
  [
    "Please list the steps to reproduce the issue",
    "请列出复现此问题的步骤"
  ],
  [
    "Quickly add and update imports with Tab key.",
    "按下 Tab 键快速添加和更新导入。"
  ],
  [
    "Search conversations (by name or Cascade ID)",
    "搜索对话（按名称或 Cascade ID）"
  ],
  [
    "% of the customization budget is available.",
    "% 的自定义预算可用。"
  ],
  [
    "broadcast Go Live, Click to run live server",
    "广播 Go Live，点击运行实时服务器"
  ],
  [
    "Configure the browser subagent. It requires",
    "配置浏览器子智能体。它需要"
  ],
  [
    "Configure when follow-up messages are sent.",
    "配置何时发送后续消息。"
  ],
  [
    "No customizations found for this workspace.",
    "此工作区没有找到自定义内容。"
  ],
  [
    "to back up your data and run the migration.",
    "备份数据并运行迁移。"
  ],
  [
    "Work with local agents from another device.",
    "从其他设备连接并使用本地智能体。"
  ],
  [
    "Antigravity would like to use the browser.",
    "Antigravity 想要使用浏览器。"
  ],
  [
    "Confirmation required to execute this step",
    "执行此步骤需要确认"
  ],
  [
    "Folder no longer exists or is unavailable.",
    "文件夹不再存在或不可用。"
  ],
  [
    "Show suggestions when typing in the editor",
    "在编辑器中输入时显示建议"
  ],
  [
    "Allow Tab to access .gitignore exclusions",
    "Tab 键访问 .gitignore 排除文件"
  ],
  [
    "Ask anything, @ to mention, / for actions",
    "想问什么都可以，@ 引用，/ 执行动作"
  ],
  [
    "Interrupt the agent and send immediately.",
    "打断智能体并立即发送。"
  ],
  [
    "Configure AI models and view your quota.",
    "配置 AI 模型并查看额度。"
  ],
  [
    "Terminal commands the agent can execute.",
    "智能体可执行的终端命令。"
  ],
  [
    "Block all browser JavaScript execution.",
    "阻止所有浏览器 JavaScript 执行。"
  ],
  [
    "Explain and Fix in Current Conversation",
    "在当前对话中解释并修复"
  ],
  [
    "GCP Project ID for enterprise features.",
    "适用于企业级功能的 GCP 项目 ID。"
  ],
  [
    "Local permissions have higher priority.",
    "本地权限优先级更高。"
  ],
  [
    "Manually customize individual settings.",
    "手动自定义各项设置。"
  ],
  [
    "Allow/deny specific terminal commands.",
    "允许或拒绝指定终端命令。"
  ],
  [
    "Google Drive integration not available",
    "Google 云端硬盘集成不可用"
  ],
  [
    "No (tell the agent what to do instead)",
    "否（告诉智能体改做什么）"
  ],
  [
    "Manage your notification preferences.",
    "管理您的通知偏好设置。"
  ],
  [
    "Outside of folders file access policy",
    "文件夹外访问策略"
  ],
  [
    "Select where to open the conversation",
    "选择在哪里打开对话"
  ],
  [
    "Configure allowed terminal commands.",
    "配置允许的终端命令。"
  ],
  [
    "Manage your model quota and credits.",
    "管理您的模型额度与积分。"
  ],
  [
    "(tell the agent what to do instead)",
    "（告诉智能体改做什么）"
  ],
  [
    "Browser JavaScript Execution Policy",
    "浏览器 JavaScript 执行策略"
  ],
  [
    "By using this app, you agree to its",
    "使用本应用即表示你同意其"
  ],
  [
    "Describe the bug you encountered...",
    "描述您遇到的错误..."
  ],
  [
    "Enter command (e.g., git, blaze)...",
    "输入命令（例如 git、blaze）..."
  ],
  [
    "Loading workspace customizations...",
    "正在加载工作区自定义项..."
  ],
  [
    "Queue until after the current turn.",
    "排队直到当前轮次结束后发送。"
  ],
  [
    "Set how fast Tab suggestions appear",
    "设置 Tab 建议的显示速度"
  ],
  [
    "Build with Antigravity IDE Plugins",
    "使用 Antigravity IDE 插件构建"
  ],
  [
    "Search for files in the project...",
    "在项目中搜索文件..."
  ],
  [
    "Initializing virtual environments",
    "正在初始化虚拟环境"
  ],
  [
    "Open Agent panel on window reload",
    "窗口重新加载时打开智能体面板"
  ],
  [
    "Manage Antigravity app settings.",
    "管理 Antigravity 应用设置。"
  ],
  [
    "Select one of the three options.",
    "选择以下三个选项之一。"
  ],
  [
    "Set the speed of tab suggestions",
    "设置 Tab 建议的显示速度"
  ],
  [
    "Agent Non-Workspace File Access",
    "智能体非工作区文件访问"
  ],
  [
    "Enter file or directory path...",
    "输入文件或目录路径..."
  ],
  [
    "Search by name or Cascade ID...",
    "按名称或 Cascade ID 搜索..."
  ],
  [
    "Terminal Command Auto Execution",
    "终端命令自动执行"
  ],
  [
    "Welcome to the new Antigravity!",
    "欢迎使用新版 Antigravity！"
  ],
  [
    "Attach a screenshot (optional)",
    "附加屏幕截图（可选）"
  ],
  [
    "Attach Antigravity server logs",
    "附加 Antigravity 服务端日志"
  ],
  [
    "Enable notifications for Agent",
    "为智能体启用通知"
  ],
  [
    "Getting started with a Project",
    "开始使用项目"
  ],
  [
    "Refresh quota and credits data",
    "刷新额度和积分数据"
  ],
  [
    "Terminal & Tooling Permissions",
    "终端与工具权限"
  ],
  [
    "Enable Sandbox Mode (Preview)",
    "启用沙盒模式（预览）"
  ],
  [
    "New Conversation in Workspace",
    "在工作区中新建对话"
  ],
  [
    "Undo changes up to this point",
    "撤销到此处的更改"
  ],
  [
    "Allow List Terminal Commands",
    "终端命令允许列表"
  ],
  [
    "Auto-Expand Changes Overview",
    "自动展开更改概览"
  ],
  [
    "Download the Antigravity IDE",
    "下载 Antigravity IDE"
  ],
  [
    "Enter tool name or server...",
    "输入工具名称或服务器..."
  ],
  [
    "Manage application settings.",
    "管理应用设置。"
  ],
  [
    "Select Model to Send Message",
    "选择用于发送消息的模型"
  ],
  [
    "Steps to reproduce the issue",
    "复现问题的步骤"
  ],
  [
    "Allow running this command?",
    "允许运行此命令？"
  ],
  [
    "Confirm Browser Interaction",
    "确认浏览器交互"
  ],
  [
    "Deny List Terminal Commands",
    "终端命令拒绝列表"
  ],
  [
    "Enter avatar URL (optional)",
    "输入头像 URL（可选）"
  ],
  [
    "Explore the new Antigravity",
    "探索新版 Antigravity"
  ],
  [
    "Generate CitC Workspace VCS",
    "生成 CitC 工作区 VCS"
  ],
  [
    "New Conversation in Project",
    "在项目中新建对话"
  ],
  [
    "Paths the agent can modify.",
    "智能体可修改的路径。"
  ],
  [
    "Agent Auto-Fix Lint Errors",
    "智能体自动修复 Lint 错误"
  ],
  [
    "Click to copy full command",
    "点击复制完整命令"
  ],
  [
    "Copy conversation markdown",
    "复制对话 Markdown"
  ],
  [
    "Copy full URL to clipboard",
    "复制完整 URL 到剪贴板"
  ],
  [
    "Search MCP servers by name",
    "按名称搜索 MCP 服务器"
  ],
  [
    "Archive this conversation",
    "归档此对话"
  ],
  [
    "Browser User Profile Path",
    "浏览器用户资料路径"
  ],
  [
    "Build With Google Plugins",
    "使用 Google 插件构建"
  ],
  [
    "Built with Google Plugins",
    "使用 Google 插件构建"
  ],
  [
    "Enable AI Credit Overages",
    "启用 AI 积分超额使用"
  ],
  [
    "Enter bot name (optional)",
    "输入机器人名称（可选）"
  ],
  [
    "Five Hour Limit Remaining",
    "剩余 5 小时限额"
  ],
  [
    "Open Conversation History",
    "打开对话历史"
  ],
  [
    "Paths the agent can read.",
    "智能体可读取的路径。"
  ],
  [
    "Project validation failed",
    "项目验证失败"
  ],
  [
    "Project-Specific Settings",
    "项目专属设置"
  ],
  [
    "Select Python Interpreter",
    "选择 Python 解释器"
  ],
  [
    "Toggle Agent (Ctrl+Alt+B)",
    "切换智能体 (Ctrl+Alt+B)"
  ],
  [
    "Any relevant information",
    "任何相关信息"
  ],
  [
    "Commands Outside Sandbox",
    "沙箱外命令"
  ],
  [
    "Current sidebar grouping",
    "当前侧边栏分组方式"
  ],
  [
    "Editor-Specific Settings",
    "编辑器专属设置"
  ],
  [
    "Enable Shell Integration",
    "启用 Shell 集成"
  ],
  [
    "Import AI Studio Project",
    "导入 AI Studio 项目"
  ],
  [
    "Launching the browser...",
    "正在启动浏览器..."
  ],
  [
    "No MCP servers installed",
    "未安装 MCP 服务器"
  ],
  [
    "Open Conversation Picker",
    "打开对话选择器"
  ],
  [
    "Project name. E.g. Tasks",
    "项目名称，例如 Tasks"
  ],
  [
    "Workspace Command Access",
    "工作区命令访问"
  ],
  [
    "Your Plan: Google AI Pro",
    "你的套餐：Google AI Pro"
  ],
  [
    "Advanced Command Access",
    "高级命令访问"
  ],
  [
    "Automatic update checks",
    "自动检查更新"
  ],
  [
    "Back to Scheduled Tasks",
    "返回定时任务"
  ],
  [
    "Browser Actuation Rules",
    "浏览器操作规则"
  ],
  [
    "Deny setting up browser",
    "拒绝设置浏览器"
  ],
  [
    "Edit Conversation Title",
    "编辑对话标题"
  ],
  [
    "Enable Sounds for Agent",
    "启用智能体提示音"
  ],
  [
    "Marketplace Gallery URL",
    "插件市场列表 URL"
  ],
  [
    "Open Keyboard Shortcuts",
    "打开键盘快捷键"
  ],
  [
    "Open System Preferences",
    "打开系统设置"
  ],
  [
    "Open Workspace Selector",
    "打开工作区选择器"
  ],
  [
    "Queued Message Delivery",
    "排队消息发送"
  ],
  [
    "Search conversations...",
    "搜索对话..."
  ],
  [
    "Standalone Conversation",
    "独立对话"
  ],
  [
    "Artifact Review Policy",
    "产物审核策略"
  ],
  [
    "Auto-Open Edited Files",
    "自动打开已编辑文件"
  ],
  [
    "Background Task Output",
    "后台任务输出"
  ],
  [
    "Copy the trajectory ID",
    "复制轨迹 ID"
  ],
  [
    "Edit permission target",
    "编辑权限目标"
  ],
  [
    "Highlight After Accept",
    "接受后高亮"
  ],
  [
    "Loading MCP servers...",
    "正在加载 MCP 服务器..."
  ],
  [
    "Loading token usage...",
    "正在加载 Token 用量..."
  ],
  [
    "Marketplace Search URL",
    "插件市场列表 URL"
  ],
  [
    "Model Context Protocol",
    "模型上下文协议 (MCP)"
  ],
  [
    "My Custom Gemini Model",
    "我的自定义 Gemini 模型"
  ],
  [
    "No more older messages",
    "没有更早的消息了"
  ],
  [
    "Open Browser (Preview)",
    "打开浏览器 (预览)"
  ],
  [
    "Opening URL in Browser",
    "正在浏览器中打开 URL"
  ],
  [
    "quota and credits data",
    "额度和积分数据"
  ],
  [
    "Search across files...",
    "跨文件搜索..."
  ],
  [
    "Show Selection Actions",
    "显示选择操作"
  ],
  [
    "Toggle Developer Tools",
    "切换开发者工具"
  ],
  [
    "Toggle Voice Recording",
    "切换录音"
  ],
  [
    "Weekly Limit Remaining",
    "剩余周额度"
  ],
  [
    "Actuation Permissions",
    "操作权限"
  ],
  [
    "Allow in Conversation",
    "在本次对话中允许"
  ],
  [
    "Auto-Execution Policy",
    "自动执行策略"
  ],
  [
    "Claude and GPT Models",
    "Claude 和 GPT 模型"
  ],
  [
    "Enable Remote Control",
    "启用远程控制"
  ],
  [
    "Experimental features",
    "实验性功能"
  ],
  [
    "Installed MCP Servers",
    "已安装 MCP 服务器"
  ],
  [
    "Model quota exhausted",
    "模型额度已耗尽"
  ],
  [
    "Notification Settings",
    "通知设置"
  ],
  [
    "Open project settings",
    "打开项目设置"
  ],
  [
    "Opened URL in Browser",
    "已在浏览器中打开 URL"
  ],
  [
    "Regroup Google3 Chats",
    "重新整理 Google3 聊天"
  ],
  [
    "Start Voice Recording",
    "开始语音录制"
  ],
  [
    "Suggestions in Editor",
    "编辑器内联建议"
  ],
  [
    "Toggle Auxiliary Pane",
    "切换辅助面板"
  ],
  [
    "Toggle Model Selector",
    "切换模型选择器"
  ],
  [
    "Workspace File Access",
    "工作区文件访问"
  ],
  [
    "[Dev] GCP Project ID",
    "[开发] GCP 项目 ID"
  ],
  [
    "Advanced File Access",
    "高级文件访问"
  ],
  [
    "Agent Auto-Fix Lints",
    "智能体自动修复 Lint 错误"
  ],
  [
    "Archive Conversation",
    "归档对话"
  ],
  [
    "Conversation History",
    "对话历史"
  ],
  [
    "Enable Browser Tools",
    "启用浏览器工具"
  ],
  [
    "Enter URL pattern...",
    "输入 URL 匹配模式..."
  ],
  [
    "Go Explorer: Refresh",
    "Go 资源管理器: 刷新"
  ],
  [
    "Marketplace Item URL",
    "插件市场单项 URL"
  ],
  [
    "Network Access Rules",
    "网络访问规则"
  ],
  [
    "No conversations yet",
    "暂无对话"
  ],
  [
    "Open Agent on Reload",
    "重新加载时打开智能体"
  ],
  [
    "Open Command Palette",
    "打开命令面板"
  ],
  [
    "Pinned Conversations",
    "已固定对话"
  ],
  [
    "Restore Conversation",
    "恢复对话"
  ],
  [
    "Search all convos...",
    "搜索全部对话..."
  ],
  [
    "Stop Voice Recording",
    "停止语音录制"
  ],
  [
    "Tab Gitignore Access",
    "Tab 键访问 .gitignore 排除文件"
  ],
  [
    "Yes, allow this time",
    "是，仅允许本次"
  ],
  [
    "Advanced Web Access",
    "高级网页访问"
  ],
  [
    "Agent security mode",
    "智能体安全模式"
  ],
  [
    "Conversation picker",
    "对话选择器"
  ],
  [
    "Delete Conversation",
    "删除对话"
  ],
  [
    "Follow the guide at",
    "请按照以下指南"
  ],
  [
    "Loading Antigravity",
    "正在加载 Antigravity"
  ],
  [
    "Model quota reached",
    "模型额度已达上限"
  ],
  [
    "Modern Web Guidance",
    "现代 Web 开发指南"
  ],
  [
    "Network Permissions",
    "网络权限"
  ],
  [
    "Open Project Picker",
    "打开项目选择器"
  ],
  [
    "Open System Browser",
    "在系统浏览器中打开"
  ],
  [
    "Other Conversations",
    "其他对话"
  ],
  [
    "Parent Conversation",
    "父对话"
  ],
  [
    "Pinned Conversation",
    "已固定对话"
  ],
  [
    "Add Scheduled Task",
    "添加定时任务"
  ],
  [
    "Alphabetical (A-Z)",
    "按字母顺序 (A-Z)"
  ],
  [
    "Analyzing Task Log",
    "正在分析任务日志"
  ],
  [
    "Any error messages",
    "任何错误信息"
  ],
  [
    "Autocomplete Speed",
    "补全速度"
  ],
  [
    "Best of N Settings",
    "Best of N 设置"
  ],
  [
    "Chrome Binary Path",
    "Chrome 可执行文件路径"
  ],
  [
    "Conversation Width",
    "对话宽度"
  ],
  [
    "Copy trajectory ID",
    "复制轨迹 ID"
  ],
  [
    "Create New Project",
    "创建新项目"
  ],
  [
    "Creating a Project",
    "正在创建项目"
  ],
  [
    "Delete Permanently",
    "永久删除"
  ],
  [
    "Keyboard Shortcuts",
    "键盘快捷键"
  ],
  [
    "New Scheduled Task",
    "新建定时任务"
  ],
  [
    "Outside of Project",
    "项目外"
  ],
  [
    "Previous Worktrees",
    "以前的工作树"
  ],
  [
    "Proceed in Sandbox",
    "在沙箱中继续"
  ],
  [
    "Search projects...",
    "搜索项目..."
  ],
  [
    "Sort Conversations",
    "排序对话"
  ],
  [
    "Steps to Reproduce",
    "复现步骤"
  ],
  [
    "Unpin Conversation",
    "取消固定对话"
  ],
  [
    "Verbose Agent Chat",
    "详细智能体聊天"
  ],
  [
    "Workspace Settings",
    "工作区设置"
  ],
  [
    "Add to Chat/Quote",
    "添加到聊天/引用"
  ],
  [
    "Advanced Settings",
    "高级设置"
  ],
  [
    "Analyzed Task Log",
    "已分析任务日志"
  ],
  [
    "Archive / Restore",
    "归档 / 恢复"
  ],
  [
    "Automatic Updates",
    "自动检查更新"
  ],
  [
    "Build With Google",
    "使用 Google 构建"
  ],
  [
    "Check for Updates",
    "检查更新"
  ],
  [
    "Copy Project Name",
    "复制项目名称"
  ],
  [
    "Copy sign-in link",
    "复制登录链接"
  ],
  [
    "Copy to clipboard",
    "复制到剪贴板"
  ],
  [
    "Edit Custom Model",
    "编辑自定义模型"
  ],
  [
    "Expected behavior",
    "预期行为"
  ],
  [
    "File Access Rules",
    "文件访问规则"
  ],
  [
    "No agents running",
    "没有正在运行的智能体"
  ],
  [
    "No Model Selected",
    "未选择模型"
  ],
  [
    "No projects found",
    "未找到项目"
  ],
  [
    "Open Conversation",
    "打开对话"
  ],
  [
    "Previous Pane Tab",
    "上一个面板标签页"
  ],
  [
    "Record voice memo",
    "录制语音备忘"
  ],
  [
    "Select one of the",
    "选择以下"
  ],
  [
    "Setup Jetski Chat",
    "配置 Jetski 聊天"
  ],
  [
    "Sort Conversation",
    "排序对话"
  ],
  [
    "Terminal Commands",
    "终端命令"
  ],
  [
    "Add Custom Model",
    "添加自定义模型"
  ],
  [
    "Auth and Billing",
    "账号与账单"
  ],
  [
    "Background Tasks",
    "后台任务"
  ],
  [
    "Best of N Models",
    "Best of N 模型"
  ],
  [
    "Browser CDP Port",
    "浏览器 CDP 端口"
  ],
  [
    "Cancel All Tasks",
    "取消全部任务"
  ],
  [
    "Create a Project",
    "创建项目"
  ],
  [
    "Enable Demo Mode",
    "启用演示模式"
  ],
  [
    "Enable Telemetry",
    "启用遥测"
  ],
  [
    "File Permissions",
    "文件权限"
  ],
  [
    "General Feedback",
    "一般反馈"
  ],
  [
    "Keep In Menu Bar",
    "保留在菜单栏"
  ],
  [
    "Marketing Emails",
    "营销邮件"
  ],
  [
    "New Conversation",
    "新建对话"
  ],
  [
    "No conversations",
    "暂无对话"
  ],
  [
    "Open Preferences",
    "打开偏好设置"
  ],
  [
    "Pin Conversation",
    "固定对话"
  ],
  [
    "Project Detected",
    "检测到项目"
  ],
  [
    "Project Settings",
    "项目设置"
  ],
  [
    "Provide Feedback",
    "提供反馈"
  ],
  [
    "Send Immediately",
    "立即发送"
  ],
  [
    "Terms of Service",
    "服务条款"
  ],
  [
    "1 agent running",
    "1 个智能体正在运行"
  ],
  [
    "Actual behavior",
    "实际行为"
  ],
  [
    "Actuation Rules",
    "操作规则"
  ],
  [
    "Background Task",
    "后台任务"
  ],
  [
    "Code with Agent",
    "与智能体协作编码"
  ],
  [
    "Command Palette",
    "命令面板"
  ],
  [
    "Copy debug info",
    "复制调试信息"
  ],
  [
    "Display Options",
    "显示选项"
  ],
  [
    "Editor Settings",
    "编辑器设置"
  ],
  [
    "Feature Request",
    "功能请求"
  ],
  [
    "Five Hour Limit",
    "5 小时限额"
  ],
  [
    "For help, visit",
    "如需帮助，请访问"
  ],
  [
    "global settings",
    "全局设置"
  ],
  [
    "Import success:",
    "导入成功："
  ],
  [
    "Layout Controls",
    "布局控制"
  ],
  [
    "Message history",
    "消息历史"
  ],
  [
    "Missing Folders",
    "缺失文件夹"
  ],
  [
    "Open MCP Config",
    "打开 MCP 配置"
  ],
  [
    "Package Outline",
    "包大纲"
  ],
  [
    "Project Folders",
    "项目文件夹"
  ],
  [
    "Project General",
    "项目常规"
  ],
  [
    "Queued Messages",
    "排队消息"
  ],
  [
    "Scheduled Tasks",
    "定时任务"
  ],
  [
    "Search files...",
    "搜索文件..."
  ],
  [
    "Search tasks...",
    "搜索任务..."
  ],
  [
    "Security Preset",
    "安全预设"
  ],
  [
    "Toggle Terminal",
    "切换终端"
  ],
  [
    "Agent Behavior",
    "智能体行为"
  ],
  [
    "Agent response",
    "智能体回复"
  ],
  [
    "Always Proceed",
    "始终继续"
  ],
  [
    "Auto Execution",
    "自动执行"
  ],
  [
    "Copy File Name",
    "复制文件名"
  ],
  [
    "Copy File Path",
    "复制文件路径"
  ],
  [
    "Create Project",
    "创建项目"
  ],
  [
    "Customizations",
    "自定义扩展"
  ],
  [
    "Delete Project",
    "删除项目"
  ],
  [
    "Go to Projects",
    "前往项目"
  ],
  [
    "Import failed:",
    "导入失败："
  ],
  [
    "Inline Actions",
    "内联操作"
  ],
  [
    "Mark As Unread",
    "标记为未读"
  ],
  [
    "Missing Folder",
    "缺失文件夹"
  ],
  [
    "Models & Usage",
    "模型与用量"
  ],
  [
    "No MCP Servers",
    "没有 MCP 服务器"
  ],
  [
    "Not in Project",
    "未在项目中"
  ],
  [
    "Open window...",
    "打开窗口..."
  ],
  [
    "Open Workspace",
    "打开工作区"
  ],
  [
    "Opened browser",
    "已打开浏览器"
  ],
  [
    "Proceeded with",
    "已执行"
  ],
  [
    "Project picker",
    "项目选择器"
  ],
  [
    "Remote Control",
    "远程控制"
  ],
  [
    "Request Review",
    "请求审核"
  ],
  [
    "Require Review",
    "需要审核"
  ],
  [
    "Review Changes",
    "审核更改"
  ],
  [
    "Select Project",
    "选择项目"
  ],
  [
    "Toggle Sidebar",
    "切换侧边栏"
  ],
  [
    "Typeahead menu",
    "自动补全菜单"
  ],
  [
    "View Changelog",
    "查看更新日志"
  ],
  [
    "Agent Decides",
    "由智能体决定"
  ],
  [
    "Allow options",
    "允许选项"
  ],
  [
    "Chat Settings",
    "聊天设置"
  ],
  [
    "CitC Settings",
    "CitC 设置"
  ],
  [
    "Conversations",
    "对话"
  ],
  [
    "Default Light",
    "默认浅色"
  ],
  [
    "Feedback Type",
    "反馈类型"
  ],
  [
    "Gemini Models",
    "Gemini 模型"
  ],
  [
    "Good response",
    "好评"
  ],
  [
    "Inherits from",
    "继承自"
  ],
  [
    "Message input",
    "消息输入框"
  ],
  [
    "Model Credits",
    "模型积分"
  ],
  [
    "New Workspace",
    "新建工作区"
  ],
  [
    "Next Pane Tab",
    "下一个面板标签页"
  ],
  [
    "Notifications",
    "通知"
  ],
  [
    "Open in Cider",
    "在 Cider 中打开"
  ],
  [
    "Open Settings",
    "打开设置"
  ],
  [
    "Prevent Sleep",
    "防止睡眠"
  ],
  [
    "Project Agent",
    "项目智能体"
  ],
  [
    "Reload Window",
    "重新加载窗口"
  ],
  [
    "Review Policy",
    "审核策略"
  ],
  [
    "Send Feedback",
    "发送反馈"
  ],
  [
    "Tab to Import",
    "按下 Tab 导入"
  ],
  [
    "Toggle Editor",
    "切换编辑器"
  ],
  [
    "Always Allow",
    "始终允许"
  ],
  [
    "App Settings",
    "应用设置"
  ],
  [
    "Bad response",
    "差评"
  ],
  [
    "Browser Task",
    "浏览器任务"
  ],
  [
    "Close Folder",
    "关闭文件夹"
  ],
  [
    "Confirm Quit",
    "确认退出"
  ],
  [
    "Conversation",
    "对话"
  ],
  [
    "Copy Command",
    "复制命令"
  ],
  [
    "Copy Content",
    "复制内容"
  ],
  [
    "Default Dark",
    "默认深色"
  ],
  [
    "Disable Task",
    "禁用任务"
  ],
  [
    "Execute URLs",
    "执行 URL"
  ],
  [
    "Find in Pane",
    "在面板中查找"
  ],
  [
    "Full machine",
    "整机访问"
  ],
  [
    "Last Updated",
    "最近更新"
  ],
  [
    "Mark As Read",
    "标记为已读"
  ],
  [
    "More actions",
    "更多操作"
  ],
  [
    "New Worktree",
    "新建工作树"
  ],
  [
    "Record Audio",
    "录制音频"
  ],
  [
    "Restart Task",
    "重启任务"
  ],
  [
    "Select Model",
    "选择模型"
  ],
  [
    "Send message",
    "发送消息"
  ],
  [
    "Toggle Agent",
    "切换智能体"
  ],
  [
    "User message",
    "用户消息"
  ],
  [
    "Weekly Limit",
    "周额度"
  ],
  [
    "Add context",
    "添加上下文"
  ],
  [
    "Application",
    "应用"
  ],
  [
    "Cancel Task",
    "取消任务"
  ],
  [
    "Copy prompt",
    "复制提示词"
  ],
  [
    "Delete Task",
    "删除任务"
  ],
  [
    "Description",
    "描述"
  ],
  [
    "Enable Task",
    "启用任务"
  ],
  [
    "File Access",
    "文件访问"
  ],
  [
    "File Writes",
    "文件写入"
  ],
  [
    "Focus Input",
    "聚焦输入框"
  ],
  [
    "Full access",
    "完全访问"
  ],
  [
    "Get Started",
    "开始使用"
  ],
  [
    "Jetski Chat",
    "Jetski 聊天"
  ],
  [
    "Last Prompt",
    "上次提示词"
  ],
  [
    "Light Theme",
    "浅色主题"
  ],
  [
    "Marketplace",
    "插件市场"
  ],
  [
    "Model Quota",
    "模型额度"
  ],
  [
    "New Project",
    "新建项目"
  ],
  [
    "No Subtitle",
    "无副标题"
  ],
  [
    "Open Folder",
    "打开文件夹"
  ],
  [
    "or join the",
    "或加入"
  ],
  [
    "Permissions",
    "权限"
  ],
  [
    "Quick Start",
    "快速开始"
  ],
  [
    "Recommended",
    "推荐"
  ],
  [
    "Suggestions",
    "建议"
  ],
  [
    "Tab to Jump",
    "按下 Tab 跳转"
  ],
  [
    "Token Usage",
    "Token 使用量"
  ],
  [
    "Write Files",
    "写入文件"
  ],
  [
    "Add Folder",
    "添加文件夹"
  ],
  [
    "Allow Once",
    "允许一次"
  ],
  [
    "Always Ask",
    "始终询问"
  ],
  [
    "Appearance",
    "外观"
  ],
  [
    "Automation",
    "自动化"
  ],
  [
    "Avatar URL",
    "头像 URL"
  ],
  [
    "Background",
    "背景色"
  ],
  [
    "Bug Report",
    "问题报告"
  ],
  [
    "chat space",
    "聊天群组"
  ],
  [
    "Dark Theme",
    "深色主题"
  ],
  [
    "Date Added",
    "添加日期"
  ],
  [
    "Deprecated",
    "已弃用"
  ],
  [
    "Edit Model",
    "编辑模型"
  ],
  [
    "File Reads",
    "文件读取"
  ],
  [
    "Foreground",
    "前景色"
  ],
  [
    "Go Forward",
    "前进"
  ],
  [
    "Learn more",
    "了解更多"
  ],
  [
    "Navigation",
    "导航"
  ],
  [
    "No Project",
    "无项目"
  ],
  [
    "Quick Open",
    "快速打开"
  ],
  [
    "Read Files",
    "读取文件"
  ],
  [
    "Reset Zoom",
    "重置缩放"
  ],
  [
    "Tab Import",
    "按下 Tab 导入"
  ],
  [
    "Turbo mode",
    "极速模式"
  ],
  [
    "View Debug",
    "查看调试信息"
  ],
  [
    "Working...",
    "正在工作..."
  ],
  [
    "Workspaces",
    "工作区"
  ],
  [
    "Your Plan:",
    "你的套餐："
  ],
  [
    "Actuation",
    "操作"
  ],
  [
    "Add Model",
    "添加模型"
  ],
  [
    "Automatic",
    "自动"
  ],
  [
    "Copy Path",
    "复制路径"
  ],
  [
    "Customize",
    "自定义"
  ],
  [
    "Developer",
    "开发者"
  ],
  [
    "Execution",
    "执行"
  ],
  [
    "Knowledge",
    "知识库"
  ],
  [
    "Launchpad",
    "启动台"
  ],
  [
    "MCP Tools",
    "MCP 工具"
  ],
  [
    "Read URLs",
    "读取 URL"
  ],
  [
    "regrouped",
    "重新分组"
  ],
  [
    "Remaining",
    "剩余"
  ],
  [
    "Sandboxed",
    "沙盒化"
  ],
  [
    "Searching",
    "正在搜索"
  ],
  [
    "Selection",
    "选择"
  ],
  [
    "Shortcuts",
    "快捷键"
  ],
  [
    "Subtitles",
    "副标题"
  ],
  [
    "Tab Speed",
    "Tab 补全速度"
  ],
  [
    "Workspace",
    "工作区"
  ],
  [
    "[MODIFY]",
    "[修改]"
  ],
  [
    "Advanced",
    "高级"
  ],
  [
    "Archived",
    "已归档"
  ],
  [
    "Bot Name",
    "机器人名称"
  ],
  [
    "Disabled",
    "已禁用"
  ],
  [
    "Download",
    "下载"
  ],
  [
    "Explored",
    "已探索"
  ],
  [
    "Feedback",
    "反馈"
  ],
  [
    "Group By",
    "分组方式"
  ],
  [
    "Maximize",
    "最大化"
  ],
  [
    "Mentions",
    "提及"
  ],
  [
    "Minimize",
    "最小化"
  ],
  [
    "Open App",
    "打开应用"
  ],
  [
    "Open URL",
    "打开 URL"
  ],
  [
    "Planning",
    "规划"
  ],
  [
    "Projects",
    "项目管理"
  ],
  [
    "Searched",
    "已搜索"
  ],
  [
    "Searches",
    "搜索次数"
  ],
  [
    "See less",
    "收起"
  ],
  [
    "Settings",
    "软件设置"
  ],
  [
    "Show all",
    "显示全部"
  ],
  [
    "Sign Out",
    "退出登录"
  ],
  [
    "Terminal",
    "终端"
  ],
  [
    "Worktree",
    "工作树"
  ],
  [
    "Zoom Out",
    "缩小"
  ],
  [
    "Account",
    "账户"
  ],
  [
    "Actions",
    "操作"
  ],
  [
    "Add MCP",
    "添加 MCP"
  ],
  [
    "Browser",
    "浏览器"
  ],
  [
    "Context",
    "上下文"
  ],
  [
    "Default",
    "默认"
  ],
  [
    "Deleted",
    "已删除"
  ],
  [
    "Dismiss",
    "忽略"
  ],
  [
    "Enabled",
    "已启用"
  ],
  [
    "folders",
    "文件夹"
  ],
  [
    "General",
    "常规"
  ],
  [
    "Go Back",
    "后退"
  ],
  [
    "Go Live",
    "实时预览 (Go Live)"
  ],
  [
    "History",
    "历史"
  ],
  [
    "Plugin:",
    "插件："
  ],
  [
    "Plugins",
    "插件"
  ],
  [
    "Proceed",
    "继续"
  ],
  [
    "Profile",
    "配置文件"
  ],
  [
    "Project",
    "项目"
  ],
  [
    "Refresh",
    "刷新"
  ],
  [
    "Release",
    "松开"
  ],
  [
    "Science",
    "科学"
  ],
  [
    "Sidebar",
    "侧边栏"
  ],
  [
    "Upgrade",
    "升级"
  ],
  [
    "Working",
    "正在工作"
  ],
  [
    "Zoom In",
    "放大"
  ],
  [
    "Accent",
    "强调色"
  ],
  [
    "Cancel",
    "取消"
  ],
  [
    "Custom",
    "自定义"
  ],
  [
    "Delete",
    "删除"
  ],
  [
    "Edited",
    "已编辑"
  ],
  [
    "Editor",
    "编辑器"
  ],
  [
    "Export",
    "导出"
  ],
  [
    "Filter",
    "筛选"
  ],
  [
    "folder",
    "文件夹"
  ],
  [
    "Global",
    "全局"
  ],
  [
    "Inline",
    "内联"
  ],
  [
    "Log in",
    "登录"
  ],
  [
    "Medium",
    "中"
  ],
  [
    "Models",
    "模型"
  ],
  [
    "Narrow",
    "窄"
  ],
  [
    "Picker",
    "选择器"
  ],
  [
    "Pinned",
    "已固定"
  ],
  [
    "Preset",
    "预设"
  ],
  [
    "Recent",
    "最近使用"
  ],
  [
    "Rename",
    "重命名"
  ],
  [
    "Review",
    "审核"
  ],
  [
    "Search",
    "搜索"
  ],
  [
    "Skills",
    "技能"
  ],
  [
    "Snooze",
    "稍后提醒"
  ],
  [
    "Status",
    "状态"
  ],
  [
    "Strict",
    "严格"
  ],
  [
    "Submit",
    "提交"
  ],
  [
    "System",
    "跟随系统"
  ],
  [
    "Value:",
    "当前值："
  ],
  [
    "Window",
    "窗口"
  ],
  [
    "After",
    "分组后"
  ],
  [
    "Close",
    "关闭"
  ],
  [
    "Email",
    "邮箱"
  ],
  [
    "files",
    "文件"
  ],
  [
    "Light",
    "浅色"
  ],
  [
    "Local",
    "本地"
  ],
  [
    "Media",
    "媒体"
  ],
  [
    "Model",
    "模型"
  ],
  [
    "Queue",
    "排队"
  ],
  [
    "Quote",
    "引用"
  ],
  [
    "Rules",
    "规则"
  ],
  [
    "Setup",
    "配置"
  ],
  [
    "Theme",
    "主题"
  ],
  [
    "Usage",
    "用量"
  ],
  [
    "Copy",
    "复制"
  ],
  [
    "Dark",
    "深色"
  ],
  [
    "Edit",
    "编辑"
  ],
  [
    "Fast",
    "快"
  ],
  [
    "file",
    "文件"
  ],
  [
    "Help",
    "帮助"
  ],
  [
    "High",
    "高"
  ],
  [
    "Hold",
    "按住"
  ],
  [
    "Labs",
    "实验室"
  ],
  [
    "None",
    "无"
  ],
  [
    "Open",
    "打开"
  ],
  [
    "Plan",
    "套餐计划"
  ],
  [
    "Quit",
    "退出"
  ],
  [
    "Read",
    "读取"
  ],
  [
    "Skip",
    "跳过"
  ],
  [
    "Slow",
    "慢"
  ],
  [
    "View",
    "视图"
  ],
  [
    "Wide",
    "宽"
  ],
  [
    "Add",
    "添加"
  ],
  [
    "App",
    "应用"
  ],
  [
    "Low",
    "低"
  ],
  [
    "Now",
    "当前"
  ],
  [
    "Off",
    "关闭"
  ],
  [
    "Ran",
    "已运行"
  ],
  [
    "Run",
    "运行"
  ],
  [
    "Use",
    "使用"
  ],
  [
    "Go",
    "转到"
  ],
  [
    "On",
    "开启"
  ],
  [
    "Skills & Customizations",
    "技能与自定义扩展"
  ],
  [
    "Subagents",
    "子智能体"
  ],
  [
    "Artifacts",
    "方案产物"
  ],
  [
    "Files Changed",
    "修改文件"
  ],
  [
    "Terminals",
    "终端控制台"
  ],
  [
    "Implementation Plan",
    "方案实施规划书"
  ],
  [
    "Walkthrough",
    "任务交付复盘"
  ],
  [
    "always-proceed",
    "始终自动执行"
  ],
  [
    "request-review",
    "执行前请求确认"
  ],
  [
    "proceed-in-sandbox",
    "在沙箱中执行"
  ],
  [
    "Planning Mode",
    "规划模式"
  ],
  [
    "Waiting for user input",
    "等待用户输入"
  ],
  [
    "Privacy",
    "隐私"
  ],
  [
    "About",
    "关于"
  ],
  [
    "Language",
    "语言"
  ],
  [
    "Approval Policy",
    "审批策略"
  ],
  [
    "Sandbox",
    "沙箱"
  ],
  [
    "Network Access",
    "网络访问"
  ],
  [
    "Save",
    "保存"
  ],
  [
    "Apply",
    "应用"
  ],
  [
    "Back",
    "返回"
  ],
  [
    "Next",
    "下一步"
  ],
  [
    "Retry",
    "重试"
  ],
  [
    "Loading",
    "加载中"
  ],
  [
    "Stop",
    "停止"
  ],
  [
    "Pause",
    "暂停"
  ],
  [
    "Resume",
    "继续"
  ],
  [
    "Create",
    "创建"
  ],
  [
    "Type a message",
    "输入消息"
  ],
  [
    "Start a new conversation",
    "开始新对话"
  ],
  [
    "See all",
    "查看全部"
  ],
  [
    "Install IDE",
    "安装 IDE"
  ],
  [
    "Agent Settings",
    "智能体设置"
  ],
  [
    "Selection Actions",
    "选择操作"
  ],
  [
    "Open Editor Settings",
    "打开编辑器设置"
  ],
  [
    "Tab",
    "Tab"
  ],
  [
    "Browser Settings",
    "浏览器设置"
  ],
  [
    "Open File Search",
    "打开文件搜索"
  ],
  [
    "File Picker",
    "文件选择器"
  ],
  [
    "Select Previous Conversation",
    "选择上一个对话"
  ],
  [
    "Select Next Conversation",
    "选择下一个对话"
  ],
  [
    "AI Credit Overages",
    "AI 积分超额使用"
  ],
  [
    "Path",
    "路径"
  ],
  [
    "Select",
    "选择"
  ],
  [
    "Refresh MCP servers",
    "刷新 MCP 服务器"
  ],
  [
    "New standalone conversation, outside of projects.",
    "新建独立对话，不属于任何项目。"
  ],
  [
    "More options",
    "更多选项"
  ],
  [
    "Project options",
    "项目选项"
  ],
  [
    "More",
    "更多"
  ],
  [
    "Pin",
    "固定"
  ],
  [
    "Unpin",
    "取消固定"
  ],
  [
    "Archive",
    "归档"
  ],
  [
    "Restore",
    "恢复"
  ],
  [
    "Split",
    "分屏"
  ],
  [
    "Split Right",
    "向右分屏"
  ],
  [
    "Split Down",
    "向下分屏"
  ],
  [
    "Replace With New",
    "替换为新建"
  ],
  [
    "Remove From Split",
    "从分屏中移除"
  ],
  [
    "Conversation Name",
    "对话名称"
  ],
  [
    "Conversation ID",
    "对话 ID"
  ],
  [
    "Workspace Name",
    "工作区名称"
  ],
  [
    "Worktree Name",
    "工作树名称"
  ],
  [
    "Project Name",
    "项目名称"
  ],
  [
    "Fork",
    "派生"
  ],
  [
    "Share",
    "分享"
  ],
  [
    "Share Conversation",
    "分享对话"
  ],
  [
    "Copy Link",
    "复制链接"
  ],
  [
    "Code Search",
    "代码搜索"
  ],
  [
    "Trajectory Debug View",
    "轨迹调试视图"
  ],
  [
    "Command Center",
    "命令中心"
  ],
  [
    "Mark Read",
    "标为已读"
  ],
  [
    "Mark Unread",
    "标为未读"
  ],
  [
    "Move to Group",
    "移动到分组"
  ],
  [
    "New Group",
    "新建分组"
  ],
  [
    "Create Group",
    "创建分组"
  ],
  [
    "Remove from Group",
    "从分组中移除"
  ],
  [
    "No groups yet",
    "暂无分组"
  ],
  [
    "Are you sure you want to delete this conversation? This action cannot be undone.",
    "您确定要删除此对话吗？此操作无法撤销。"
  ],
  [
    "Collapse queued messages",
    "折叠排队消息"
  ],
  [
    "Expand queued messages",
    "展开排队消息"
  ],
  [
    "Cancel (Ctrl+D)",
    "取消 (Ctrl+D)"
  ],
  [
    "Maximize Pane",
    "最大化面板"
  ],
  [
    "Restore Pane",
    "还原面板"
  ],
  [
    "Overview",
    "概览"
  ],
  [
    "Overview tab",
    "概览标签页"
  ],
  [
    "Review tab",
    "审查标签页"
  ],
  [
    "Terminal tab",
    "终端标签页"
  ],
  [
    "Scroll to Bottom",
    "滚动到底部"
  ],
  [
    "Stop execution",
    "停止执行"
  ],
  [
    "View Usage",
    "查看用量明细"
  ],
  [
    "Skills Used",
    "已使用的技能"
  ],
  [
    "Uncommitted",
    "未提交"
  ],
  [
    "Auxiliary Pane",
    "辅助面板"
  ],
  [
    "Custom tool call output is missing",
    "自定义工具调用输出缺失"
  ],
  [
    "Drag to select a region to comment",
    "拖拽框选区域以添加批注"
  ],
  [
    "Untitled Conversation",
    "未命名对话"
  ],
  [
    "CLI Project",
    "命令行项目"
  ],
  [
    "Sends after agent finishes working",
    "智能体结束工作后发送"
  ],
  [
    "Error Verification Required",
    "错误：需要完成验证"
  ],
  [
    "Verification Required",
    "需要完成验证"
  ],
  [
    "Working",
    "工作中"
  ],
  [
    "Exploring",
    "探索中"
  ],
  [
    "Analyzed",
    "已分析"
  ],
  [
    "Preview",
    "预览"
  ],
  [
    "Raw",
    "源码"
  ],
  [
    "Uploads",
    "上传文件"
  ]
,
    ['Terms of Service & Data Use', '服务条款与数据使用'],
    ['Security Notice & Data Use', '安全须知与数据使用'],
    ['Terms and Privacy:', '条款与隐私：'],
    ['Terms and Privacy', '条款与隐私'],
    ['Privacy Notice', '隐私权声明'],
    ['Google Privacy Policy', 'Google 隐私权政策'],
    ['Accept and continue', '接受并继续'],
    ['Get started', '开始使用'],
    ['Getting started with Google Antigravity', '开始使用 Google Antigravity'],
    ["Here's how you and your agents work together", '了解您与智能体如何协同工作'],
    ['Build with one agent or a team', '与单个智能体或团队共同构建'],
    ['Review plans and walkthroughs', '审核计划与演练指南'],
    ['Set the rules, define the boundaries.', '设定规则，明确边界。'],
    ['(excluding product analytics data)', '（不包括产品分析数据）'],
    ['via email.', '（通过电子邮件）。'],
    ['via email', '通过电子邮件'],
    ['your plan', '您的方案'],
    ['accounts', '个账号'],
    ['Yes, I agree to help improve', '是的，我同意帮助改进'],
    ['by allowing Google to collect and use my Interactions data, subject to the', '允许 Google 收集并使用我的互动数据，并遵守'],
    ['I understand I can choose to opt out later whenever I want via my settings.', '我了解我随时可以在设置中选择退出。'],
    ['. I understand I can choose to opt out later whenever I want via my settings.', '；我了解我随时可以在设置中选择退出。'],
    ["Yes, I'd like to receive product updates, tips, and promotions from Google", '是的，我希望接收来自 Google 的产品更新、提示和优惠信息'],
    ['Built-in Browser', '内置浏览器'],
    ['External Browser', '外部浏览器'],
    ['Open Links In', '打开链接方式'],
    ['Download Location', '下载文件保存位置'],
    ['Browsing History', '浏览历史记录'],
    ['Browser Subagent', '浏览器子智能体'],
    ['Change…', '更改…'],
    ['Voice mode', '语音模式'],
    ['Voice Mode', '语音模式'],
    ['Voice engine', '语音引擎'],
    ['Default (Mendel)', '默认 (Mendel)'],
    ['System default', '系统默认'],
    ['Mute Voice Mic', '静音麦克风'],
    ['Mute Voice Speaker', '静音扬声器'],
    ['Conversation Steps', '对话步骤详情'],
    ['Verbose', '详细 (Verbose)'],
    ['Contrast', '对比度'],
    ['Strong', '高对比 (Strong)'],
    ['Project 4K', 'Project 4K 沉浸模式'],
    ['Modified in', '修改于'],
    ['Sound', '提示音'],
    ['Volume', '音量'],
    ['Windows Subsystem for Linux', 'Windows Subsystem for Linux (WSL)'],
    ['Connect', '连接'],
    ['App version', '应用版本'],
    ['New Tab', '新建标签页'],
    ['Reopen Closed Tab', '重新打开关闭的标签页'],
    ['Move Conversation Up', '上移对话'],
    ['Move Conversation Down', '下移对话'],
    ['Previous Side Panel Tab', '上一个侧边面板标签页'],
    ['Next Side Panel Tab', '下一个侧边面板标签页'],
    ['Toggle Side Panel', '切换侧边面板'],
    ['Toggle Maximize Side Panel', '最大化/还原侧边面板'],
    ['Toggle Overview Panel', '切换概览面板'],
    ['Remote Control Issue', '远程控制相关问题'],
    ['Legal Help', '法律援助'],
    ['Visit', '访问'],
    ['Your plan:', '您的方案：'],
    ['Your Plan:', '您的方案：'],
    ['Your Plan', '您的方案'],
    ['Your plan', '您的方案'],
    ['Marketplace', '市场'],
    ['Installed', '已安装'],
    ['Skills & Rules', '技能与规则'],
    ['Custom Agents', '自定义智能体'],
    ['Built In', '内置'],
    ['Built-in', '内置'],
    ['Built-in Skills', '内置技能'],
    ['Custom Skills', '自定义技能'],
    ['No custom agents yet.', '暂无自定义智能体。'],
    ['No custom agents yet', '暂无自定义智能体'],
    ['No description available.', '暂无可用说明。'],
    ['No description available', '暂无可用说明'],
    ['Featured', '精选推荐'],
    ['All', '全部'],
    ['Loading available plugins...', '正在加载可用插件...'],
    ['Loading available plugins', '正在加载可用插件'],
    ['Installed Plugins', '已安装插件'],
    ['Installed Skills', '已安装技能'],
    ['Discover Skills', '发现技能'],
    ['Discover helpful skills & plugins', '发现实用的技能与插件'],
    ['Delete Skill', '删除技能'],
    ['Disable Plugin', '禁用插件'],
    ['Enable Plugin', '启用插件'],
    ['Delete plugin', '删除插件'],
    ['Close skills panel', '关闭技能面板'],
    ['Core tools and knowledge required to develop for Android.', '开发 Android 所需的核心工具与知识。'],
    ['Using the Google Antigravity Python SDK to build AI agents', '使用 Google Antigravity Python SDK 构建 AI 智能体'],
    ['Curated collection of agent skills for modern web development.', '精选用于现代 Web 开发的智能体技能集合。'],
    ['Curated collection of agent skills for science tasks.', '精选用于科学任务的智能体技能集合。'],
    ['Fix with Agent', '使用智能体修复'],
    ['Authenticate', '去认证'],
    ['5 tools enabled', '已启用 5 个工具'],
    ['92 tools enabled', '已启用 92 个工具'],
    ['tools enabled', '个工具已启用'],
    ['Active Skills', '已启用技能'],
    ['Customize Global Skills', '自定义全局技能'],
    ['agy-customizations', 'agy-customizations（反重力系统自定义扩展）'],
    ['/agy-customizations', '/agy-customizations（反重力系统自定义扩展）'],
    ['antigravity-guide', 'antigravity-guide（官方开发指南与全景索引）'],
    ['/antigravity-guide', '/antigravity-guide（官方开发指南与全景索引）'],
    ['antigravity_guide', 'antigravity_guide（官方开发指南与全景索引）'],
    ['/antigravity_guide', '/antigravity_guide（官方开发指南与全景索引）'],
    ['automation', 'automation（自动化定时任务创建向导）'],
    ['/automation', '/automation（自动化定时任务创建向导）'],
    ['generative_ui', 'generative_ui（生成式交互 UI 组件）'],
    ['/generative_ui', '/generative_ui（生成式交互 UI 组件）'],
    ['migrate-workflows', 'migrate-workflows（工作流旧版规范平滑迁移）'],
    ['/migrate-workflows', '/migrate-workflows（工作流旧版规范平滑迁移）'],
    ['permissioned-github', 'permissioned-github（GitHub 安全受限操作指南）'],
    ['/permissioned-github', '/permissioned-github（GitHub 安全受限操作指南）'],
    ['plugin', 'plugin（插件管理与打包规范）'],
    ['/plugin', '/plugin（插件管理与打包规范）'],
    ['run-workflow', 'run-workflow（动态多 Agent 工作流运行器）'],
    ['/run-workflow', '/run-workflow（动态多 Agent 工作流运行器）'],
    ['ui-plugin-navigation', 'ui-plugin-navigation（UI 插件侧边面板导航）'],
    ['/ui-plugin-navigation', '/ui-plugin-navigation（UI 插件侧边面板导航）'],
    ['android-cli', 'android-cli（Android 命令行开发工具）'],
    ['/android-cli', '/android-cli（Android 命令行开发工具）'],
    ['android-device-hub', 'android-device-hub（Android 设备中心真机/模拟器控制）'],
    ['/android-device-hub', '/android-device-hub（Android 设备中心真机/模拟器控制）'],
    ['compose-preview', 'compose-preview（Android Jetpack Compose 实时 UI 预览）'],
    ['/compose-preview', '/compose-preview（Android Jetpack Compose 实时 UI 预览）'],
    ['alphafold-database-fetch-and-analyze', 'alphafold-database-fetch-and-analyze（AlphaFold 蛋白质结构检索与分析）'],
    ['/alphafold-database-fetch-and-analyze', '/alphafold-database-fetch-and-analyze（AlphaFold 蛋白质结构检索与分析）'],
    ['alphagenome-atlas-website-links', 'alphagenome-atlas-website-links（AlphaGenome 基因组图谱链接构建）'],
    ['/alphagenome-atlas-website-links', '/alphagenome-atlas-website-links（AlphaGenome 基因组图谱链接构建）'],
    ['alphagenome-single-variant-analysis', 'alphagenome-single-variant-analysis（AlphaGenome 单变异位点效应分析）'],
    ['/alphagenome-single-variant-analysis', '/alphagenome-single-variant-analysis（AlphaGenome 单变异位点效应分析）'],
    ['alphagenome-variant-impact-score', 'alphagenome-variant-impact-score（AlphaGenome 变异功能影响评分 AVI）'],
    ['/alphagenome-variant-impact-score', '/alphagenome-variant-impact-score（AlphaGenome 变异功能影响评分 AVI）'],
    ['biomolecular-structure-viewer', 'biomolecular-structure-viewer（3D 生物分子结构交互查看器 Mol*）'],
    ['/biomolecular-structure-viewer', '/biomolecular-structure-viewer（3D 生物分子结构交互查看器 Mol*）'],
    ['chembl-database', 'chembl-database（ChEMBL 生物活性小分子与靶点数据库）'],
    ['/chembl-database', '/chembl-database（ChEMBL 生物活性小分子与靶点数据库）'],
    ['cheminformatics-cofolding', 'cheminformatics-cofolding（计算化学：蛋白质配体共折叠模拟）'],
    ['/cheminformatics-cofolding', '/cheminformatics-cofolding（计算化学：蛋白质配体共折叠模拟）'],
    ['cheminformatics-core', 'cheminformatics-core（计算化学：RDKit 物理化学分子描述符）'],
    ['/cheminformatics-core', '/cheminformatics-core（计算化学：RDKit 物理化学分子描述符）'],
    ['cheminformatics-doc2mol', 'cheminformatics-doc2mol（计算化学：文献与专利分子提取 Doc2Mol）'],
    ['/cheminformatics-doc2mol', '/cheminformatics-doc2mol（计算化学：文献与专利分子提取 Doc2Mol）'],
    ['cheminformatics-ml', 'cheminformatics-ml（计算化学：小分子 QSAR 机器学习模型）'],
    ['/cheminformatics-ml', '/cheminformatics-ml（计算化学：小分子 QSAR 机器学习模型）'],
    ['cheminformatics-physics', 'cheminformatics-physics（计算化学：3D 分子动力学与对接模拟）'],
    ['/cheminformatics-physics', '/cheminformatics-physics（计算化学：3D 分子动力学与对接模拟）'],
    ['cheminformatics-reactions', 'cheminformatics-reactions（计算化学：有机反应与逆合成路线）'],
    ['/cheminformatics-reactions', '/cheminformatics-reactions（计算化学：有机反应与逆合成路线）'],
    ['clinical-trials-database', 'clinical-trials-database（ClinicalTrials 全球临床试验数据库）'],
    ['/clinical-trials-database', '/clinical-trials-database（ClinicalTrials 全球临床试验数据库）'],
    ['clinvar-database', 'clinvar-database（ClinVar 人类基因组致病性变异数据库）'],
    ['/clinvar-database', '/clinvar-database（ClinVar 人类基因组致病性变异数据库）'],
    ['credentials', 'credentials（API 凭据与密钥安全验证管理）'],
    ['/credentials', '/credentials（API 凭据与密钥安全验证管理）'],
    ['dbsnp-database', 'dbsnp-database（NCBI dbSNP 短变异位点数据库检索）'],
    ['/dbsnp-database', '/dbsnp-database（NCBI dbSNP 短变异位点数据库检索）'],
    ['embl-ebi-ols', 'embl-ebi-ols（EMBL-EBI 生物医学本体术语词汇库 OLS）'],
    ['/embl-ebi-ols', '/embl-ebi-ols（EMBL-EBI 生物医学本体术语词汇库 OLS）'],
    ['encode-ccres-database', 'encode-ccres-database（ENCODE 顺式调控元件数据库 cCREs）'],
    ['/encode-ccres-database', '/encode-ccres-database（ENCODE 顺式调控元件数据库 cCREs）'],
    ['ensembl-database', 'ensembl-database（Ensembl 基因组注释与变异效应预测数据库）'],
    ['/ensembl-database', '/ensembl-database（Ensembl 基因组注释与变异效应预测数据库）'],
    ['foldseek-structural-search', 'foldseek-structural-search（Foldseek 蛋白质 3D 结构相似性搜索）'],
    ['/foldseek-structural-search', '/foldseek-structural-search（Foldseek 蛋白质 3D 结构相似性搜索）'],
    ['gnomad-database', 'gnomad-database（gnomAD 人群基因组变异等位基因频率库）'],
    ['/gnomad-database', '/gnomad-database（gnomAD 人群基因组变异等位基因频率库）'],
    ['gtex-database', 'gtex-database（GTEx 人体组织基因表达量与 eQTL 数据库）'],
    ['/gtex-database', '/gtex-database（GTEx 人体组织基因表达量与 eQTL 数据库）'],
    ['human-protein-atlas-database', 'human-protein-atlas-database（人类蛋白质图谱 HPA 组织与亚细胞定位）'],
    ['/human-protein-atlas-database', '/human-protein-atlas-database（人类蛋白质图谱 HPA 组织与亚细胞定位）'],
    ['interpro-database', 'interpro-database（InterPro 蛋白质家族、功能域与活性位点分析）'],
    ['/interpro-database', '/interpro-database（InterPro 蛋白质家族、功能域与活性位点分析）'],
    ['jaspar-database', 'jaspar-database（JASPAR 转录因子结合基序数据库）'],
    ['/jaspar-database', '/jaspar-database（JASPAR 转录因子结合基序数据库）'],
    ['literature-search-arxiv', 'literature-search-arxiv（arXiv 学术论文搜索与全文下载）'],
    ['/literature-search-arxiv', '/literature-search-arxiv（arXiv 学术论文搜索与全文下载）'],
    ['literature-search-biorxiv', 'literature-search-biorxiv（bioRxiv/medRxiv 生物医学预印本文献检索）'],
    ['/literature-search-biorxiv', '/literature-search-biorxiv（bioRxiv/medRxiv 生物医学预印本文献检索）'],
    ['literature-search-europepmc', 'literature-search-europepmc（Europe PMC 欧洲医学文献检索与全文获取）'],
    ['/literature-search-europepmc', '/literature-search-europepmc（Europe PMC 欧洲医学文献检索与全文获取）'],
    ['literature-search-openalex', 'literature-search-openalex（OpenAlex 全球学术论文与文献图谱检索）'],
    ['/literature-search-openalex', '/literature-search-openalex（OpenAlex 全球学术论文与文献图谱检索）'],
    ['ncbi-sequence-fetch', 'ncbi-sequence-fetch（NCBI 蛋白质与核酸生物序列提取）'],
    ['/ncbi-sequence-fetch', '/ncbi-sequence-fetch（NCBI 蛋白质与核酸生物序列提取）'],
    ['openfda-database', 'openfda-database（openFDA 药品与食品安全监管大数据库）'],
    ['/openfda-database', '/openfda-database（openFDA 药品与食品安全监管大数据库）'],
    ['opentargets-database', 'opentargets-database（Open Targets 靶点发现与疾病关联生物数据库）'],
    ['/opentargets-database', '/opentargets-database（Open Targets 靶点发现与疾病关联生物数据库）'],
    ['pdb-database', 'pdb-database（PDB 蛋白质与生物大分子 3D 空间结构数据库）'],
    ['/pdb-database', '/pdb-database（PDB 蛋白质与生物大分子 3D 空间结构数据库）'],
    ['predictingthepast', 'predictingthepast（古文献修复、断代与地理归属推断 Aeneas/Ithaca）'],
    ['/predictingthepast', '/predictingthepast（古文献修复、断代与地理归属推断 Aeneas/Ithaca）'],
    ['protein-sequence-msa', 'protein-sequence-msa（Clustal Omega 蛋白质多序列比对分析 MSA）'],
    ['/protein-sequence-msa', '/protein-sequence-msa（Clustal Omega 蛋白质多序列比对分析 MSA）'],
    ['protein-sequence-similarity-search', 'protein-sequence-similarity-search（蛋白质同源序列相似度搜索 MMseqs2/BLAST）'],
    ['/protein-sequence-similarity-search', '/protein-sequence-similarity-search（蛋白质同源序列相似度搜索 MMseqs2/BLAST）'],
    ['pubchem-database', 'pubchem-database（PubChem 化学物质与化合物数据库）'],
    ['/pubchem-database', '/pubchem-database（PubChem 化学物质与化合物数据库）'],
    ['pubmed-database', 'pubmed-database（PubMed 全球医学与生命科学同行评审文献检索）'],
    ['/pubmed-database', '/pubmed-database（PubMed 全球医学与生命科学同行评审文献检索）'],
    ['pymol', 'pymol（PyMOL 蛋白质与分子三维结构精美渲染）'],
    ['/pymol', '/pymol（PyMOL 蛋白质与分子三维结构精美渲染）'],
    ['quickgo-database', 'quickgo-database（QuickGO 基因本体与生物学途径分析 GO/ECO）'],
    ['/quickgo-database', '/quickgo-database（QuickGO 基因本体与生物学途径分析 GO/ECO）'],
    ['rdkit-general', 'rdkit-general（RDKit 化学结构 2D 绘图与 ACS 规范渲染）'],
    ['/rdkit-general', '/rdkit-general（RDKit 化学结构 2D 绘图与 ACS 规范渲染）'],
    ['reactome-database', 'reactome-database（Reactome 生物学通路富集与信号通路分析）'],
    ['/reactome-database', '/reactome-database（Reactome 生物学通路富集与信号通路分析）'],
    ['string-database', 'string-database（STRING 蛋白质相互作用网络与功能富集分析）'],
    ['/string-database', '/string-database（STRING 蛋白质相互作用网络与功能富集分析）'],
    ['ucsc-conservation-and-tfbs', 'ucsc-conservation-and-tfbs（UCSC 进化保守性得分与结合位点）'],
    ['/ucsc-conservation-and-tfbs', '/ucsc-conservation-and-tfbs（UCSC 进化保守性得分与结合位点）'],
    ['unibind-database', 'unibind-database（UniBind 实验验证转录因子结合位点数据库）'],
    ['/unibind-database', '/unibind-database（UniBind 实验验证转录因子结合位点数据库）'],
    ['uniprot-database', 'uniprot-database（UniProt 蛋白质序列与结构功能权威数据库）'],
    ['/uniprot-database', '/uniprot-database（UniProt 蛋白质序列与结构功能权威数据库）'],
    ['uv', 'uv（uv Python 极速包管理器安装与环境诊断）'],
    ['/uv', '/uv（uv Python 极速包管理器安装与环境诊断）'],
    ['workflow-skill-creator', 'workflow-skill-creator（交互工作流提炼与 Agent 自定义技能构建器）'],
    ['/workflow-skill-creator', '/workflow-skill-creator（交互工作流提炼与 Agent 自定义技能构建器）'],
    ['chatroom-austrian', 'chatroom-austrian（奥派经济学多智能体研讨室）'],
    ['/chatroom-austrian', '/chatroom-austrian（奥派经济学多智能体研讨室）'],
    ['content-production', 'content-production（图文矩阵内容全自动生成与发布管线）'],
    ['/content-production', '/content-production（图文矩阵内容全自动生成与发布管线）'],
    ['dbs', 'dbs（DontBeSilent 商业自媒体技能入口）'],
    ['/dbs', '/dbs（DontBeSilent 商业自媒体技能入口）'],
    ['dbs-action', 'dbs-action（DontBeSilent 商业行动力突破与执行引擎）'],
    ['/dbs-action', '/dbs-action（DontBeSilent 商业行动力突破与执行引擎）'],
    ['dbs-benchmark', 'dbs-benchmark（DontBeSilent 商业对标账号与爆款模型拆解）'],
    ['/dbs-benchmark', '/dbs-benchmark（DontBeSilent 商业对标账号与爆款模型拆解）'],
    ['dbs-content', 'dbs-content（DontBeSilent 商业私域内容生产与转化脚本）'],
    ['/dbs-content', '/dbs-content（DontBeSilent 商业私域内容生产与转化脚本）'],
    ['dbs-deconstruct', 'dbs-deconstruct（DontBeSilent 商业认知与第一性原理深度拆解）'],
    ['/dbs-deconstruct', '/dbs-deconstruct（DontBeSilent 商业认知与第一性原理深度拆解）'],
    ['dbs-diagnosis', 'dbs-diagnosis（DontBeSilent 商业模式全局诊断与业务问诊）'],
    ['/dbs-diagnosis', '/dbs-diagnosis（DontBeSilent 商业模式全局诊断与业务问诊）'],
    ['dbs-hook', 'dbs-hook（DontBeSilent 爆款短视频开头黄金三秒 Hook 优化）'],
    ['/dbs-hook', '/dbs-hook（DontBeSilent 爆款短视频开头黄金三秒 Hook 优化）'],
    ['find-skills', 'find-skills（智能检索与推荐适用技能库）'],
    ['/find-skills', '/find-skills（智能检索与推荐适用技能库）'],
    ['humanizer-zh', 'humanizer-zh（AI 文本深度去味与真人语言风格拟真）'],
    ['/humanizer-zh', '/humanizer-zh（AI 文本深度去味与真人语言风格拟真）'],
    ['instinct-apply', 'instinct-apply（经验本能自动加载与任务预设对齐）'],
    ['/instinct-apply', '/instinct-apply（经验本能自动加载与任务预设对齐）'],
    ['notebooklm', 'notebooklm（Google NotebookLM 全功能 API 与知识库交互）'],
    ['/notebooklm', '/notebooklm（Google NotebookLM 全功能 API 与知识库交互）'],
    ['remind-me', 'remind-me（自然语言定时提醒与 Cron 任务计划）'],
    ['/remind-me', '/remind-me（自然语言定时提醒与 Cron 任务计划）'],
    ['session-memory', 'session-memory（跨端跨会话记忆与长效上下文管理）'],
    ['/session-memory', '/session-memory（跨端跨会话记忆与长效上下文管理）'],
    ['super-save', 'super-save（核心项目资产与工程经验一键归档存储）'],
    ['/super-save', '/super-save（核心项目资产与工程经验一键归档存储）'],
    ['super-search', 'super-search（历史会话与编码记忆智能精准搜索）'],
    ['/super-search', '/super-search（历史会话与编码记忆智能精准搜索）'],
    ['google-antigravity-sdk', 'google-antigravity-sdk（Google Antigravity Python SDK 开发指南）'],
    ['/google-antigravity-sdk', '/google-antigravity-sdk（Google Antigravity Python SDK 开发指南）'],
    ['modern-web-guidance-plugin', 'modern-web-guidance-plugin（现代 Web 前端开发工程实践规范）'],
    ['/modern-web-guidance-plugin', '/modern-web-guidance-plugin（现代 Web 前端开发工程实践规范）'],
    ['chrome-devtools-plugin', 'chrome-devtools-plugin（Chrome 开发者工具自动化调试插件）'],
    ['/chrome-devtools-plugin', '/chrome-devtools-plugin（Chrome 开发者工具自动化调试插件）'],
    ['workbuddy-chat', 'workbuddy-chat（WorkBuddy 跨平台多 Agent 协作工作台）'],
    ['/workbuddy-chat', '/workbuddy-chat（WorkBuddy 跨平台多 Agent 协作工作台）'],
    ['Comprehensive guide and reference for the Antigravity Customization System. Use to explain how customizations work, their loading priority, discovery mechanisms, and to guide the creation of skills, rules, plugins, hooks, and MCP servers.', 'Google Antigravity 自定义系统的全面指南与参考手册。用于了解自定义系统的运作机制、加载优先级、发现规则，并指导技能、规则、插件、钩子及 MCP 服务的创建。'],
    ['Provides a comprehensive guide, quick reference, and sitemap for Google Antigravity (AGY), including the Antigravity CLI (agy), Antigravity 2.0, Antigravity IDE, Python SDK, slash commands, keybindings, and customizations (skills, rules, MCP, sidecars). Activate this skill when the user asks questions about how to use, configure, or customize Antigravity, AGY, the agy CLI, the Antigravity IDE, or Antigravity 2.0.', '提供 Google Antigravity (AGY) 的全景开发指南、速查手册与系统导航，涵盖 CLI、Antigravity 2.0、IDE、Python SDK、快捷指令、键位映射与各项自定义扩展。'],
    ['Interactive guide to design and create a scheduled background automation. Use this skill when the user wants to create an automated or recurring scheduled task (e.g. "summarize my emails every morning", "every Monday send me a to-do list"). Also triggered by the /automation slash command.', '用于设计并创建计划后台自动化的交互向导。当用户希望创建定时自动化任务时激活此技能。'],
    ['How to render rich interactive HTML widgets inline in the chat or as standalone artifacts. Use this skill when you want to show the user diagrams, data visualizations, interactive controls, educational walkthroughs, or any rich visual content beyond plain text and markdown.', '在对话中以富交互 HTML 小组件或独立产物形式呈现图表、数据可视化、交互式控件与教程流程。'],
    ['Automatically migrate legacy workflows to modern skills across global and workspace configurations. Scans for existing workflows, creates target SKILL.md files, and safely archives old workflow files.', '自动将全局和工作区配置中的旧版工作流规范平滑迁移至现代技能体系，创建标准化 SKILL.md 并安全归档旧文件。'],
    ['Guidelines for interacting with GitHub and request permissions from the user when commands fail due to restrictions in the agent environment.', '与 GitHub 交互并处理 Agent 环境受限时向用户申请安全权限的操作指南与准则。'],
    ['How to manage and create plugins — namespaced bundles of skills, agents, rules, MCP servers and hooks that install, enable and disable as a single unit. Use this skill when the user wants to enable, disable, install or uninstall a plugin, when they want to create a new plugin, or when a new customization should be packaged into a plugin rather than left loose. Also triggered by the /plugin slash command. Don\'t use for the underlying customization system itself — discovery roots, loading priority, or authoring a standalone skill, agent, rule, hook or MCP server outside a plugin; see the customizations guide skill for those.', '管理与打包插件（技能、智能体、规则、MCP 服务与钩子的命名空间包）。用于安装、卸载、启用、禁用及发布自定义插件。'],
    ['How to write and run a dynamic workflow script with the `run_workflow` tool: a Python script that orchestrates many agents with `agent`, `parallel`, `pipeline`, and `phase`. Use when a task splits into many independent or staged pieces of agent work (fan out over files, modules, bugs, or review angles, then aggregate), or when the user asks for a workflow. Don\'t use for a single delegated task (use a subagent) or for legacy workflow files (see migrate-workflows).', '使用 run_workflow 工具编写并运行动态多智能体工作流脚本，通过 Python 脚本编排并行、管线与分阶段 Agent 协作。'],
    ['Discover UI plugin panels relevant to the current task and surface a one-click pill in chat to open (toggle) them in the side pane. Use when a running UI plugin\'s panel would help with what the user is doing, or right after the user enables a new UI plugin pane and a shortcut to open it is handy.', '自动发现与当前任务相关的 UI 插件面板，并在聊天中提供一键调起的交互胶囊链接，方便用户在侧边栏直接打开。'],
    ['Provides instructions for installing and using the `android` CLI. The `android` command-line tool is a critical tool for Android development and helps you create new Android projects, run Android apps on devices, manage and interact with Android virtual devices (including screenshots and UI inspection), manage Android SDK components, look up official Android documentation, and discover and install official Android skills.', '提供安装与使用 android CLI 的完整指南。支持创建 Android 工程、连接与管理真机/模拟器、截屏与 UI 探测、管理 Android SDK 以及安装官方 Android 技能。'],
    ['Instructions for working with the Android Device Hub sidecar, which lists, starts, stops, creates and removes Android Virtual Devices (AVDs), lists physical devices connected to adb, and lets the user mirror and control any of them (video, touch, keyboard, mouse wheel) in the Device Hub pane. Also explains how to inspect and interact with the screen the user is mirroring, with `android layout`, `android screen` and `adb`.', 'Android Device Hub 辅助面板操作指南。用于列出、启动、停止、创建与移除 Android 虚拟设备 (AVD)，列出 ADB 连接的物理设备，并实现低延迟画面镜像与键鼠触摸控制。'],
    ['Instructions for the Android Compose Preview sidecar, which renders Jetpack Compose @Preview functions with `android preview render` and shows them in the Android Compose Preview pane. Use it when the user wants to see a Compose preview, or to review the result of UI changes — re-render after changing the code so that the pane shows the result.', 'Android Compose 预览辅助面板操作指南。用于通过 android preview render 实时渲染 Jetpack Compose 的 @Preview 组件并在侧边栏直接交互预览。'],
    ['Retrieve and analyze AlphaFold predicted structures for a protein. Use when the user provides a specific UniProt Accession ID and wants structural confidence metrics (pLDDT), domain boundary analysis, or disorder assessment. Do not use if the user only has a protein name, gene name, or amino acid sequence — ask for a UniProt ID first.', '检索并分析蛋白质的 AlphaFold 预测 3D 结构。根据 UniProt 访问 ID 计算结构置信度度量 (pLDDT)、结构域边界分析及内在无序区评估。'],
    ['Constructs deep-links and URLs for the AlphaGenome Atlas website. Supports generating single-variant exploration links (1-based VCF-style coordinates), genomic locus views (1-based closed chr:start-end), candidate summary tables, and AlphaGenome reference vs. alternate predictions. Use when visualizing, exploring, charting, or linking genetic variants and genomic loci on the AlphaGenome Atlas, or when asked to inspect, view, or link predictions for a genomic variant. Don\'t use for computing raw AlphaGenome variant predictions directly without Atlas URLs (use alphagenome-single-variant-analysis or alphagenome-variant-impact-score).', '构建 AlphaGenome Atlas 网站的深度跳转链接。支持生成单变异位点探索链接、基因组基因座视图、候选变异摘要表及参考/突变预测比对。'],
    ['Analyzes genetic variant effects on gene expression (RNA-seq), chromatin accessibility (DNASE), histone marks (ChIP), and transcription factors using the AlphaGenome API. Use when the user asks about non-coding variant effects, pathogenicity, clinical significance, disease associations, functional effects, gene expression changes, splicing disruption, or regulatory effects in promoters and enhancers. Also use for resolving biological terms to tissue/cell-type ontologies (UBERON/CL) or analyzing variants in chr:pos:ref>alt format.', '利用 AlphaGenome API 分析遗传变异对基因表达 (RNA-seq)、染色质可及性 (DNASE)、组蛋白修饰 (ChIP) 及转录因子的功能影响。'],
    ['Score, annotate, and analyze the functional impact of genetic variants using AlphaGenome Variant Impact (AVI) scores. Query variants in chr:pos:ref>alt format, annotate VCF/tabular callsets, perform saturation mutagenesis window scans (1-based closed chr:start-end), and extract GENCODE v46 GTF gene/exon/junction coordinates all via the AlphaGenome Atlas API.', '使用 AlphaGenome 变异影响评分 (AVI) 评估和注释人类遗传变异的功能影响，支持饱和突变窗口扫描与 GENCODE 基因外显子坐标提取。'],
    ['Interactive 3D biomolecular structure viewer via Mol*. Renders 3D molecular structures from local workspace files (.cif, .mmcif, .pdb) or conversation artifacts, and manages user 3D annotations and highlighted residues. Use when the user asks to visualise a protein or nucleic acid, display a 3D structure, or asks about 3D biomolecular structure annotations and highlighted residues.', '基于 Mol* 的交互式 3D 生物分子结构查看器。渲染本地工作区或对话产物中的蛋白质与核酸分子三维模型，支持高亮残基与 3D 标注。'],
    ['Query the ChEMBL database for bioactive molecules, drug targets, bioactivity data, approved drugs, and chemical structures. Use when the user asks about compounds, targets, IC50/Ki values, drug mechanisms, or structure searches.', '查询 ChEMBL 数据库中的生物活性小分子、药物靶点、IC50/Ki 生物活性数据、获批上市药物及化学结构。'],
    ['Co-folds protein-ligand, protein-DNA/RNA, and covalent inhibitor complexes: prepares AlphaFold 3 JSON, Boltz-2 YAML, and Boltz API (boltz-2.1) inputs, extracts bound ligand poses from mmCIF/PDB, and computes 3D protein-ligand interaction fingerprints (PLIF) and pharmacophore overlaps.', '计算化学：协同折叠蛋白质-配体、蛋白质-DNA/RNA 以及共价抑制剂复合物，准备 AlphaFold 3 JSON 与 Boltz-2 输入并计算 3D 相互作用指纹 (PLIF)。'],
    ['Computes RDKit physicochemical descriptors (MW, cLogP, TPSA, CNS MPO, SA score), PAINS/Brenk structural alerts, pH 7.4 ionization, congeneric series curation, activity cliffs, combinatorial library enumeration, vendor pricing, and organometallic %V_bur sterics.', '计算化学核心：计算 RDKit 理化分子描述符（MW、cLogP、TPSA、CNS MPO、SA 评分）、PAINS/Brenk 结构警示物、pH 7.4 电离状态与组合化学库枚举。'],
    ['Extracts and curates validated chemical structures from patents, literature, synthesis procedures, and Markush core/R-group tables: resolves IUPAC names via OPSIN and PubChem, retrieves Google Patents full text and assay tables, and exports curated SDF/CSV.', '计算化学：从专利、学术文献与合成步骤中提取并验证化学结构，通过 OPSIN/PubChem 解析 IUPAC 命名并导出标准化 SDF/CSV 库。'],
    ['Trains, benchmarks, and evaluates predictive SAR and QSAR/ADMET models for chemical series: small-N regularized regressors, nested cross-validation, Tukey HSD model tiering, scaffold/temporal splitting, matched molecular pairs (MMPA), similarity attribution maps, model persistence, and candidate scoring.', '计算化学机器学习：训练、基准测试与评估针对化学分子序列的预测性 SAR 和 QSAR/ADMET 模型，支持小样本正则化、嵌套交叉验证与骨架分割。'],
    ['Simulates 3D molecular physics, conformer ensembles, and CADD workflows: pH-dependent ligand and receptor protonation, ETKDGv3 3D conformer generation, dihedral/relaxed PES torsion scans, AutoDock Vina/smina docking, conformational ligand strain energy, PROTAC/macrocycle 3D geometry, and OpenMM molecular dynamics.', '计算化学分子物理模拟：pH 依赖性受体/配体质子化、ETKDGv3 3D 构象系综生成、扭转角 PES 扫描、AutoDock Vina/smina 分子对接与 OpenMM 分子动力学模拟。'],
    ['Proposes and models organic reactions, retrosynthesis, multi-step synthesis routes, intramolecular cyclizations, and reaction SMARTS: checks experimental precedents first, validates atom conservation, prochirality (pro-R/pro-S, Re/Si), topicity, 1H/13C NMR equivalence, and stereogenesis, and renders 2D curved-arrow mechanisms.', '计算化学反应与逆合成：模拟有机化学反应、多步合成路线、分子内环化与反应 SMARTS，验证原子守恒与手性立体构型。'],
    ['Query ClinicalTrials.gov via APIv2. Use when you want to search for trials by condition, drug, location, status, or phase; retrieve trial details by NCT ID; check eligibility/inclusion criteria; count trials across conditions or time periods; identify a sponsor\'s trial portfolio; find recruiting trials for patient matching.', '通过 ClinicalTrials.gov API 查询全球临床试验，按病症、药物、地点、试验阶段检索试验详情与患者入组准入标准。'],
    ['Use when needing clinical significance, pathogenicity classifications (e.g., Pathogenic, Benign, VUS), clinical evidence rationales, or finding "hard positive" benchmark controls for human genomic variants.', '查询 NCBI ClinVar 数据库中人类基因组变异的临床意义、致病性分类（致病、良性、意义未明 VUS）与临床证据支持等级。'],
    ['Instructions for handling API keys and credentials safely, verifying their presence, and prompting the user to add them if missing using a safe protocol.', '安全处理 API 密钥与凭据验证，检测关键凭据状态并在缺失时引导用户通过安全协议添加凭证。'],
    ['Use when you want to look up, map, and search for short genetic variants (SNPs, indels) in NCBI\'s dbSNP database. Resolves between rsIDs, genomic coordinates in VCF format, and HGVS strings. For an rsID, returns variant type, gene associations, clinical significance, allele frequencies, and genomic coordinates (GRCh38).', '在 NCBI dbSNP 数据库中检索、映射和查找短遗传变异（SNP、插入缺失），在 rsID、GRCh38 染色体坐标与 HGVS 格式间互相转换。'],
    ['Query and search the EMBL-EBI Ontology Lookup Service (OLS) for biomedical ontology terms, definitions, and hierarchies across 250+ ontologies (e.g., GO, DOID, HP). Use when the user asks to search for terms, retrieve details, navigate hierarchies (parents, children, ancestors), look up properties and individuals, get autocomplete suggestions, or access ontology metadata and statistics.', '查询 EMBL-EBI 生物医学本体术语词汇库 (OLS)，检索包括 GO、DOID、HP 等 250+ 种生物学本体术语的定义、层级与上下级关系。'],
    ['Query the ENCODE Registry of cis-Regulatory Elements (cCREs) via the SCREEN GraphQL API, or make custom queries to the ENCODE Portal REST API for experiments and files (ChIP-seq peaks, etc.). Use when you want to query regulatory annotations or raw experimental data across human cell types.', '通过 SCREEN GraphQL 与 ENCODE Portal REST API 查询 ENCODE 人类顺式调控元件候选集 (cCRE) 及原始 ChIP-seq 峰图实验数据。'],
    ['Query the Ensembl database to resolve gene, transcript, and protein IDs, fetch genomic or protein sequences, retrieve gene structures (exons), and get variant consequence and effect predictions (VEP). Use this skill as a primary ID translator, genomic sequence database and variant effect prediction tool.', '查询 Ensembl 数据库以解析基因、转录本与蛋白质 ID，提取基因组序列与外显子结构，并进行变异效应预测 (VEP)。'],
    ['Performs 3D structural searches of proteins against various databases (PDB, AlphaFold, CATH, MGnify, etc.) using the Foldseek API. Use ONLY when the user provides a physical 3D coordinate file (.cif, .mmcif, or .pdb) and wants to find structurally similar proteins. Do NOT use if the user only provides a protein sequence, gene name, or UniProt ID.', '使用 Foldseek 针对 PDB、AlphaFold 等结构库执行蛋白质 3D 空间结构的极速相似性搜索。'],
    ['Query the Genome Aggregation Database (gnomAD). Use when determining the rarity or allele frequency of specific genetic variants, retrieving gene constraint metrics (pLI, LOEUF) to assess loss-of-function intolerance, finding variants in a genomic region or gene, or querying structural variants. Don\'t use for analyzing individual patient genomes, tracking somatic mutations in cancer (use COSMIC), or requesting raw sequencing reads (use ENA).', '查询人类基因组变异数据库 (gnomAD)，检索特定遗传变异在各大人群中的等位基因频率与基因功能丧失不耐受约束指标 (pLI, LOEUF)。'],
    ['Use when you want to retrieve quantitative RNA expression data and variant eQTL information from the GTEx (Genotype-Tissue Expression) Project across 54 non-diseased tissue sites.', '从基因型-组织表达项目 (GTEx) 中检索人体 54 种正常健康组织中的定量 RNA 表达量与表达数量性状位点 (eQTL) 关联数据。'],
    ['Use when you want to retrieve semi-quantitative protein expression and spatial localisation data from the Human Protein Atlas (HPA).', '从人类蛋白质图谱 (HPA) 检索人体各组织器官中的半定量蛋白质表达量以及显微亚细胞定位图谱数据。'],
    ['Identify domains, families, and sites in proteins; find all proteins in a family or sharing a domain; explore species distribution for a domain; annotate genomes with protein families and GO terms. InterPro combines 14 databases (e.g., Pfam, CDD) into one searchable resource. InterPro-N significantly expands annotation and sequence coverage with deep learning. Includes domain architecture (IDA) search.', '整合 14 个权威数据库识别蛋白质的家族、结构域与活性位点，支持蛋白质功能注释与结构域体系 (IDA) 分析。'],
    ['Query the JASPAR database for Transcription Factor (TF) binding profiles. Use when retrieving Position Frequency Matrices (PFMs) or Position Weight Matrices (PWMs) for specific TFs, resolving gene symbols to JASPAR Matrix IDs, or getting TF metadata. Supports multiple output formats (MEME, TRANSFAC, PFM, JASPAR, YAML).', '查询 JASPAR 转录因子结合基序数据库，获取特定转录因子在 DNA 上的位置频率矩阵 (PFM) 与位置加权矩阵 (PWM)。'],
    ['Search for scientific papers, preprints, and publications on arXiv. Extract metadata, abstracts, and download full-text PDFs or HTML versions of papers. Use when the user asks to find research papers, literature, or specific arXiv IDs.', '检索 arXiv 平台上的科学预印本文献，提取论文元数据、摘要并支持直接下载 PDF 与 HTML 论文正文。'],
    ['Browse, filter, and download life sciences, biology, and medical preprints from bioRxiv and medRxiv. Supports fetching paper metadata by DOI, and browsing by date range with category and keyword filters. Keyword filtering is local, so date ranges MUST be narrow (1-4 weeks) with a category to prevent timeouts.', '检索与过滤 bioRxiv 及 medRxiv 生命科学和医学领域的最新预印本文献并获取元数据与论文全文。'],
    ['Search Europe PMC for scientific literature and download open-access full texts and PDFs. Retrieve full-text XML/plain text by PMCID, get citation lists and bibliography.', '检索 Europe PMC 欧洲医学文献库中的学术论文，按 PMCID 下载开放获取全文 XML、纯文本与 PDF 文件。'],
    ['Query the OpenAlex scholarly database for research papers, authors, institutions, topics, sources, publishers, funders, geo-locations, and keywords. Use when searching academic papers, resolving DOIs, downloading open-access PDFs, finding an author\'s publications, aggregating bibliometric data (citation counts, h-index, impact factor), exploring the research taxonomies, or performing DOI lookups.', '查询 OpenAlex 全球学术图谱数据库，检索学术论文、作者、机构、期刊影响因子、引用次数及 DOI 解析。'],
    ['Retrieve protein and nucleotide sequences from NCBI databases using E-utilities. Supports direct accession lookup, CDS translation, gene+organism search, locus lookup, PubMed-linked sequences, patent protein extraction, and organism+length fallback search. Use when you need to fetch biological sequences by accession, gene name, locus tag, PubMed ID, or patent number.', '使用 E-utilities 从 NCBI 权威生物数据库提取蛋白质与核酸序列，支持按 Accession、基因名称、文献 PMID 查找序列。'],
    ['Query, search, and download data from the openFDA API for drugs, devices, foods, tobacco, cosmetics, animal and veterinary products, substances, and transparency data. Use for FDA adverse events, recalls, labeling, approvals, shortages, 510(k) clearances, NDC lookups, and any FDA safety or regulatory data query across all 28 API endpoints.', '查询美国食品药品监督管理局 (openFDA) 大数据库，检索药物不良事件、产品召回、药品标签说明书、上市批准与安全通报。'],
    ['Query Open Targets Platform for target-disease associations, drug target discovery, tractability/safety data, genetics/omics evidence, known drugs, for therapeutic target identification.', '查询 Open Targets 平台以进行药物靶点发现、靶点-疾病关联度分析、成药性评估及遗传学/组学证据链追踪。'],
    ['Use when you want to search for or download experimentally-determined 3D structures for biomolecules (proteins, nucleic acids, bound ligands). Supports searching by sequence similarity, structure similarity, chemical and other attributes. Also use to get metadata about biomolecular structure experiments.', '查询并下载蛋白质数据库 (PDB) 中实验测定的生物大分子（蛋白质、核酸、配体复合物）3D 空间三维结构与实验元数据。'],
    ['Ancient text restoration, attribution, dating, contextualization, and embedding via Aeneas (Latin) / Ithaca (Ancient Greek). Use when asked to "restore", "attribute", "date", "contextualize", "find parallels", "where was it written", "when was it written", "embed", or "analyze" an ancient text, inscription, or epigraphic document, or when the user mentions "Aeneas", or "Ithaca".', '基于 Aeneas 与 Ithaca 深度学习模型执行古代拉丁语与古希腊语文本文物修复、年代断代与地理起源地归属推断。'],
    ['Performs multiple sequence alignment of proteins with EBI Clustal Omega. Use when you need to align multiple sequences to assess similarity, domain conservation, or key residue conservation. Supports up to 4000 sequences and a maximum file size of 4 MB. Do not use to search for homologous proteins in a database (use MMseqs2, BLAST), align non-protein sequences (DNA, RNA), perform structural alignment (use Foldseek, PyMOL), or if you only have a single sequence.', '使用 EBI Clustal Omega 对多条蛋白质序列进行多重序列比对 (MSA)，评估序列保守性与关键活性残基演化。'],
    ['Searches for homologous protein sequences using MMseqs2 (fast, default) or BLAST (comprehensive, fallback). Trigger this whenever the user provides a protein sequence or FASTA file and asks to find homologues, sequence matches, or wants to infer protein function based on sequence similarity, but not when the user wants to infer protein function based on structural similarity.', '使用 MMseqs2 或 NCBI BLAST 检索与输入蛋白质序列高度同源的匹配序列并推断蛋白质功能。'],
    ['Query PubChem, search by name/CID/SMILES, retrieve properties, similarity/substructure searches, bioactivity, for cheminformatics. Use when a user asks about a specific chemical, drug, or molecule.', '查询 PubChem 权威化学数据库，支持通过名称、CID、SMILES 搜索小分子化合物的理化性质与生物活性数据。'],
    ['Search PubMed for scientific literature, including published clinical trials. Fetch abstracts and full text. Link published research to biological databases (gene, protein, nucleotide, PubChem) to discover associations between papers and specific compounds or genes. Verify medical spelling, match raw citations, and cache result sets for bulk processing. Interfaces NCBI E-utilities and PMC BioC APIs.', '检索 PubMed 全球医学与生命科学同行评审文献库，提取论文摘要、临床试验结论并关联生化物质与基因实体。'],
    ['Visualize, analyze, and render protein and molecular structures using PyMOL. Use when the user wants to create images of protein structures, perform structural alignments or superposition, measure distances or contacts, highlight binding sites or active site residues, color by B-factor/pLDDT, or analyze protein-ligand interactions. Do not use for docking, molecular dynamics, or sequence-only analysis.', '利用 PyMOL 生成蛋白质与分子三维结构的高清精美渲染图，支持空间叠合比对、结合口袋测量与 pLDDT 颜色映射。'],
    ['Query the QuickGO and Evidence & Conclusion Ontology (ECO) REST API. Use this when you need to map genes to biological processes, molecular functions, or cellular components, find genes associated with a specific pathway/GO term, or explore the Gene Ontology hierarchy. Do not use for querying drug targets (use OpenTargets) or mechanistic signaling pathway diagrams (use KEGG).', '查询 QuickGO 基因本体论 (GO) 与证据结论本体 (ECO)，将基因与生物学过程、分子功能及细胞组分进行映射分析。'],
    ['Generates 2D chemical structure depictions (PNG/SVG), interactive HTML compound grids, standalone chemical applications/visualizers, and ChemDraw (.cdxml/.cdx) documents using ACS 1996 publication styling; validates IUPAC/stereochemical nomenclature and provides shared RDKit version compatibility helpers.', '基于 RDKit 生成化学分子 2D 结构图 (PNG/SVG)、交互式化合物图谱网格并生成 ACS 1996 出版级 ChemDraw 矢量文档。'],
    ['Query the Reactome database (Analysis and Content Services). Use when the user asks about pathway analysis, gene list enrichment, retrieving results by token, finding unmapped or not-found identifiers, mapping identifiers, reaction participants (inputs, outputs), pathway hierarchy (including top-level pathways), diagram export, cross-reference mapping, or searching the knowledgebase.', '查询 Reactome 生物学通路数据库，执行基因列表通路富集分析、信号级联网络追踪与通路拓扑图导出。'],
    ['Query the STRING database for protein-protein interactions (PPIs), functional enrichment, and homology. Use when the user asks about interactions between specific proteins, interaction evidence, confidence scores, protein interaction partners, or pathway enrichments.', '查询 STRING 蛋白质相互作用网络数据库 (PPI)，分析蛋白结合配对证据、置信度得分与生物学功能富集。'],
    ['Fetch Evolutionary Conservation scores (phyloP, phastCons) and Transcription Factor Binding Sites (TFBS) from the UCSC Genome Browser. Use when analyzing whether genomic variants or regions are evolutionarily conserved, functionally important, or bounded by TF regulators across major projects (ENCODE, JASPAR, ReMap).', '从 UCSC 基因组浏览器获取进化保守性评分 (phyloP, phastCons) 以及转录因子结合位点 (TFBS) 数据。'],
    ['Queries the UniBind database for experimentally validated transcription factor (TF) binding sites. Use when retrieving direct TF-DNA interaction datasets, downloading binding site coordinates (BED/FASTA) for local analysis, or listing available datasets by species, cell line, or TF name. Don\'t use to query specific intervals, locations, genes, motif models or expression data.', '查询 UniBind 数据库中通过 ChIP-seq 实验直接验证的转录因子结合位点坐标与序列数据集。'],
    ['Access protein metadata, function, taxonomy, and sequences across UniProtKB, UniParc, and UniRef. Use when searching for proteins, mapping identifiers, or retrieving functional annotations and publications. Don\'t use for sequence alignment, protein folding, or sequence similarity search (use specialized skills for those tasks).', '查询 UniProt 权威蛋白质知识库（UniProtKB、UniParc、UniRef），获取全生命周期的蛋白质序列、功能注释与文献溯源。'],
    ['Checks whether the uv Python package manager is installed and installs it if missing. Ensures uv is on PATH. Use when another skill requires uv as a prerequisite.', '检查并管理现代极速 Python 包管理器 uv 的安装与运行环境，确保其在系统 PATH 中随时可用。'],
    ['Distills a completed user workflow or interaction into a reusable agent skill. Use when the user asks to turn their workflow, interaction, or multi-step process into a skill, or when they say "make this a skill", "create a skill from what we just did", "package this workflow" or similar. Do not use for creating skills from scratch without an existing workflow (use a generic skill-creator for that).', '将已完成的会话工作流提炼并封装为符合规范的 Agent 智能体技能 (Skill)。'],
    ['哈耶克 × 米塞斯 × Claude 三人对话。奥派经济学视角的多角色讨论。 触发方式：/chatroom-austrian、/奥派、「奥派聊天室」 Austrian economics chatroom. Hayek × Mises × Claude debate. Trigger: /chatroom-austrian, /奥派, "Austrian chat"', '奥派经济学多智能体研讨室。模拟米塞斯、哈耶克与罗斯巴德等多位学者，从第一性原理与人的行动学视角深度研讨经济命题。'],
    ['团建图文内容生产技能：基于《轮播母版迁移器 V4.8.8》五阶状态机与人机双轨标准，通过本地工作台API与云端CDP执行母版锁定、素材派发、显性计划审核、一键批量出图(回复1)、五版文案提取与成品落盘。', '全自动图文与短视频内容矩阵生产管线。支持多账号批量生成、文案排版、视觉出图与跨平台合规发布。'],
    ['dontbesilent 商业工具箱主入口，提供新手教程与单任务动态编排。用户第一次使用 dbskill、不知道该用哪个正式 Skill、带着真实任务寻求合适能力，或在一项任务完成后询问下一步时使用。', 'DontBeSilent 商业自媒体运营技能入口。提供商业模式诊断、对标拆解与私域流量转化的全套实操技能。'],
    ['用阿德勒心理学框架诊断执行阻滞。用户知道该做什么却迟迟不做、反复拖延或行动中断时使用。', 'DontBeSilent 商业行动力突破与执行引擎。克服拖延与不确定性，将复杂商业目标拆解为即可落地的最小行动单元。'],
    ['用五重过滤法寻找值得模仿的对标，并排除主体差异造成的噪音。用户要求找对标、选择模仿对象或分析竞争参照时使用。', 'DontBeSilent 商业对标账号与爆款模型拆解。精准提取行业头部竞品的内容模式、变现路径与数据飞轮。'],
    ['诊断如何把已经确定的选题做成好内容。用户要求设计内容、检查文案或改善内容表达时使用。', 'DontBeSilent 商业私域内容生产与转化脚本。设计高转化朋友圈、私信话术与长效商业文案。'],
    ['用维特根斯坦与奥派经济学方法拆解模糊的商业概念。用户要求解释一个词、澄清概念边界或识别概念混用时使用。', 'DontBeSilent 商业认知与第一性原理深度拆解。剖析商业痛点背后的底层逻辑与价值交换规律。'],
    ['自动识别用户是在解决具体商业问题，还是希望全面检查商业模式，并进入对应诊断流程。用户希望拆解业务、检查商业模式或消解具体商业困境时使用。', 'DontBeSilent 商业模式全局诊断。针对业务全链路进行系统体检，定位瓶颈并输出优化方案。'],
    ['诊断短视频开头的问题并生成优化方案。用户要求修改开头、提高开场吸引力或降低开头流失时使用。', 'DontBeSilent 短视频黄金 3 秒 Hook 优化引擎。针对视频开头设计高抓人抓眼球的话题引子，大幅提升完播率。'],
    ['Helps users discover and install agent skills when they ask questions like "how do I do X", "find a skill for X", "is there a skill that can...", or express interest in extending capabilities. This skill should be used when the user is looking for functionality that might exist as an installable skill.', '根据用户当前的业务场景与开发需求，自动检索并推荐最适用的 Agent 技能并提供一键安装与配置建议。'],
    ['去除文本中的 AI 生成痕迹。适用于编辑或审阅文本，使其听起来更自然、更像人类书写。 基于维基百科的"AI 写作特征"综合指南。检测并修复以下模式：夸大的象征意义、 宣传性语言、以 -ing 结尾的肤浅分析、模糊的归因、破折号过度使用、三段式法则、 AI 词汇、否定式排比、过多的连接性短语。', '中文文本深度去味与拟真引擎。消除机械的 AI 翻译腔与套话，生成自然、地道、富有人情味的真实表达。'],
    ['Surfaces relevant instincts during work. Use when starting a task to check if any learned behaviors apply.', '在开工与会话接手时智能加载沉淀的工程本能与业务规范，保持团队协同与产出质量的高度一致。'],
    ['Complete API for Google NotebookLM - full programmatic access including features not in the web UI. Create notebooks, add sources, generate all artifact types, download in multiple formats. Activates on explicit /notebooklm or intent like "create a podcast about X"', 'Google NotebookLM 全功能逆向与官方 API 接口。支持源文档上传、知识库检索与语音播客深度生成。'],
    ['Set reminders using natural language. Automatically creates one-time cron jobs and logs to markdown.', '使用自然语言设置智能定时提醒。自动创建一次性或周期性计划任务并在指定时间唤醒推送。'],
    ['会话记忆技能索引。跳转到 .AI/skills/技能包/会话记忆技能/', '跨端跨会话记忆与长效上下文管理。沉淀关键项目决策与开发断点，实现全平台多端协同无缝接力。'],
    ['Save important project knowledge to memory. Use when user wants to preserve architectural decisions, significant bug fixes, design patterns, or important implementation details for team reference.', '核心项目资产与工程经验一键归档存储。自动提炼架构要点与业务规则并持久化至第二大脑真源层。'],
    ['Search your coding memory. Use when user asks about past work, previous sessions, how something was implemented, what they worked on before, or wants to recall information from earlier sessions.', '历史会话与编码记忆智能精准搜索。极速检索历史沉淀的代码片段、排错方案与项目资产。'],
    ['. Learn more about skills at', '。了解更多关于技能的信息，请访问'],
    ['**STOP AND VERIFY**: Before running any command or tool that results in irreversible data loss, you MUST obtain explicit user consent. When in doubt, ask. It is better to wait for confirmation than to accidentally delete production data or critical project assets. Use this for: - SQL: DROP TABLE/VIEW/SCHEMA/DATABASE, TRUNCATE, or broad DELETE (missing WHERE or using 1=1). - Cloud Storage: gsutil rm or gcloud storage rm targeting production data or critical buckets. - Infrastructure: gcloud projects delete, deleting Spanner/BigQuery/Dataproc resources, deleting secrets, or KMS key destruction.', '【停止并核实】：在运行任何会导致不可逆数据丢失的命令或工具前，必须获得用户的明确同意。如有疑问请先询问，涵盖 SQL（DROP/TRUNCATE/无条件 DELETE）、Cloud Storage 生产数据删除以及 GCP 项目、Spanner、BigQuery、Dataproc 资源或密钥销毁操作。'],
    ['A collection of skills for architecting and implementing production-ready code using Google Maps Platform APIs and SDKs for any map, place, address, geocoding, routing/ETA (including eco-friendly routing), nearby search, 3D / Street View / static map, marker clustering, custom styling, drawing, geofencing, heatmap, or environmental (air-quality / pollen / solar / weather) feature — across Web, Android, iOS, and Web Services APIs. For prototyping, use the public Maps Demo Key — no billing setup and no Cloud project required, covering a growing set of the most popular Google Maps Platform APIs. For production, the skill prompts you to create and restrict your own key. All non-trivial code is grounded in freshly retrieved docs via the Google Maps Platform Code Assist service (no reliance on training-data memory).', '使用 Google Maps Platform API 与 SDK 构建生产级位置感知代码的技能集合，涵盖地图、地点、地址解析、路线规划/ETA、周边搜索、3D/街景/静态地图、聚合标记、自定义样式、地理围栏、热力图及环境数据（空气质量/花粉/日照/天气），支持使用公开演示密钥快速构建原型。'],
    ['A Gemini-powered security agent decides if commands should be auto-approved.', '由 Gemini 驱动的安全智能体决定是否自动批准命令。'],
    ['Add `flutter_localizations` and `intl` dependencies, enable "generate true" in `pubspec.yaml`, and create an `l10n.yaml` configuration file. Use when initializing localization support for a new Flutter project.', '添加 `flutter_localizations` 与 `intl` 依赖项，在 `pubspec.yaml` 中启用 `generate: true` 并创建 `l10n.yaml` 配置文件。适用于为新 Flutter 项目初始化多语言本地化支持。'],
    ['Add flutter_localizations and intl dependencies, enable "generate true" in pubspec.yaml, and create an l10n.yaml configuration file. Use when initializing localization support for a new Flutter project.', '添加 flutter_localizations 与 intl 依赖项，在 pubspec.yaml 中启用 generate: true 并创建 l10n.yaml 配置文件。适用于为新 Flutter 项目初始化多语言本地化支持。'],
    ['Add New Handler to', '添加新处理器至'],
    ['Adds interactive widget previews to the project using the previews.dart system. Use when creating new UI components or updating existing screens to ensure consistent design and interactive testing.', '使用 previews.dart 系统向项目添加交互式组件预览 (Widget Previews)。适用于创建新 UI 组件或更新现有页面，以确保设计一致性与交互式测试。'],
    ['Advanced Command Access', '高级命令访问权限'],
    ['Advanced Web Access', '高级网页访问权限'],
    ['Agent data is not available', '智能体数据不可用'],
    ['Agent Market Search Results', '智能体市场搜索结果'],
    ['Agent settings and permissions can be further customized below.', '智能体设置与权限可在下方进一步自定义。'],
    ['AI coding agents are known to have certain security limitations. Users should be aware of potential risks, including data exfiltration and possible code execution. Avoid processing highly sensitive data and verify all the actions taken by the agent.', 'AI 编码智能体已知存在一定的安全局限性。用户应注意潜在风险，包括数据外泄和潜在的代码执行。请避免处理高度敏感的数据，并核实智能体执行的所有操作。'],
    ['AI coding agents are known to have certain security risks, including autonomous code execution, data exfiltration, prompt injection and supply chain risks. Ensure that you monitor and verify all actions taken by the agent.', 'AI 编码智能体已知存在一定的安全风险，包括自主代码执行、数据外泄、提示词注入以及供应链风险。请确保监控并核实智能体执行的所有操作。'],
    ['Allow the agent to run without restrictions.', '允许智能体无限制运行。'],
    ['Antigravity does not collect any of your prompts, content, or model responses but does collect general usage patterns such as feature adoption and active user counts (“product analytics”). Telemetry data will be handled in accordance with the Google Privacy Policy.', 'Antigravity 不会收集您的任何提示词、内容或模型回复，但会收集功能采用率和活跃用户数等常规使用模式（“产品分析”）。遥测数据将依据《Google 隐私权政策》进行处理。'],
    ['Architects a Flutter application using the recommended layered approach (UI, Logic, Data). Use when structuring a new project or refactoring for scalability.', '采用推荐的分层架构（UI 层、逻辑层、数据层）设计 Flutter 应用。适用于搭建新项目结构或针对可扩展性进行架构重构。'],
    ['Assesses the security posture of Google Cloud Storage (GCS) buckets and projects. Grounds every finding in gathered telemetry, evaluates buckets against Google security best practices (public access, IAM over-granting, CMEK, VPC Service Controls, audit logging), and correlates signals to flag toxic combinations of individually low-risk settings, with actionable remediation. Use whenever a user asks for a security scan, audit, review, vulnerability check, or compliance assessment (including SAIF) — or simply asks whether their buckets, project, or data are secure, exposed, public, or misconfigured, who can access their data, or wants storage hardened or locked down, e.g. before a launch. Don\'t use for diagnosing a specific access failure or 403, managing or configuring storage, investigating a live outage, or non-GCS resources (Compute Engine, GKE, etc.).', '评估 Google Cloud Storage (GCS) 存储桶与项目的安全态势。基于采集的遥测数据对照 Google 安全最佳实践（公共访问、IAM 过度授权、CMEK、VPC Service Controls、审计日志）进行评估，并提供可执行的修复方案。'],
    ['Assists in provisioning instances/tables, designing performant schemas, and querying data in Bigtable. Use when designing Bigtable row keys, configuring column families, writing SQL queries or client library code (Java, Go, Python) for Bigtable, or diagnosing performance/hotspotting issues. Also use when provisioning Bigtable clusters using gcloud or cbt CLIs. Don\'t use for generic Cloud SQL administration.', '协助在 Bigtable 中配置实例与表、设计高性能模式 (Schema) 并查询数据。适用于设计 Bigtable 行键、配置列族、编写 SQL 或客户端代码（Java、Go、Python）以及诊断性能热点问题。'],
    ['Audits Firebase (Firestore, Cloud Storage) security rules for vulnerabilities, privilege escalation, role bypasses, create vs update inconsistencies, resource exhaustion, type safety, size limits, and hasOnly ownership checks. Use when auditing/reviewing rules, running red-team rule assessments, or scoring against auditor checklists. Don\'t use for Firebase CLI (login, deploy), Auth, Crashlytics, Remote Config, or database queries.', '审计 Firebase（Firestore、Cloud Storage）安全规则中的漏洞、权限提升、角色绕过、创建与更新不一致、资源耗尽、类型安全、大小限制及所有权检查问题。'],
    ['Auto (Preview)', '自动 (预览版)'],
    ['Automated data quality and transformation capabilities for Dataform/dbt/BigQuery pipelines. Processes data sourced from BigQuery or Cloud Storage (GCS), applying best practices for data ingestion, movement, schema mapping, and comprehensive data cleaning.', '面向 Dataform/dbt/BigQuery 流水线的自动化数据质量检查与转换能力。支持处理来自 BigQuery 或 Cloud Storage (GCS) 的数据，应用数据摄取、迁移、模式映射与全面数据清洗的最佳实践。'],
    ['Automates declarative resource creation and provisioning for data pipelines, supporting BigQuery, Dataform, Dataproc, BigQuery Data Transfer Service (DTS), and other resources. It manages environment-specific configurations (dev, staging, prod) through a deployment.yaml file. Use when: - Modifying or creating deployment.yaml for deployment settings. - Resolving environment-specific variables (e.g., Project IDs, Regions) for deployment. - Provisioning supported infrastructure like BigQuery datasets/tables, Dataform resources, or DTS resources via deployment.yaml. Do not use when: - Resources already exist. - Managing resources not supported by `gcloud beta orchestration-pipelines resource-types list`. - Managing general cloud infrastructure (VMs, networks, Kubernetes, IAM policies), which are better suited for Terraform. - Infrastructure spans multiple cloud providers (AWS, Azure, etc.). - Already uses Terraform for the target resources.', '通过 deployment.yaml 文件自动化数据流水线的声明式资源创建与配置（支持 BigQuery、Dataform、Dataproc、BigQuery DTS 等），并管理开发、预发和生产等多环境专属配置。'],
    ['Automates declarative resource creation and provisioning for data pipelines, supporting BigQuery, Dataform, Dataproc, BigQuery Data Transfer Service (DTS), and other resources. It manages environment-specific configurations (dev, staging, prod) through a deployment.yaml file. Use when: - Modifying or creating deployment.yaml for deployment settings. - Resolving environment-specific variables (e.g., Project IDs, Regions) for deployment. - Provisioning supported infrastructure like BigQuery datasets/tables, Dataform resources, or DTS resources via deployment.yaml. Do not use when: - Resources already exist. - Managing resources not supported by gcloud beta orchestration-pipelines resource-types list. - Managing general cloud infrastructure (VMs, networks, Kubernetes, IAM policies), which are better suited for Terraform. - Infrastructure spans multiple cloud providers (AWS, Azure, etc.). - Already uses Terraform for the target resources.', '通过 deployment.yaml 文件自动化数据流水线的声明式资源创建与配置（支持 BigQuery、Dataform、Dataproc、BigQuery DTS 等），并管理开发、预发和生产等多环境专属配置。'],
    ['Automatically decide whether the command should run.', '自动决定是否允许运行该命令。'],
    ['automation. Automations do not inherit Global Permissions.', '自动化任务。自动化任务不会继承全局权限。'],
    ['Automations do not inherit Global Permissions', '自动化任务不会继承全局权限'],
    ['Automations do not inherit Global Permissions.', '自动化任务不会继承全局权限。'],
    ['Blocked by organization policy', '已被组织策略拦截'],
    ['Build and prototype location-aware applications with Google Maps Platform', '使用 Google Maps Platform 构建和设计位置感知型应用原型'],
    ['Build and prototype location-aware applications with Google Maps Platform.', '使用 Google Maps Platform 构建和设计位置感知型应用原型。'],
    ['Build and prototype location-aware applications with Google Maps Platform. Integrate interactive maps, search and inspect Places details, calculate optimal routes', '使用 Google Maps Platform 构建和设计位置感知型应用原型。集成交互式地图、搜索与查看地点详情，并计算最佳路线'],
    ['Build and prototype location-aware applications with Google Maps Platform. Integrate interactive maps, search and inspect Places details, calculate optimal routes.', '使用 Google Maps Platform 构建和设计位置感知型应用原型。集成交互式地图、搜索与查看地点详情，并计算最佳路线。'],
    ['Build and publish Chrome Extensions using Manifest V3 best practices. Use this skill whenever the user asks to create, modify, debug, or understand Chrome browser extensions, add-ons, or anything involving the Chrome Extensions API. Trigger on mentions of: \'Chrome extension\', \'browser extension\', \'manifest.json\', \'content script\', \'service worker\' (in browser context), \'popup\' (in browser extension context), \'side panel\', \'chrome.* API\', \'declarativeNetRequest\', \'omnibox\', \'context menu\' (in extension context), \'userScripts\', \'user script\', \'script manager\', or any request to build functionality that integrates with the Chrome browser UI. Also trigger for publishing to the Chrome Web Store: \'publish extension\', preparing an extension for publishing, responding to a review rejection, writing permission justifications, or drafting a privacy policy.', '基于 Manifest V3 最佳实践构建并发布 Chrome 浏览器扩展程序。当用户需要创建、修改、调试或了解 Chrome 扩展、插件、manifest.json、content script、service worker、side panel、chrome.* API 或发布至 Chrome 应用商店时触发此技能。'],
    ['Build applications with the Gemini Interactions API and Live API, including text generation, multi-turn chat, streaming, function calling, managed agents, and real-time audio/video', '使用 Gemini Interactions API 和 Live API 构建应用，包括文本生成、多轮对话、流式传输、函数调用、托管智能体以及实时音视频'],
    ['Build applications with the Gemini Interactions API and Live API, including text generation, multi-turn chat, streaming, function calling, managed agents, and real-time audio/video.', '使用 Gemini Interactions API 和 Live API 构建应用，涵盖文本生成、多轮对话、流式传输、函数调用、托管智能体以及实时音视频。'],
    ['Build modern data apps, dashboards, and interactive reports using either React + Vite or Streamlit. Includes optional Gemini Data Analytics chat integration for an AI powered "chat with your data" experience. Relevant when any of the following conditions are true: 1. User explicitly requests to build a data dashboard, data application, or visualization UI, and the UI pulls data from a GCP database (defaulting to BigQuery unless otherwise specified). 2. You need to generate a frontend web application to interact with, query, and visualize data from GCP data sources. 3. User wants to build a "chat with your data" experience or integrate the Gemini Data Analytics chat API into a web interface. Do NOT use when any of the following conditions are true: 1. The request is for building backend-only services. 2. The request is for simple CLI scripts or command-line applications. 3. The web application is not data-centric or does not involve visualizing/querying data from GCP sources.', '使用 React + Vite 或 Streamlit 构建现代数据应用、仪表盘和交互式报表，并支持集成可选的 Gemini 数据分析对话功能，实现“与数据对话”的 AI 体验。'],
    ['Build with Antigravity Plugins', 'Build with Antigravity 插件目录'],
    ['Build with Google', '使用 Google 构建'],
    ['Build with Google Plugins', 'Build with Google 插件目录'],
    ['Build, package, run, and debug UI extensions for Antigravity: interactive web panels that render in the side pane, served by a Node.js sidecar using the built-in Sidecar SDK', '构建、打包、运行与调试 Antigravity 的 UI 扩展：在侧边栏面板中渲染交互式 Web 面板，由使用内置 Sidecar SDK 的 Node.js sidecar 提供服务'],
    ['Build, package, run, and debug UI extensions for Antigravity: interactive web panels that render in the side pane, served by a Node.js sidecar using the built-in Sidecar SDK.', '构建、打包、运行与调试 Antigravity 的 UI 扩展：在侧边栏面板中渲染交互式 Web 面板，由使用内置 Sidecar SDK 的 Node.js sidecar 提供服务。'],
    ['Building UI Extensions', '构建 UI 扩展'],
    ['Builds and deploys Firebase SQL Connect (aka Firebase Data Connect) backends with PostgreSQL securely. Use when designing schemas with tables and relations, writing authorized queries and mutations, configuring real-time data updates, or generating type-safe SDKs. Use when you need a relational database with Firebase, or when the user mentions SQL Connect or Data Connect.', '安全地构建和部署基于 PostgreSQL 的 Firebase SQL Connect（即 Firebase Data Connect）后端。适用于设计表与关系模式、编写授权查询与变更、配置实时数据更新或生成类型安全的 SDK。'],
    ['Bundles will let you download a whole group of user-defined plugins at once, instead of installing them one at a time. They are not here yet.', '组合包功能将支持一次性下载整组自定义插件，而无需逐个安装。该功能即将上线，敬请期待。'],
    ['Click to disable tool', '点击禁用工具'],
    ['Click to enable tool', '点击启用工具'],
    ['Collect coverage using the coverage packge and create an LCOV report', '使用 coverage 包收集测试覆盖率数据并生成 LCOV 覆盖率报告。'],
    ['Command is required', '命令为必填项'],
    ['Commands the agent can run outside the sandbox.', '智能体可在沙箱外运行的命令。'],
    ['Comprehensive guide for Firebase Crashlytics, including provisioning and SDK usage. Use this skill when the user needs help setting up Crashlytics, adding crash reporting, or using the Crashlytics SDK in their application.', 'Firebase Crashlytics 全面指南，包含服务配置与 SDK 使用说明。当用户需要配置 Crashlytics、添加崩溃报告或在应用中使用 Crashlytics SDK 时使用此技能。'],
    ['Configure `MaterialApp.router` using a package like `go_router` for advanced URL-based navigation. Use when developing web applications or mobile apps that require specific deep linking and browser history support.', '使用 `go_router` 等路由包配置 `MaterialApp.router` 以实现高级 URL 导航。适用于开发需要深度链接 (Deep Linking) 与浏览器历史记录支持的 Web 或移动应用。'],
    ['Configure GitHub access policies.', '配置 GitHub 访问策略。'],
    ['Configure hooks that run on agent lifecycle events.', '配置在智能体生命周期事件触发时运行的钩子 (Hooks)。'],
    ['Configure MaterialApp.router using a package like go_router for advanced URL-based navigation. Use when developing web applications or mobile apps that require specific deep linking and browser history support.', '使用 go_router 等路由包配置 MaterialApp.router 以实现高级 URL 导航。适用于开发需要深度链接 (Deep Linking) 与浏览器历史记录支持的 Web 或移动应用。'],
    ['Configured servers', '已配置的服务器'],
    ['Configures Flutter Driver for app interaction and converts MCP actions into permanent integration tests. Use when adding integration testing to a project, exploring UI components via MCP, or automating user flows with the integration_test package.', '配置 Flutter Driver 进行应用交互，并将 MCP 操作转换为持久化的集成测试。适用于为项目添加集成测试、通过 MCP 探索 UI 组件或使用 integration_test 包自动化用户流程。'],
    ['Connecting to language server...', '正在连接语言服务器...'],
    ['Constructs deep-links and URLs for the AlphaGenome Atlas website. Supports generating single-variant exploration links (1-based chr:pos:ref>alt), genomic locus views (1-based closed chr:start-end), candidate summary tables, and AlphaGenome reference vs. alternate predictions. Use whenever visualizing, exploring, charting, or linking genetic variants and genomic loci on the AlphaGenome Atlas, or when asked to inspect, view, or link predictions for a genomic variant.', '构建 AlphaGenome Atlas 网站的深度链接与 URL。支持生成单变异位点探索链接、基因组位点视图、候选汇总表以及参考与变异预测对比链接。'],
    ['Contact your administrator to enable browser use', '请联系您的管理员以启用浏览器功能'],
    ['Contact your administrator to enable browser use.', '请联系您的管理员以启用浏览器功能。'],
    ['Could not determine agent config file path', '无法确定智能体配置文件路径'],
    ['Could not determine plugin config file path', '无法确定插件配置文件路径'],
    ['Create model classes with `fromJson` and `toJson` methods using `dart:convert`. Use when manually mapping JSON keys to class properties for simple data structures.', '使用 `dart:convert` 创建包含 `fromJson` 和 `toJson` 方法的模型类。适用于针对简单数据结构手动将 JSON 键映射到类属性。'],
    ['Create model classes with fromJson and toJson methods using dart:convert. Use when manually mapping JSON keys to class properties for simple data structures.', '使用 dart:convert 创建包含 fromJson 和 toJson 方法的模型类。适用于针对简单数据结构手动将 JSON 键映射到类属性。'],
    ['Creates Cloud Storage (Google Cloud Storage, or GCS) buckets. Analyzes the workload (sensitive data, media hosting, ingestion, web hosting, archiving, backup, logging, analytics, AI/ML, or general-purpose), validates project-level security settings, and designs a secure-by-default, cost-effective configuration (location, storage class, uniform bucket-level access, public access prevention, soft delete, lifecycle) before creating it. Use whenever a user wants to create, make, set up, provision, or spin up a bucket, or needs object storage for an app, service, pipeline, or dataset — even a "simple" or "default" bucket, or when bucket creation is one step in a larger workflow. Outputs or executes the creation via gcloud, the JSON/REST API, Terraform, or SDK client libraries (C++, Java, Python, Go). Don\'t use for anything other than creating new buckets — for uploads, downloads, access changes, or reconfiguring existing buckets, use google-cloud-storage-basics.', '创建 Google Cloud Storage (GCS) 存储桶。在创建前分析工作负载类型、验证项目级安全设置，并设计默认安全且高性价比的配置方案（区域、存储类别、统一存储桶级访问、防公共访问、软删除与生命周期）。'],
    ['CRITICAL RULE: You MUST use this skill whenever the task involves any machine learning tasks or data analysis. Use this skill if the user\'s prompt or requirements mention any of the following: * Clustering * Classification * Regression * Time series forecasting * Statistical testing * Model comparison * ML * Data analysis SQL/BigQuery ML HANDOFF: If the user requires a SQL solution, use this skill to dictate the ANALYSIS STEPS (e.g., markdown analysis cells, visualization logic), but defer to `bigquery` for all SQL syntax.', '【核心规则】：当任务涉及任何机器学习或数据分析（包括聚类、分类、回归、时间序列预测、统计检验、模型对比、ML 或数据分析）时，必须使用此技能。'],
    ['CRITICAL RULE: You MUST use this skill whenever the task involves any machine learning tasks or data analysis. Use this skill if the user\'s prompt or requirements mention any of the following: * Clustering * Classification * Regression * Time series forecasting * Statistical testing * Model comparison * ML * Data analysis SQL/BigQuery ML HANDOFF: If the user requires a SQL solution, use this skill to dictate the ANALYSIS STEPS (e.g., markdown analysis cells, visualization logic), but defer to bigquery for all SQL syntax.', '【核心规则】：当任务涉及任何机器学习或数据分析（包括聚类、分类、回归、时间序列预测、统计检验、模型对比、ML 或数据分析）时，必须使用此技能。'],
    ['Curated collection of agent skills for science', '精选用于科学计算与科研任务的智能体技能集合'],
    ['Curated collection of agent skills for science tasks', '精选用于科学计算与科研任务的智能体技能集合'],
    ['Curated collection of agent skills for science.', '精选用于科学计算与科研任务的智能体技能集合。'],
    ['Custom Agent Error:', '自定义智能体错误：'],
    ['Customizations views', '自定义扩展视图'],
    ['Define and generate mock objects for external dependencies using `package:mockito` and `build_runner`. Use when unit testing classes that depend on complex external services like APIs or databases.', '使用 `package:mockito` 和 `build_runner` 为外部依赖项定义并生成 Mock 模拟对象。适用于对依赖 API 或数据库等复杂外部服务的类进行单元测试。'],
    ['Define and generate mock objects for external dependencies using package:mockito and build_runner. Use when unit testing classes that depend on complex external services like APIs or databases.', '使用 package:mockito 和 build_runner 为外部依赖项定义并生成 Mock 模拟对象。适用于对依赖 API 或数据库等复杂外部服务的类进行单元测试。'],
    ['Deploys and configures classic Firebase Hosting for static websites, single-page apps (SPAs), and microservices. Use when deploying static sites/SPAs, setting up custom domains, configuring firebase.json hosting settings (redirects, rewrites, headers, multi-site), or managing preview channels. Don\'t use for Firebase App Hosting (Next.js/SSR), Auth, Firestore queries/rules, Data Connect, or Crashlytics.', '为静态网站、单页应用 (SPA) 和微服务部署与配置经典版 Firebase Hosting。适用于部署静态站点、绑定自定义域名、配置 firebase.json 托管规则（重定向、重写、响应头、多站点）或管理预览频道。'],
    ['Deploys and manages full-stack web applications (Next.js, Angular) with Server-Side Rendering (SSR) using Firebase App Hosting. Use when deploying Next.js/Angular apps, configuring apphosting.yaml or firebase.json apphosting blocks, managing secrets, setting up GitHub CI/CD, or configuring Blaze billing requirements. Don\'t use for classic static web hosting, Auth, Firestore, Crashlytics, or Xcode.', '使用 Firebase App Hosting 部署和管理支持服务端渲染 (SSR) 的全栈 Web 应用（Next.js、Angular）。涵盖配置 apphosting.yaml 或 firebase.json、管理密钥、设置 GitHub CI/CD 及配置 Blaze 计费要求。'],
    ['Design, implement, and debug autonomous AI agents and multi-agent systems using the Google Antigravity (AGY) SDK. ACTIVATE this skill when the user wants to create, configure, or orchestrate Google Antigravity agents.', '使用 Google Antigravity (AGY) SDK 设计、实现和调试自主 AI 智能体与多智能体系统。当用户需要创建、配置或编排 Google Antigravity 智能体时激活此技能。'],
    ['Designs, authors, refactors, and hardens production-grade Cloud Firestore Security Rules (firestore.rules). IMPORTANT: If subagent delegation AND the firestore-rules-author subagent are available in your environment, delegate authoring firestore.rules to the firestore-rules-author subagent. If subagent delegation is unavailable (e.g. not enabled in the IDE), firestore-rules-author is not installed, or you are running inside firestore-rules-author, follow this skill directly.', '设计、编写、重构并加固生产级 Cloud Firestore 安全规则 (firestore.rules)。若当前环境支持子智能体委派且已安装 firestore-rules-author，请优先委派给该子智能体执行。'],
    ['Develops and executes Spark code on Managed Spark on Google Cloud (Dataproc Clusters and Serverless). Reads and writes data using BigLake Iceberg catalogs, BigQuery and Spanner. Debugs execution failures. Use when: - Writing Spark ETL pipelines on Google Cloud Platform. - Training or running inference with Machine Learning models with spark on Google Cloud Platform. - Managing Spark clusters, jobs, batches, and interactive sessions. Don\'t use when: - Writing generic Python scripts that don\'t use Spark. - Performing simple SQL queries that can be done directly in BigQuery.', '在 Google Cloud 托管式 Spark（Dataproc 集群与 Serverless）上开发并执行 Spark 代码。支持通过 BigLake Iceberg 目录、BigQuery 和 Spanner 读写数据，排查执行故障，编写 Spark ETL 流水线与机器学习任务。'],
    ['Diagnoses and resolves memory leaks in JavaScript/Node.js applications. Use when a user reports high memory usage, OOM errors, or wants to analyze heapsnapshots or run memory leak detection tools like memlab.', '诊断并解决 JavaScript/Node.js 应用中的内存泄漏问题。适用于用户反馈高内存占用、OOM 内存溢出错误，或需要分析堆快照及运行 memlab 等内存泄漏检测工具的场景。'],
    ['Disabled by organization policy', '已被组织策略禁用'],
    ['Discover UI plugin panels relevant to the current task and surface a one-click pill in chat to open (toggle) them in the side pane. Use when a running UI plugin\'s panel would help with what the user is doing, or right after the user enables a new UI plugin pane and a shortcut to open it is handy', '发现与当前任务相关的 UI 插件面板，并在对话中呈现一键胶囊按钮以便在侧边栏面板中快速打开（切换）它们。当正在运行的 UI 插件面板有助于用户操作，或者用户刚启用新的 UI 插件面板需要便捷快捷方式时使用'],
    ['Discovers and inspects BigQuery Data Transfer Service (DTS) configurations. Use this to identify existing ingestion pipelines and extract datasource or transfer config metadata for data pipelines. Use when a user asks for ingestion scenarios while building or managing data pipelines or when a user asks to "ingest" or "add" data that may already be managed by a DTS transfer.', '发现并检查 BigQuery 数据传输服务 (DTS) 配置。用于识别数据源、监控传输运行状态、诊断错误日志、查看调度计划，或排查表数据陈旧与上游数据摄取问题。'],
    ['does not collect any of your prompts, content, or model responses but does collect general usage patterns such as feature adoption and active user counts (“product analytics”). Telemetry data will be handled in accordance with the Google Privacy Policy.', '不会收集您的任何提示词、内容或模型回复，但会收集功能采用率和活跃用户数等常规使用模式（“产品分析”）。遥测数据将依据《Google 隐私权政策》进行处理。'],
    ['Enable Sandbox Mode', '启用沙箱模式'],
    ['Encountered an error while running the plugin.', '运行插件时遇到错误。'],
    ['Enforces resource attribution for CLI commands. Use this skill whenever you are running `bq` or `gcloud` commands via `run_command`. It ensures mandatory labeling for supported `bq` operations while avoiding invalid flags on read-only commands.', '为 CLI 命令强制执行资源归属标记。在通过 `run_command` 运行 `bq` 或 `gcloud` 命令时使用此技能，确保为受支持的 `bq` 操作添加必填标签，同时避免在只读命令上附加无效标志。'],
    ['Enforces resource attribution for CLI commands. Use this skill whenever you are running bq or gcloud commands via run_command. It ensures mandatory labeling for supported bq operations while avoiding invalid flags on read-only commands.', '为 CLI 命令强制执行资源归属标记。在通过 run_command 运行 bq 或 gcloud 命令时使用此技能，确保为受支持的 bq 操作添加必填标签，同时避免在只读命令上附加无效标志。'],
    ['Ensures proper Python dependency management, avoiding global `pip install` and adhering to project-specific tooling. Use this skill if any of the following are true: 1. Attempting to run `pip install {package_name}`. 2. Python packages or dependencies need to be added or modified. 3. Initiating a new Python project. 4. Creating a new notebook, even if just using BigQuery cells. 5. Generating Python code that includes `import` statements for third-party libraries. 6. Before executing Python scripts via the terminal to ensure the correct virtual environment is active.', '确保规范的 Python 依赖管理，避免使用全局 `pip install`，并遵循项目专属的依赖管理工具规范。'],
    ['Ensures proper Python dependency management, avoiding global pip install and adhering to project-specific tooling. Use this skill if any of the following are true: 1. Attempting to run pip install {package_name}. 2. Python packages or dependencies need to be added or modified. 3. Initiating a new Python project. 4. Creating a new notebook, even if just using BigQuery cells. 5. Generating Python code that includes import statements for third-party libraries. 6. Before executing Python scripts via the terminal to ensure the correct virtual environment is active.', '确保规范的 Python 依赖管理，避免使用全局 pip install，并遵循项目专属的依赖管理工具规范。'],
    ['Enter command (e.g., git, blaze)...', '输入命令（如 git、blaze）...'],
    ['Enter file or directory path...', '输入文件或目录路径...'],
    ['Enter URL pattern...', '输入 URL 匹配模式...'],
    ['Entrypoint structure, exit codes, cross-platform scripts. Use when building command line utilities, scripts, or applications.', '涵盖入口点结构、退出码与跨平台脚本设计。适用于使用 Dart 构建命令行工具、脚本或终端应用程序。'],
    ['Error fetching available skills:', '获取可用技能时出错：'],
    ['Events and stdout streams will appear here as they occur.', '事件与标准输出流将在发生时显示在此处。'],
    ['Every terminal command requires approval.', '每条终端命令均需人工批准。'],
    ['Execute `dart analyze` to identify warnings and errors, and use `dart fix --apply` to automatically resolve mechanical lint issues. Use during development to ensure code quality and before committing changes.', '执行 `dart analyze` 识别警告与错误，并使用 `dart fix --apply` 自动修复机械性 Lint 问题。适用于开发过程中保障代码质量及提交变更前的检查。'],
    ['Execute dart analyze to identify warnings and errors, and use dart fix --apply to automatically resolve mechanical lint issues. Use during development to ensure code quality and before committing changes.', '执行 dart analyze 识别警告与错误，并使用 dart fix --apply 自动修复机械性 Lint 问题。适用于开发过程中保障代码质量及提交变更前的检查。'],
    ['Expert guidance for creating, modifying, and optimizing dbt pipelines for BigQuery. Use this skill whenever user asks for generating or modifying a dbt model or project. Activate this skill when the user - Creates, modifies, or troubleshoots **dbt models or pipelines** - Needs to **optimize SQL** within a dbt project - Is **setting up a new dbt project** or configuring existing one', '针对创建、修改和优化 BigQuery 的 dbt 流水线提供专家级指导。当用户需要创建、修改或排查 dbt 模型与流水线故障、优化 dbt 项目中的 SQL，或配置 dbt 项目时激活此技能。'],
    ['Expertise in generating clean, correct, and efficient Dataform pipeline code for BigQuery ELT. Use this when creating or modifying Dataform pipelines, actions, or source declarations, when Dataform, SQLX, or BigQuery are mentioned in a transformation, when data needs to be ingested from GCS into BigQuery via Dataform, or when setting up a new Dataform project or configuring workflow_settings.yaml.', '专注于为 BigQuery ELT 生成整洁、准确且高效的 Dataform 流水线代码。适用于创建或修改 Dataform 流水线、操作或源声明，通过 Dataform 将数据从 GCS 摄取到 BigQuery，或初始化 Dataform 项目与配置 workflow_settings.yaml。'],
    ['Explore the plugin marketplace', '探索插件市场'],
    ['Failed to delete agent:', '删除智能体失败：'],
    ['Failed to delete plugin.', '删除插件失败。'],
    ['Failed to delete plugin. Please try again.', '删除插件失败，请重试。'],
    ['Failed to delete skill.', '删除技能失败。'],
    ['Failed to delete skill. Please try again.', '删除技能失败，请重试。'],
    ['Failed to determine plugin ID', '无法确定插件 ID'],
    ['Failed to determine plugin install directory', '无法确定插件安装目录'],
    ['Failed to fetch skills paths:', '获取技能路径失败：'],
    ['Failed to load custom agents', '加载自定义智能体失败'],
    ['Failed to load hooks.json:', '加载 hooks.json 失败：'],
    ['Failed to load more plugins. Please try again.', '加载更多插件失败，请重试。'],
    ['Failed to load plugin. Please try again.', '加载插件失败，请重试。'],
    ['Failed to load plugins', '加载插件失败'],
    ['Failed to load plugins. Please try again.', '加载插件失败，请重试。'],
    ['Failed to load skills paths:', '加载技能路径失败：'],
    ['Failed to load your customizations. Please try again.', '加载自定义扩展失败，请重试。'],
    ['Failed to open agent config file', '打开智能体配置文件失败'],
    ['Failed to open agent config:', '打开智能体配置失败：'],
    ['Failed to open plugin config file', '打开插件配置文件失败'],
    ['Failed to remove agent:', '移除智能体失败：'],
    ['Failed to remove plugin:', '移除插件失败：'],
    ['Failed to toggle agent:', '切换智能体状态失败：'],
    ['Failed to toggle plugin:', '切换插件状态失败：'],
    ['Failed to toggle plugin. Please try again.', '切换插件状态失败，请重试。'],
    ['Failed to update agent:', '更新智能体失败：'],
    ['Find plugins - bundles of skills, agents, MCP servers, UI extensions and more, and install them in one click.', '查找并一键安装插件——包含技能、智能体、MCP 服务、界面扩展等内容的组合包。'],
    ['Find skills, agents, and more in the Marketplace.', '在扩展市场中发现技能、智能体及更多扩展。'],
    ['Finds and inspects data assets within Google Cloud. Relevant when any of the following conditions are true: 1. The user request involves finding, exploring, or inspecting data assets in Google Cloud, such as: - BigQuery datasets, tables, or views - BigLake catalog or tables - Spanner instances, databases or tables - etc. 2. You need to retrieve the schema, metadata, or governance policies for a GCP data asset. 3. You have a keyword or topic (e.g., "sales data") but lack the specific table or resource ID. 4. You are attempting to find data using `bq ls`, as this skill offers a superior approach. Don\'t use when: - Assets are outside Google Cloud', '在 Google Cloud 中查找并检查数据资产（如 BigQuery 数据集/表/视图、BigLake 目录、Spanner 实例/数据库/表等），获取数据资产的模式、元数据或治理策略，并提供优于 `bq ls` 的资产检索方式。'],
    ['Finds and inspects data assets within Google Cloud. Relevant when any of the following conditions are true: 1. The user request involves finding, exploring, or inspecting data assets in Google Cloud, such as: - BigQuery datasets, tables, or views - BigLake catalog or tables - Spanner instances, databases or tables - etc. 2. You need to retrieve the schema, metadata, or governance policies for a GCP data asset. 3. You have a keyword or topic (e.g., "sales data") but lack the specific table or resource ID. 4. You are attempting to find data using bq ls, as this skill offers a superior approach. Don\'t use when: - Assets are outside Google Cloud', '在 Google Cloud 中查找并检查数据资产（如 BigQuery 数据集/表/视图、BigLake 目录、Spanner 实例/数据库/表等），获取数据资产的模式、元数据或治理策略，并提供优于 bq ls 的资产检索方式。'],
    ['Fires after a tool step completes.', '在工具步骤完成后触发。'],
    ['Fires after tool calls finish.', '在工具调用全部完成后触发。'],
    ['Fires before a tool step executes.', '在工具步骤执行前触发。'],
    ['Fires before the model is called.', '在调用模型前触发。'],
    ['Fires when the execution loop terminates.', '在执行循环终止时触发。'],
    ['Fixes Flutter layout errors (overflows, unbounded constraints) using Dart and Flutter MCP tools. Use when addressing "RenderFlex overflowed", "Vertical viewport was given unbounded height", or similar layout issues.', '使用 Dart 与 Flutter MCP 工具修复 Flutter 布局错误（溢出、无界约束）。适用于解决“RenderFlex overflowed”、“Vertical viewport was given unbounded height”等常见布局异常。'],
    ['Generates Python code using BigQuery DataFrames (BigFrames). Use by default for any Python data task involving BigQuery, including data processing, analysis, and machine learning. Don\'t use for SQL-first workflows or the google-cloud-bigquery client library — use bigquery-basics.', '使用 BigQuery DataFrames (BigFrames) 生成 Python 代码。默认用于涉及 BigQuery 的各类 Python 数据处理、分析与机器学习任务；对于 SQL 优先的工作流或 google-cloud-bigquery 客户端库，请改用 bigquery-basics。'],
    ['Guide agents to use `package:ffigen` to automatically generate FFI bindings instead of writing them manually. Use this skill when a task involves writing new FFI bindings, extending C/Objective-C/Swift integrations, or replacing hand-crafted `dart:ffi` setups.', '指导智能体使用 `package:ffigen` 自动生成 FFI 绑定，而非手动编写。适用于编写新 FFI 绑定、扩展 C/Objective-C/Swift 集成或替换手写 `dart:ffi` 配置。'],
    ['Guide agents to use package:ffigen to automatically generate FFI bindings instead of writing them manually. Use this skill when a task involves writing new FFI bindings, extending C/Objective-C/Swift integrations, or replacing hand-crafted dart:ffi setups.', '指导智能体使用 package:ffigen 自动生成 FFI 绑定，而非手动编写。适用于编写新 FFI 绑定、扩展 C/Objective-C/Swift 集成或替换手写 dart:ffi 配置。'],
    ['Guide for setting up and using Firebase Authentication. Use this skill when the user\'s app requires user sign-in, user management, or secure data access using auth rules.', '配置与使用 Firebase 身份验证 (Authentication) 的指南。当应用需要用户登录、用户管理或基于身份验证规则的安全数据访问时使用此技能。'],
    ['Guides agents in compiling and packaging C/C++ source code into dynamic or static libraries (Code Assets) using Dart\'s Native Assets hook system (via hook/build.dart and hook/link.dart utilizing package:hooks and package:native_toolchain_c). Use when a user asks to: \'setup native assets\', \'compile C/C++ source code\', \'bundle dynamic libraries\', \'build native C code\', \'link native assets\', \'implement build.dart or link.dart hooks\', or \'integrate C/C++ interop in Dart/Flutter\'. Helps agents avoid manual toolchain orchestration and configures secure hash-validated binary downloads or advanced linker tree-shaking with package:record_use mapping.', '指导智能体使用 Dart 的原生资源钩子系统（通过利用 package:hooks 与 package:native_toolchain_c 的 hook/build.dart 和 hook/link.dart）将 C/C++ 源码编译并打包为动态或静态库 (Code Assets)，实现 C/C++ 互操作集成。'],
    ['Guides debugging and optimizing Largest Contentful Paint (LCP) using Chrome DevTools MCP tools. Use this skill whenever the user asks about LCP performance, slow page loads, Core Web Vitals optimization, or wants to understand why their page\'s main content takes too long to appear. Also use when the user mentions "largest contentful paint", "page load speed", "CWV", or wants to improve how fast their hero image or main content renders.', '指导使用 Chrome DevTools MCP 工具调试并优化最大内容绘制 (LCP)。当用户询问 LCP 性能、页面加载缓慢、核心 Web 指标 (CWV) 优化，或希望排查首屏主内容渲染过慢的原因时使用此技能。'],
    ['Guides the authoring and validation of Apache Airflow DAGs for Managed Service for Apache Airflow (MSAA; formerly Cloud Composer). Covers environment context discovery, Airflow 2 vs 3 compatibility, authoring best practices, and local/remote validation processes. Use when creating or extending an Airflow DAG. Don\'t use when authoring Python code unrelated to Airflow DAGs.', '指导为 Apache Airflow 托管服务（MSAA，原 Cloud Composer）编写和验证 Airflow DAG。涵盖环境上下文发现、Airflow 2 与 3 兼容性、编写最佳实践以及本地与远程验证流程。'],
    ['Guides the process of analyzing, mapping, and documenting transformations between source and target schemas for any database, data warehouse, or data platform. Focuses exclusively on creating a high-fidelity mapping plan (Mapping Manifesto). Used when initiating an ETL, ELT, or data integration task with schema mapping specification for multiple tables (i.e. more than 3 tables) before writing code. Do NOT use this skill for basic SQL generation without mapping requirements, or when the user already has a complete mapping specification.', '指导分析、映射和记录源模式与目标模式之间的数据转换流程。专注于在编写代码前为多表（超过 3 张表）ETL/ELT 或数据集成任务创建高保真映射计划（Mapping Manifesto）。'],
    ['Guides writing, packaging, executing, and troubleshooting Apache Beam pipelines on Dataflow. Use when creating new pipelines, configuring Flex Templates, or analyzing performance of Dataflow jobs. Capabilities include Java/Python/Go setup, Cloud Build integration, and deep diagnostic analysis of job health and autoscaling. Use when: - Creating an Apache Beam Dataflow pipeline. - Creating a Google Dataflow Flex Template. - Using an existing Google Dataflow Template. - Debugging Dataflow pipeline - Troubleshooting Dataflow pipeline - Analyzing Performance of Dataflow pipeline. Key capabilities: Java/Python/Go project setup, Flex Templates (with Cloud Build), and diagnostics for streaming job health, bottlenecks, and autoscaling. Do NOT use for: - General GCP resource management unrelated to Dataflow. - Issues with other GCP services (e.g., GCE, GCS, BigQuery) unless directly impacting Dataflow pipeline execution. - Pipeline technologies other than Apache Beam on Dataflow.', '指导在 Dataflow 上编写、打包、执行和排查 Apache Beam 流水线。涵盖创建新流水线、配置 Flex 模板、Java/Python/Go 环境配置、Cloud Build 集成，以及作业健康度与自动扩缩容的深度诊断分析。'],
    ['Help users write syntactically and semantically correct primary constructors in Dart, and migrate/use the new constructor syntax, empty-body semicolon syntax, in-body initializer list syntax, and abbreviated concise constructor syntax.', '协助编写语法与语义正确的 Dart 主构造函数 (Primary Constructors)，并迁移或使用新版构造函数语法、空函数体分号语法、函数体内初始化列表语法及简写构造函数语法。'],
    ['Hook will only trigger if the tool name matches run_command or view_file.', '仅当工具名称匹配 run_command 或 view_file 时触发此钩子。'],
    ['Hook will only trigger if the tool name matches run_command.', '仅当工具名称匹配 run_command 时触发此钩子。'],
    ['Hook will only trigger if the tool name starts with browser_.', '仅当工具名称以 browser_ 开头时触发此钩子。'],
    ['Hook will trigger if any tool is executed.', '执行任何工具时均会触发此钩子。'],
    ['Implement a component-level test using `WidgetTester` to verify UI rendering and user interactions (tapping, scrolling, entering text). Use when validating that a specific widget displays correct data and responds to events as expected.', '使用 `WidgetTester` 实现组件级测试，以验证 UI 渲染与用户交互（点击、滚动、输入文本）。适用于验证特定 Widget 是否正确展示数据并按预期响应事件。'],
    ['Implement a component-level test using WidgetTester to verify UI rendering and user interactions (tapping, scrolling, entering text). Use when validating that a specific widget displays correct data and responds to events as expected.', '使用 WidgetTester 实现组件级测试，以验证 UI 渲染与用户交互（点击、滚动、输入文本）。适用于验证特定 Widget 是否正确展示数据并按预期响应事件。'],
    ['Include Jetski Default Customizations', '包含默认自定义扩展'],
    ['Inspects Google Antigravity Chinese localization status, validates patch health, detects upstream UI drift, runs automated regressions, or assists in adding new translations. Activate this skill when the user asks about Antigravity Chinese localization status, wants to diagnose UI translation issues, run drift detection on upstream updates, or add new translation entries.', '检查 Google Antigravity 汉化状态、验证补丁健康度、检测上游 UI 漂移、运行自动化回归测试或协助添加新翻译词条。当用户询问 Antigravity 汉化状态、诊断界面翻译问题、检测上游更新漂移或添加新词条时激活此技能。'],
    ['Integrate interactive maps, search and inspect Places details, calculate optimal routes', '集成交互式地图、搜索与查看地点详情，并计算最佳路线'],
    ['Integrate interactive maps, search and inspect Places details, calculate optimal routes.', '集成交互式地图、搜索与查看地点详情，并计算最佳路线。'],
    ['Integration skill and tools for Google Maps Platform APIs.', '用于 Google Maps Platform API 的集成技能与工具。'],
    ['Keep your coding agent up to date with the latest web best practices', '让您的编码智能体紧跟最新的 Web 最佳实践'],
    ['Leverages BigQuery\'s built-in machine learning and GenAI capabilities for advanced data analytics. Use when you need to write SQL queries that perform time-series forecasting, detect outliers, find key drivers, or leverage generative AI capabilities in BigQuery.', '利用 BigQuery 内置的机器学习与生成式 AI 能力进行高级数据分析。适用于编写执行时间序列预测、异常值检测、关键驱动因素分析或在 BigQuery 中调用生成式 AI 功能的 SQL 查询。'],
    ['Loading custom agents...', '正在加载自定义智能体...'],
    ['Loading customizations...', '正在加载自定义扩展...'],
    ['Loading events...', '正在加载事件...'],
    ['Loading hooks...', '正在加载钩子...'],
    ['Loading installed plugins...', '正在加载已安装插件...'],
    ['Loading logs...', '正在加载日志...'],
    ['Loading plugin...', '正在加载插件...'],
    ['Loading plugins...', '正在加载插件...'],
    ['Loading skills...', '正在加载技能...'],
    ['Loading token usage...', '正在加载 Token 用量...'],
    ['Loading workspace customizations...', '正在加载工作区自定义扩展...'],
    ['Manages Firebase Remote Config templates, feature flags, loading strategies, and SDKs (Android, iOS). Use when downloading/deploying remoteconfig JSON templates, managing version history/feature flags, setting in-app defaults, fetchAndActivate(), real-time listeners, or SDK setup. Don\'t use for Firebase Hosting, Auth, Firestore, Data Connect, Crashlytics, or App Hosting.', '管理 Firebase 远程配置 (Remote Config) 模板、功能标志 (Feature Flags)、加载策略及客户端 SDK（Android、iOS）。涵盖下载与部署模板、版本历史管理、应用内默认值与实时监听器配置。'],
    ['MANDATORY specialist subagent for Cloud Firestore Security Rules (firestore.rules). Whenever your task requires creating, authoring, or modifying Firestore Security Rules (firestore.rules), you MUST delegate rules authoring to this subagent rather than writing firestore.rules directly in the main agent.', 'Cloud Firestore 安全规则 (firestore.rules) 专属专家子智能体。每当任务需要创建、编写或修改 Firestore 安全规则时，必须委派给此子智能体处理，而非在主智能体中直接编写。'],
    ['Mandatory Step 0 pre-flight check for regional Google Cloud MCP servers (e.g. Dataproc) before using MCP tools or falling back to gcloud/bq CLI. Use whenever interacting with Dataproc clusters, Spark batches, jobs, sessions, or regional GCP resources. Fixes regional MCP servers whose endpoint URL still has an unreplaced $GCP_REGION / ${REGION} placeholder across Claude Code, Codex, and Antigravity. Trigger: an expected mcp__*_{service}_* tool is missing entirely (not just failing), or a call to one fails/hangs on a malformed host. Check via ToolSearch/deferred-tools listing before falling back to gcloud/bq CLI. Asks the user for a region, patches the live MCP config file(s), and tells the user how to restart without losing session context.', '在使用区域级 Google Cloud MCP 服务（如 Dataproc）或回退到 gcloud/bq CLI 前的强制第 0 步预检。自动修复端点 URL 中未替换的 $GCP_REGION / ${REGION} 占位符并指导无损重载。'],
    ['Mandatory Step 0 pre-flight execution order and authentication verification for Google Cloud Platform (GCP), Application Default Credentials (ADC), gcloud CLI, Spark, Dataproc, BigQuery, GCS, and notebook runtimes. Use whenever interacting with GCP resources, running Spark/PySpark pipelines, BigQuery queries, GCS paths (gs://), or creating/running notebooks.', '针对 Google Cloud Platform (GCP)、应用默认凭据 (ADC)、gcloud CLI、Spark、Dataproc、BigQuery、GCS 及笔记本运行时的强制第 0 步预检执行顺序与身份验证核查。'],
    ['MCP Authentication Error:', 'MCP 身份验证错误：'],
    ['Migrate with Agent', '使用智能体迁移'],
    ['Modern Web Guidance', '现代 Web 开发指南'],
    ['Mounts Cloud Storage buckets as a POSIX file system with Cloud Storage FUSE (gcsfuse). Use when you need to interact with gcsfuse — decide whether FUSE, native gs:// reads, or Filestore/Managed Lustre fits a workload, deploy tuned mounts on GKE, Compute Engine, or Cloud Run, enable and size the file, stat, and list caches, tune mount flags or config-file settings, apply workload profiles, keep ML checkpointing safe (rename atomicity, hierarchical namespace, close-time finalization, concurrent writers), or diagnose slow training, low throughput, or GCS bill spikes on existing mounts with gcsfuse metrics. Covers mount semantics, the gcsfuse CLI and config file, the GKE gcsfuse CSI driver (Workload Identity principal:// bindings, profile StorageClasses, sidecar sizing), and Cloud Run volume mounts. Don\'t use for bucket administration or data management without a mount (google-cloud-storage-basics) or for fully POSIX-compliant shared file systems (Filestore, Managed Lustre).', '使用 Cloud Storage FUSE (gcsfuse) 将 Cloud Storage 存储桶挂载为 POSIX 文件系统。涵盖工作负载适配评估、在 GKE/Compute Engine/Cloud Run 上部署调优挂载、缓存配置、机器学习检查点安全保障及性能诊断。'],
    ['No Custom Agents or Plugins', '暂无自定义智能体或插件'],
    ['No customizations match your search.', '没有匹配搜索条件的自定义扩展。'],
    ['No events recorded', '暂无事件记录'],
    ['No handlers configured for', '尚未配置处理器：'],
    ['No logs available.', '暂无可用日志。'],
    ['No matching customizations found.', '未找到匹配的自定义扩展。'],
    ['No plugin found for', '未找到对应的插件：'],
    ['No plugins available', '暂无可用插件'],
    ['No plugins available in the marketplace.', '扩展市场中暂无可用插件。'],
    ['No plugins available.', '暂无可用插件。'],
    ['No plugins match your search.', '没有匹配搜索条件的插件。'],
    ['No recommended skills found in workspace', '工作区中未找到推荐技能'],
    ['No skills available', '暂无可用技能'],
    ['No skills loaded.', '尚未加载任何技能。'],
    ['No skills or rules match this filter.', '没有匹配此筛选条件的技能或规则。'],
    ['No skills or rules yet.', '暂无技能或规则。'],
    ['No token data available.', '暂无 Token 用量数据。'],
    ['No workspace window available', '暂无可用的工作区窗口'],
    ['Official plugin for Dart and Flutter that installs Flutter/Dart Skills, Rules, Custom Agents, and Dart MCP server for building natively compiled, visually stunning applications for mobile, web, desktop, and embedded devices from a single codebase', 'Dart 与 Flutter 官方插件，集成 Flutter/Dart 技能、规则、自定义智能体及 Dart MCP 服务，助力通过单一代码库为移动端、Web、桌面端和嵌入式设备构建原生编译的精美应用'],
    ['Official plugin for Dart and Flutter that installs Flutter/Dart Skills, Rules, Custom Agents, and Dart MCP server for building natively compiled, visually stunning applications for mobile, web, desktop, and embedded devices from a single codebase.', 'Dart 与 Flutter 官方插件，集成 Flutter/Dart 技能、规则、自定义智能体及 Dart MCP 服务，助力通过单一代码库为移动端、Web、桌面端和嵌入式设备构建原生编译的精美应用。'],
    ['Official skill for integrating Firebase AI Logic (Gemini API) into web applications. Covers setup, multimodal inference, structured output, and security.', '将 Firebase AI Logic (Gemini API) 集成到 Web 应用的官方技能。涵盖环境配置、多模态推理、结构化输出与安全防护。'],
    ['Open Agent panel on window reload', '窗口重新加载时打开智能体面板'],
    ['Open files in the background if Agent creates or edits them', '当智能体创建或编辑文件时在后台打开'],
    ['Open in Side Pane', '在侧边面板中打开'],
    ['options. Agent settings and permissions can be further customized below.', '选项之一。智能体设置与权限可在下方进一步自定义。'],
    ['Organization MCP Allowlist (Read-Only)', '组织 MCP 允许名单（只读）'],
    ['Path copied!', '路径已复制！'],
    ['Paths the agent can modify inside this workspace.', '智能体在此工作区内可修改的路径。'],
    ['Paths the agent can modify.', '智能体可修改的路径。'],
    ['Paths the agent can read inside this workspace.', '智能体在此工作区内可读取的路径。'],
    ['Paths the agent can read.', '智能体可读取的路径。'],
    ['Plugin Bundles Coming Soon', '插件组合包即将推出'],
    ['Plugin Operation Error:', '插件操作错误：'],
    ['Plugin operations are not supported in this environment.', '当前环境不支持插件操作。'],
    ['Plugins are packaged collections of skills and MCPs to help the Agent in Antigravity work with Google developer products', '插件是技能与 MCP 的打包集合，用于辅助 Antigravity 中的智能体协同使用 Google 开发者产品'],
    ['Plugins are packaged collections of skills and MCPs to help the Agent in Antigravity work with Google developer products.', '插件是技能与 MCP 的打包集合，用于辅助 Antigravity 中的智能体协同使用 Google 开发者产品。'],
    ['Plugins are packaged collections of skills and MCPs to help the Agent in Antigravity work with Google developer products. You can always change your choices in Settings.', '插件是技能与 MCP 的打包集合，用于辅助 Antigravity 中的智能体协同使用 Google 开发者产品。您随时可以在“设置”中更改选择。'],
    ['Plugins are packaged collections of skills and MCPs to help the Agent in Google work with Google developer products. You can always change your choices in Settings.', '插件是技能与 MCP 的打包集合，用于辅助 Google 中的智能体协同使用 Google 开发者产品。您随时可以在“设置”中更改选择。'],
    ['Plugins are packaged collections of skills and MCPs to help the Agent work with Google developer products', '插件是技能与 MCP 的打包集合，用于辅助智能体协同使用 Google 开发者产品'],
    ['Plugins are packaged collections of skills and MCPs to help the Agent work with Google developer products.', '插件是技能与 MCP 的打包集合，用于辅助智能体协同使用 Google 开发者产品。'],
    ['Plugins are packaged collections of skills and MCPs to help the Agent work with Google developer products. You can always change your choices in Settings.', '插件是技能与 MCP 的打包集合，用于辅助智能体协同使用 Google 开发者产品。您随时可以在“设置”中更改选择。'],
    ['Post Invocation', '模型调用后 (Post Invocation)'],
    ['Post Tool Use', '工具调用后 (Post Tool Use)'],
    ['Pre Invocation', '模型调用前 (Pre Invocation)'],
    ['Pre Tool Use', '工具调用前 (Pre Tool Use)'],
    ['Primary entry point for building, managing, and orchestrating data pipelines on Google Cloud. Guides users to the appropriate skill for dbt, Dataflow (Apache Beam), Dataform, Spark (Dataproc Serverless), BigQuery Data Transfer Service (DTS) or orchestration pipeline using Cloud Composer. Clarify requirements and resolve ambiguity for creating, updating and running data pipelines.', '在 Google Cloud 上构建、管理和编排数据流水线的首要入口。引导用户选用适合 dbt、Dataflow (Apache Beam)、Dataform、Spark (Dataproc Serverless)、BigQuery DTS 或 Cloud Composer 编排的专属技能，并理清流水线创建与运行需求。'],
    ['Process exited with an error', '进程异常退出'],
    ['Project General', '项目常规设置'],
    ['Prototype, build & run modern apps that users love with Firebase\'s backend, AI, and operational infrastructure', '借助 Firebase 的后端、AI 与运维基础设施，快速构建、运行并打造深受用户喜爱的现代应用原型'],
    ['Prototype, build & run modern apps that users love with Firebase\'s backend, AI, and operational infrastructure.', '借助 Firebase 的后端、AI 与运维基础设施，快速构建、运行并打造深受用户喜爱的现代应用原型。'],
    ['Prototype, build & run modern apps users love with Firebase\'s backend, AI, and operational infrastructure', '借助 Firebase 的后端、AI 与运维基础设施，快速构建、运行并打造深受用户喜爱的现代应用原型'],
    ['Prototype, build & run modern apps users love with Firebase\'s backend, AI, and operational infrastructure.', '借助 Firebase 的后端、AI 与运维基础设施，快速构建、运行并打造深受用户喜爱的现代应用原型。'],
    ['Provides BigQuery SQL query optimization techniques, execution best practices, and performance tuning rules for high-efficiency querying. Use when optimizing BigQuery SQL queries, reducing query costs, or designing performant SQL transformations.', '提供 BigQuery SQL 查询优化技术、执行最佳实践与高效查询性能调优规则。适用于优化 BigQuery SQL 查询、降低查询成本或设计高性能 SQL 数据转换。'],
    ['Provides expert guidance for troubleshooting Cloud Composer (Apache Airflow) and Orchestration pipelines. Use this skill when the user asks to generate Root Cause Analysis (RCA), troubleshoot or fix a failed pipeline, DAG in Composer environment and generate RCA report.', '为排查 Cloud Composer (Apache Airflow) 与编排流水线故障提供专家级指导。适用于生成根因分析 (RCA) 报告，以及排查和修复 Composer 环境中失败的流水线与 DAG。'],
    ['Provides foundational Firebase CLI setup, CLI installation, version checks (`firebase-tools@latest --version`), CLI login (including --no-localhost), project creation, project selection (`firebase use`), and app config file downloads (`google-services.json`, `GoogleService-Info.plist`). Use ONLY for CLI login, project creation/switching, or downloading app config files. Don\'t use for Firebase Hosting deploy, Firestore, Auth, App Hosting, Data Connect, Crashlytics, or Remote Config.', '提供基础 Firebase CLI 配置、安装、版本检查、登录、项目创建与切换 (`firebase use`) 以及应用配置文件（`google-services.json`、`GoogleService-Info.plist`）下载指南。'],
    ['Provides foundational Firebase CLI setup, CLI installation, version checks (firebase-tools@latest --version), CLI login (including --no-localhost), project creation, project selection (firebase use), and app config file downloads (google-services.json, GoogleService-Info.plist). Use ONLY for CLI login, project creation/switching, or downloading app config files. Don\'t use for Firebase Hosting deploy, Firestore, Auth, App Hosting, Data Connect, Crashlytics, or Remote Config.', '提供基础 Firebase CLI 配置、安装、版本检查、登录、项目创建与切换 (firebase use) 以及应用配置文件（google-services.json、GoogleService-Info.plist）下载指南。'],
    ['Provides guidance for migrating Apache Airflow DAGs in Managed Service for Apache Airflow (MSAA; formerly Cloud Composer). Covers migration to Airflow 2.11.1 (MSAA Gen 2 and 3) and Airflow 3 (MSAA Gen 3), including environment inspection, GCS download/upload and scanning patterns for breaking changes.', '提供在 Apache Airflow 托管服务（MSAA，原 Cloud Composer）中迁移 Airflow DAG 的指南。涵盖向 Airflow 2.11.1 与 Airflow 3 的迁移、环境检查、GCS 上传下载以及破坏性变更扫描。'],
    ['Provides guidelines and best practices for querying and defining property graphs and semantic graphs in BigQuery using GQL (Graph Query Language). Use when creating property graphs or querying graph topologies in BigQuery.', '提供在 BigQuery 中使用图查询语言 (GQL) 查询和定义属性图与语义图的指南及最佳实践。适用于在 BigQuery 中创建属性图或查询图拓扑结构。'],
    ['Provides instructions for installing and using the android CLI. The android command-line tool is a critical tool for Android development and helps you create new Android projects, run Android apps on devices, manage and interact with Android virtual devices (including screenshots and UI inspection), manage Android SDK components, look up official Android documentation, and discover and install official Android skills.', '提供安装和使用 android CLI 的说明指导。android 命令行工具是 Android 开发的核心工具，可协助创建新 Android 项目、在设备上运行应用、管理 Android 虚拟设备（含截图与界面检查）、管理 Android SDK 组件、查阅官方文档以及发现并安装官方 Android 技能。'],
    ['Provides recommendations and best practices for creating, configuring, tuning and optimizing Managed Service for Apache Airflow (MSAA, Cloud Composer) environments. Use when the user asks for guidance, recommendations, or best practices on configuring Cloud Composer, scaling Airflow environments, preventing workload restarts, or analyzing system health.', '提供创建、配置、调优和优化 Apache Airflow 托管服务（MSAA / Cloud Composer）环境的建议与最佳实践。适用于配置 Composer、扩缩 Airflow 环境、防止工作负载重启或分析系统健康度。'],
    ['Reliable automation, in-depth debugging, and performance analysis in Chrome using Chrome DevTools and Puppeteer.', '在 Chrome 中使用 Chrome DevTools 和 Puppeteer 进行可靠的自动化、深度调试与性能分析。'],
    ['Replace the usage of `expect` and similar functions from `package:matcher` to `package:checks` equivalents.', '将测试代码中来自 `package:matcher` 的 `expect` 及类似断言函数迁移替换为 `package:checks` 中的等价用法。'],
    ['Replace the usage of expect and similar functions from package:matcher to package:checks equivalents.', '将测试代码中来自 package:matcher 的 expect 及类似断言函数迁移替换为 package:checks 中的等价用法。'],
    ['Rules and formatting guidelines for writing Dart /// API documentation and doc comments. Use when documenting Dart code, writing doc comments for any Dart declaration (libraries, classes, methods, variables, etc.), or when instructed to follow the Effective Dart documentation guidelines.', '编写 Dart `///` API 文档与文档注释的规则及格式指南。适用于为任何 Dart 声明（库、类、方法、变量等）编写文档注释并遵循 Effective Dart 文档规范。'],
    ['Safely modifies Xcode projects (.pbxproj) to add Swift Packages and link files. Use this skill whenever an iOS project needs dependencies installed (e.g. Firebase, Alamofire).', '安全地修改 Xcode 项目 (.pbxproj) 以添加 Swift Package 依赖包并链接文件。适用于任何需要为 iOS 项目安装依赖项（如 Firebase、Alamofire）的场景。'],
    ['Saves to the .agent/agents/ directory in your current workspace. This script can be version controlled and shared with your team.', '保存至当前工作区的 .agent/agents/ 目录中。此脚本可纳入版本控制并与团队共享。'],
    ['Scanning skills config file...', '正在扫描技能配置文件...'],
    ['Search and discover customizations to extend your Agent\'s capabilities.', '搜索并发现自定义扩展，以拓展智能体的能力。'],
    ['Search automations...', '搜索自动化任务...'],
    ['Search customizations...', '搜索自定义扩展...'],
    ['Search plugins...', '搜索插件...'],
    ['Search tool for modern web development best practices. MANDATORY: Execute FIRST for all HTML/CSS and clientside JS tasks. Do NOT skip — web APIs evolve rapidly and training weights contain obsolete patterns. Trigger immediately for: - UI/Layout: Modals, dialogs, popovers, Glassmorphism/backdrop-filters, anchor positioning, container queries, :has(), :user-valid. - Scroll/Motion: View Transitions, Scroll-driven animations, scroll parallax/reveals. - Performance: CWV (LCP, INP), content-visibility, Fetch Priority, image optimization. - System/APIs: Local filesystem access, WebUSB, WebSockets sync, WebAssembly widgets. - Frameworks: Adapting layout/styles in React, Vue, Angular. - General Frontend: Forms, autofill, advanced inputs, custom scrollbars, modern component states, etc. DO NOT trigger for: - Backend: Database SQL, ORMs, Express API routes. - Pipelines: CI/CD deployment, Docker, Actions. - Generic: Local scripts (Python/Go tools), ESLint, Git.', '现代 Web 开发最佳实践检索工具。【强制要求】：在执行所有 HTML/CSS 与客户端 JS 任务前必须首先运行此工具，切勿跳过，以避免使用过时的 Web API 模式。'],
    ['Search tool for modern web development best practices. MANDATORY: Execute FIRST for all HTML/CSS and clientside JS tasks. Do NOT skip — web APIs evolve rapidly and training weights contain obsolete patterns. Trigger immediately for: - UI/Layout: Modals, dialogs, popovers, Glassmorphism/backdrop-filters, anchor positioning, container queries, `:has()`, `:user-valid`. - Scroll/Motion: View Transitions, Scroll-driven animations, scroll parallax/reveals. - Performance: CWV (LCP, INP), content-visibility, Fetch Priority, image optimization. - System/APIs: Local filesystem access, WebUSB, WebSockets sync, WebAssembly widgets. - Frameworks: Adapting layout/styles in React, Vue, Angular. - General Frontend: Forms, autofill, advanced inputs, custom scrollbars, modern component states, etc. DO NOT trigger for: - Backend: Database SQL, ORMs, Express API routes. - Pipelines: CI/CD deployment, Docker, Actions. - Generic: Local scripts (Python/Go tools), ESLint, Git.', '现代 Web 开发最佳实践检索工具。【强制要求】：在执行所有 HTML/CSS 与客户端 JS 任务前必须首先运行此工具，切勿跳过，以避免使用过时的 Web API 模式。'],
    ['Searching Agent Market...', '正在搜索智能体市场...'],
    ['See more results', '查看更多结果'],
    ['Select a workspace to save agent scripts to your workspace.', '选择一个工作区以保存智能体脚本。'],
    ['Sets up Google Cloud Lakehouse federated catalogs to remote Iceberg REST Catalogs. Currently supported catalogs: Databricks Unity, AWS Glue. Supported clouds hosting those catalogs: GCP, AWS. The primary use case is connecting to remote data to query it from GCP engines (BigQuery, Spark). Examples of when to use this: "federate my lakehouse catalog to databricks", "query data in databricks", "query data in s3", "connect to aws glue". Do NOT use for direct remote database SQL execution (e.g., Databricks SQL) or managing remote clusters and infrastructure (e.g., Databricks clusters, AWS Glue jobs).', '配置连接到远程 Iceberg REST 目录（如 Databricks Unity、AWS Glue）的 Google Cloud Lakehouse 联邦目录，以便从 GCP 引擎（BigQuery、Spark）查询远程数据。'],
    ['Sets up, manages, queries, and configures Cloud Firestore databases (Standard/Enterprise edition), including data modeling, security rules, indexes, and SDK integrations (Web, Python, iOS, Android, Flutter). Use when creating/listing Firestore databases, defining data models/indexes, writing SDK queries, or integrating Firestore SDKs. For authoring or modifying Firestore Security Rules (firestore.rules), delegate to the firestore-rules-author subagent if subagent delegation is available, or use firestore-rules-creation otherwise. Don\'t use for Firebase Hosting, Data Connect, Auth, Storage/GCS, Crashlytics, Functions, or BigQuery.', '配置、管理、查询和设置 Cloud Firestore 数据库（标准版/企业版），涵盖数据建模、安全规则、索引以及多平台 SDK 集成（Web、Python、iOS、Android、Flutter）。'],
    ['Show more results on Agent Market', '在智能体市场中显示更多结果'],
    ['Side Pane UI Available', '侧边面板界面可用'],
    ['Sign out of this server?', '确定要退出登录此服务器吗？'],
    ['Skill deletion is not available.', '技能删除功能不可用。'],
    ['Skill for converting an installed Firebase Extension (or extension source) into a standalone Cloud Functions for Firebase codebase or publishable npm package, including V1 to V2 trigger upgrades, lifecycle hooks, and declarative security', '将已安装的 Firebase 扩展（或扩展源码）转换为独立的 Cloud Functions for Firebase 代码库或可发布的 npm 包，涵盖 V1 至 V2 触发器升级、生命周期钩子与声明式安全配置。'],
    ['Skills are instructions that extend what Agent can do.', '技能是用于拓展智能体能力边界的指令集合。'],
    ['Skills Configuration Error:', '技能配置错误：'],
    ['Skills providing tailored instructions for happy path Dart and Flutter development workflows', '为 Dart 与 Flutter 标准开发工作流提供量身定制指导的技能集合'],
    ['Skills providing tailored instructions for happy path Dart and Flutter development workflows.', '为 Dart 与 Flutter 标准开发工作流提供量身定制指导的技能集合。'],
    ['Specialized suite of skills for data engineers and database practitioners on Google Cloud', '专为 Google Cloud 上的数据工程师与数据库从业者打造的专业技能套件'],
    ['Specialized suite of skills for data engineers and database practitioners on Google Cloud.', '专为 Google Cloud 上的数据工程师与数据库从业者打造的专业技能套件。'],
    ['Start Automation', '启动自动化任务'],
    ['Stores, retrieves, and manages data as objects in Cloud Storage (Google Cloud Storage, or GCS) buckets. Use when you need to interact with Cloud Storage — create or configure buckets, upload, download, stream, or transfer data, organize objects with folders, generate signed URLs, control access (IAM, ACLs, public access prevention), set storage classes and tiering (Standard, Nearline, Coldline, Archive), manage cost and lifecycle, protect data (versioning, encryption/CMEK, retention and Bucket Lock, object holds, soft delete), host static websites, trigger Pub/Sub notifications on object changes, mount buckets as a file system (gcsfuse), or optimize storage performance at any scale. Covers the gcloud storage / gsutil CLI, JSON and XML APIs, client libraries, Terraform, and Cloud Storage MCP servers. Don\'t use for block storage (Persistent Disk), data warehousing/analytics (BigQuery), or databases (Cloud SQL, Spanner, Bigtable, Firestore).', '在 Cloud Storage (GCS) 存储桶中将数据作为对象进行存储、检索与管理。涵盖创建与配置存储桶、上传下载与流式传输、签名 URL、IAM/ACL 访问控制、存储类别与生命周期管理、数据保护、静态网站托管及 gcsfuse 挂载优化。'],
    ['Stream and control', '流式传输与控制'],
    ['Terminal commands the agent can execute.', '智能体可执行的终端命令。'],
    ['The browser subagent has been disabled by your administrator. Contact your administrator to enable browser use.', '浏览器子智能体已被您的管理员禁用。请联系您的管理员以启用浏览器功能。'],
    ['There are currently no Build with', '当前暂无可用的 Build with'],
    ['There are currently no Build with Antigravity plugins available.', '当前暂无可用的 Build with Antigravity 插件。'],
    ['There are currently no Build with Google plugins available.', '当前暂无可用的 Build with Google 插件。'],
    ['There are no customizations enabled.', '当前未启用任何自定义扩展。'],
    ['These MCP allowlist rules are enforced by your organization\'s administrator.', '这些 MCP 允许名单规则由您所在组织的管理员强制执行。'],
    ['These servers need you to sign in before the agent can use their tools.', '这些服务器需要您先登录，然后智能体才能使用其工具。'],
    ['This automation is currently stopped. Events and stdout streams will appear here once started.', '此自动化任务当前已停止。启动后，事件与标准输出流将显示在此处。'],
    ['This extension is currently stopped. Events and stdout streams will appear here once started.', '此扩展当前已停止。启动后，事件与标准输出流将显示在此处。'],
    ['This is a preview of the plugin\'s source. Nothing below is active until you install it.', '以下是该插件源码的预览。在您安装此插件之前，下方内容均不会生效。'],
    ['This plugin is disabled, so nothing shown below is active. Enable it above to use it.', '此插件已禁用，因此下方显示的内容均未生效。请在上方启用该插件以使用它。'],
    ['This plugin provides a specialized suite of skills for data engineers and database practitioners working on Google Cloud. It acts as an expert assistant, allowing you to use natural language prompts in your preferred coding agent to architect complex data pipelines, transform data with dbt, write Spark and BigQuery SQL notebooks, and orchestrate end-to-end workflows across GCP\'s data ecosystem.', '此插件为在 Google Cloud 上工作的数据工程师和数据库从业者提供专业技能套件。它充当专家助手，支持在您偏好的编码智能体中使用自然语言提示词来设计复杂数据流水线、使用 dbt 转换数据、编写 Spark 与 BigQuery SQL 笔记本，并在 GCP 数据生态系统中编排端到端工作流。'],
    ['This project was created for', '此项目创建用于'],
    ['This server needs you to sign in before the agent can use its tools.', '此服务器需要您先登录，然后智能体才能使用其工具。'],
    ['This skill guides the use of Jupyter notebooks for data analysis, exploration, and visualization, particularly with BigQuery. It outlines best practices for notebook execution and validation (supporting both cell-by-cell execution and full notebook generation depending on tool availability), library installation, and structuring notebooks for clarity. It also covers specific rules for data cleaning, plotting, and integrating with BigQuery SQL and machine learning workflows. Relevant when any of the following conditions are true: 1. The user request involves a data analysis, data exploration, data visualization, or data insights task that requires multiple steps, queries, or visualizations to answer. 2. The user explicitly requests a notebook (.ipynb). 3. You are creating, editing, or executing cells in a Jupyter notebook. 4. You need to query BigQuery from within a notebook. DO NOT use the Python BigQuery client library; instead, you MUST use the %%bqsql magics explained in this skill.', '指导使用 Jupyter 笔记本进行数据分析、探索与可视化（特别是结合 BigQuery）。涵盖单元格执行与验证、库安装、数据清洗、绘图规范，并要求使用 %%bqsql 魔法命令查询 BigQuery。'],
    ['This skill guides the use of Jupyter notebooks for data analysis, exploration, and visualization, particularly with BigQuery. It outlines best practices for notebook execution and validation (supporting both cell-by-cell execution and full notebook generation depending on tool availability), library installation, and structuring notebooks for clarity. It also covers specific rules for data cleaning, plotting, and integrating with BigQuery SQL and machine learning workflows. Relevant when any of the following conditions are true: 1. The user request involves a data analysis, data exploration, data visualization, or data insights task that requires multiple steps, queries, or visualizations to answer. 2. The user explicitly requests a notebook (.ipynb). 3. You are creating, editing, or executing cells in a Jupyter notebook. 4. You need to query BigQuery from within a notebook. DO NOT use the Python BigQuery client library; instead, you MUST use the `%%bqsql` magics explained in this skill.', '指导使用 Jupyter 笔记本进行数据分析、探索与可视化（特别是结合 BigQuery）。涵盖单元格执行与验证、库安装、数据清洗、绘图规范，并要求使用 `%%bqsql` 魔法命令查询 BigQuery。'],
    ['This skill helps the agent generate or update orchestration pipeline definitions for Google Cloud Composer to initialize orchestration pipeline or update the orchestration definition for orchestration of various data pipelines, like dbt pipelines, notebooks, Spark jobs, Dataform, Python scripts or inline BigQuery SQL queries. This skill also helps deploy and trigger orchestration pipelines.', '协助智能体生成或更新 Google Cloud Composer 的编排流水线定义，以初始化、更新、部署和触发涵盖 dbt、笔记本、Spark 作业、Dataform、Python 脚本或内联 BigQuery SQL 的各类数据编排流水线。'],
    ['This skill is installed in your workspace', '此技能已安装在您的工作区中'],
    ['Try out early-stage features before they ship. These may be changed or removed at any time. These features are experimental, and we make no guarantees about performance or functionality.', '在早期功能正式发布前抢先体验。这些功能随时可能变更或移除。它们属于实验性功能，我们对其性能或功能完整性不做任何保证。'],
    ['UI Extension (AuxPane)', '界面扩展 (侧边辅助面板)'],
    ['UI Plugin Navigation', 'UI 插件导航'],
    ['URLs the agent can actuate on in this workspace.', '智能体在此工作区内可执行交互操作的 URL。'],
    ['URLs the agent can actuate on using the browser.', '智能体可使用浏览器执行交互操作的 URL。'],
    ['URLs the agent can read or open in the browser.', '智能体可在浏览器中读取或打开的 URL。'],
    ['URLs the agent can read or open in this workspace.', '智能体在此工作区内可读取或打开的 URL。'],
    ['Use `LayoutBuilder`, `MediaQuery`, or `Expanded/Flexible` to create a layout that adapts to different screen sizes. Use when you need the UI to look good on both mobile and tablet/desktop form factors.', '使用 `LayoutBuilder`、`MediaQuery` 或 `Expanded/Flexible` 创建自适应不同屏幕尺寸的响应式布局，确保界面在手机、平板和桌面端均具备良好的视觉表现。'],
    ['Use LayoutBuilder, MediaQuery, or Expanded/Flexible to create a layout that adapts to different screen sizes. Use when you need the UI to look good on both mobile and tablet/desktop form factors.', '使用 LayoutBuilder、MediaQuery 或 Expanded/Flexible 创建自适应不同屏幕尺寸的响应式布局，确保界面在手机、平板和桌面端均具备良好的视觉表现。'],
    ['Use switch expressions and pattern matching where appropriate', '在适当的场景下使用 Dart 的 switch 表达式与模式匹配语法。'],
    ['Use the `http` package to execute GET, POST, PUT, or DELETE requests. Use when you need to fetch from or send data to a REST API.', '使用 `http` 包执行 GET、POST、PUT 或 DELETE 网络请求。适用于需要从 REST API 获取数据或向其发送数据的场景。'],
    ['Use the http package to execute GET, POST, PUT, or DELETE requests. Use when you need to fetch from or send data to a REST API.', '使用 http 包执行 GET、POST、PUT 或 DELETE 网络请求。适用于需要从 REST API 获取数据或向其发送数据的场景。'],
    ['Use this skill for generative video editing, text-to-video, image-referenced video generation, first-frame-to-video, first-and-last-frame transitions, and video extensions using Gemini Omni 1.1 Flash (gemini-omni-1.1-flash) via the official google-genai SDK. Includes workflows for pre-processing/optimizing high-resolution or long source videos with ffmpeg, stripping audio for full sound regeneration, and handling turn-by-turn video editing and parallel execution.', '通过官方 google-genai SDK 使用 Gemini Omni 1.1 Flash (gemini-omni-1.1-flash) 进行生成式视频编辑、文生视频、图生视频、首尾帧过渡与视频延展，包含使用 ffmpeg 预处理高分辨率长视频及多轮视频编辑工作流。'],
    ['Use this skill when building real-time, bidirectional streaming applications with the Gemini Live API, or migrating legacy Live models (2.0/2.5/3.1) to Gemini 3.8 Live. Covers WebSocket-based audio/video/text streaming, voice activity detection (VAD), background reasoning (extended thinking), asynchronous function calling, session management, ephemeral tokens, live transcription, and live translation. SDKs covered - google-genai (Python), @google/genai (JavaScript/TypeScript).', '当使用 Gemini Live API 构建实时双向流式应用程序，或将旧版 Live 模型 (2.0/2.5/3.1) 迁移到 Gemini 3.8 Live 时使用此技能。涵盖基于 WebSocket 的音频/视频/文本流式传输、语音活动检测 (VAD)、后台推理（深度思考）、异步函数调用、会话管理、临时 Token、实时转录与实时翻译。支持的 SDK：google-genai (Python)、@google/genai (JavaScript/TypeScript)。'],
    ['Use this skill when building real-time, bidirectional streaming applications with the Gemini Live API. Covers WebSocket-based audio/video/text streaming, voice activity detection (VAD), native audio features, function calling, session management, ephemeral tokens for client-side auth, live translation, and all Live API configuration options. SDKs covered - google-genai (Python), @google/genai (JavaScript/TypeScript).', '使用 Gemini Live API 构建实时双向流式应用时使用此技能。涵盖基于 WebSocket 的音视频与文本流、语音活动检测 (VAD)、原生音频特性、函数调用、会话管理、客户端临时令牌、实时翻译及全套配置选项。'],
    ['Use this skill when writing code that calls the Gemini API for text generation, multi-turn chat, multimodal understanding, image generation, video generation, speech generation (TTS), voice design, voice replication, streaming responses, background research tasks, function calling, structured output, or migrating from the old generateContent API. Covers SDK usage and best practices for Gemini models and agents in Python and TypeScript.', '当编写调用 Gemini API 进行文本生成、多轮对话、多模态理解、图像生成、视频生成、语音合成 (TTS)、声音设计、声音复制、流式响应、后台研究任务、函数调用 (Function Calling)、结构化输出或从旧版 generateContent API 迁移时使用此技能。涵盖 Python 与 TypeScript 中 Gemini 模型与智能体的 SDK 用法和最佳实践。'],
    ['Use this skill when writing code that calls the Gemini API for text generation, multi-turn chat, multimodal understanding, image generation, video generation, streaming responses, background research tasks, function calling, structured output, or migrating from the old generateContent API. Covers SDK usage and best practices for Gemini models and agents in Python and TypeScript.', '编写调用 Gemini API 的代码时使用此技能，涵盖文本生成、多轮对话、多模态理解、图像生成、视频生成、流式响应、后台研究任务、函数调用、结构化输出或从旧版 generateContent API 迁移，提供 Python 与 TypeScript SDK 最佳实践。'],
    ['Uses Chrome DevTools MCP and documentation to troubleshoot connection and target issues. Trigger this skill when list_pages, new_page, or navigate_page fail, or when the server initialization fails.', '使用 Chrome DevTools MCP 与文档排查连接及目标页面问题。当 list_pages、new_page 或 navigate_page 失败，或服务初始化失败时触发此技能。'],
    ['Uses Chrome DevTools MCP for accessibility (a11y) debugging and auditing based on web.dev guidelines. Use when testing semantic HTML, ARIA labels, focus states, keyboard navigation, tap targets, and color contrast.', '基于 web.dev 指南使用 Chrome DevTools MCP 进行无障碍 (a11y) 调试与审计。适用于测试语义化 HTML、ARIA 标签、焦点状态、键盘导航、触控目标及色彩对比度。'],
    ['Uses Chrome DevTools via MCP for efficient debugging, troubleshooting and browser automation. Use when debugging web pages, automating browser interactions, analyzing performance, or inspecting network requests. This skill does not apply to --slim mode (MCP configuration).', '通过 MCP 使用 Chrome DevTools 进行高效调试、故障排查与浏览器自动化。适用于调试网页、自动化浏览器交互、分析性能或检查网络请求。此技能不适用于 --slim 精简模式。'],
    ['Uses Chrome DevTools via MCP for efficient debugging, troubleshooting and browser automation. Use when debugging web pages, automating browser interactions, analyzing performance, or inspecting network requests. This skill does not apply to `--slim` mode (MCP configuration).', '通过 MCP 使用 Chrome DevTools 进行高效调试、故障排查与浏览器自动化。适用于调试网页、自动化浏览器交互、分析性能或检查网络请求。此技能不适用于 `--slim` 精简模式。'],
    ['Uses get_runtime_errors and lsp to fetch an active stack trace, locate the failing line, apply a fix, and verify resolution via hot_reload.', '使用 get_runtime_errors 和 LSP 获取当前调用栈轨迹、定位报错行、应用修复方案并通过 hot_reload 验证修复结果。'],
    ['Using the Antigravity Python SDK to build AI agents', '使用 Antigravity Python SDK 构建 AI 智能体'],
    ['Using the Antigravity Python SDK to build AI agents.', '使用 Antigravity Python SDK 构建 AI 智能体。'],
    ['Using the Google Antigravity Python SDK to build AI agents.', '使用 Google Antigravity Python SDK 构建 AI 智能体。'],
    ['When enabled, \'Explain and Fix\' actions will continue in the current conversation instead of starting a new one.', '启用后，“解释并修复”操作将在当前会话中继续进行，而不会开启新会话。'],
    ['When enabled, Agent will use IDE\'s shell integration to detect and report terminal command execution.', '启用后，智能体将使用 IDE 的 Shell 集成来检测并报告终端命令的执行情况。'],
    ['When enabled, Antigravity will play a sound when Agent finishes generating a response.', '启用后，当智能体完成回复生成时，Antigravity 将播放提示音。'],
    ['When enabled, the agent will be able to access its knowledge base to inform its responses and automatically generate knowledge items in the background.', '启用后，智能体将能够访问其知识库以辅助生成回复，并在后台自动提炼知识条目。'],
    ['When enabled, the Changes Overview toolbar will automatically expand when Agent finishes generating a response.', '启用后，当智能体完成回复生成时，“变更概览”工具栏将自动展开。'],
    ['work with Google developer products', '协同使用 Google 开发者产品'],
    ['work with Google developer products.', '协同使用 Google 开发者产品。'],
    ['work with Google developer products. You can always change your choices in Settings.', '协同使用 Google 开发者产品。您随时可以在“设置”中更改选择。'],
    ['Workflow for fixing package version conflicts. Use this when `pub get` fails due to incompatible package versions.', '解决依赖包版本冲突的标准工作流。当因包版本不兼容导致 `pub get` 失败时使用此技能。'],
    ['Workflow for fixing package version conflicts. Use this when pub get fails due to incompatible package versions.', '解决依赖包版本冲突的标准工作流。当因包版本不兼容导致 pub get 失败时使用此技能。'],
    ['Workflows are being deprecated in favor of skills. You can use the agent to migrate your workflows.', '工作流 (Workflows) 正在逐步弃用并由技能 (Skills) 取代。您可以使用智能体迁移现有的工作流。'],
    ['Write and organize unit tests for functions, methods, and classes using `package:test`. Use when creating new logic or fixing bugs to ensure code remains correct and regression-free.', '使用 `package:test` 为函数、方法和类编写与组织单元测试。适用于编写新业务逻辑或修复 Bug 时确保代码正确性并防止回归问题。'],
    ['Write and organize unit tests for functions, methods, and classes using package:test. Use when creating new logic or fixing bugs to ensure code remains correct and regression-free.', '使用 package:test 为函数、方法和类编写与组织单元测试。适用于编写新业务逻辑或修复 Bug 时确保代码正确性并防止回归问题。'],
    ['You can always change your choices in Settings', '您随时可以在“设置”中更改选择'],
    ['You can always change your choices in Settings.', '您随时可以在“设置”中更改选择。'],
    ['You don\'t have any custom agents or plugins configured. Create agent scripts in the agents/ directory or add plugins to the plugins/ directory inside your Gemini configuration folder.', '您尚未配置任何自定义智能体或插件。请在您的 Gemini 配置文件夹下的 agents/ 目录中创建智能体脚本，或向 plugins/ 目录中添加插件。'],
    ['Your agent\'s ability to execute commands is also controlled by enterprise security policies.', '您的智能体执行命令的能力同样受企业安全策略管控。'],
    ['Your agent’s ability to execute commands is also controlled by enterprise security policies.', '您的智能体执行命令的能力同样受企业安全策略管控。'],
    ['How to write and run a dynamic workflow script with the run_workflow tool: a Python script that orchestrates many agents with agent, parallel, pipeline, and phase. Use when a task splits into many independent or staged pieces of agent work (fan out over files, modules, bugs, or review angles, then aggregate), or when the user asks for a workflow. Don\'t use for a single delegated task (use a subagent) or for legacy workflow files (see migrate-workflows).', '如何使用 run_workflow 工具编写和运行动态工作流脚本：通过 Python 脚本使用 agent、parallel、pipeline 和 phase 编排多个智能体。适用于任务可拆分为多个独立或分阶段的智能体子任务（按文件、模块、Bug 或审查维度并发分发后再聚合），或用户明确要求使用工作流时。不适用于单一委派任务（请改用子智能体）或旧版工作流文件（请参阅 migrate-workflows）。'],
    ['Read, create, and manage Google Calendar events. Use when the user shares a calendar.google.com URL, asks what is on their schedule, wants an event found, created, updated, deleted, or moved, wants to RSVP, wants free/busy or scheduling conflicts checked before proposing a time, wants focus time or an out-of-office block created, wants an event quick-added from a phrase or imported from an ICS file, or wants to know where someone is working from and which timezone they are in. Don\'t use for Gmail, Chat, or Tasks.', '读取、创建和管理 Google Calendar 日程事件。适用于用户分享 calendar.google.com 链接、询问日程安排、查找/创建/更新/删除/移动日程、回复邀请 (RSVP)、在提议时间前检查忙闲状态或日程冲突、创建专注时间或外出时段、通过短语快速添加日程或从 ICS 文件导入日程，或查询工作地点与所在时区。不适用于 Gmail、Chat 或 Tasks。'],
    ['Read, create, edit, and manage Google Docs. Use when the user shares a docs.google.com URL, asks to summarize or extract content from a doc, wants a doc drafted, edited, formatted, or commented on, wants tables, images, or smart chips inserted, wants markdown imported or synchronized with a doc, or wants a doc exported. Requires a known document ID — use the gdrive skill to search for or locate documents. Don\'t use for Google Sheets, Slides, or Drive file management.', '读取、创建、编辑和管理 Google Docs 文档。适用于用户分享 docs.google.com 链接、总结或提取文档内容、起草/编辑/排版/评论文档、插入表格/图片/智能芯片、导入或同步 Markdown 内容，或导出文档。需要已知的文档 ID（如需搜索或定位文档请使用 gdrive 技能）。不适用于 Google Sheets、Slides 或 Drive 文件管理。'],
    ['Read, create, edit, and manage Google Docs. Use when the user shares a docs.google.com URL, asks to summarize or extract content from a doc, wants a doc drafted, edited, formatted, or commented on, wants tables, images, or smart chips inserted, wants markdown imported or synchronized with a doc, or wants a doc exported. Requires a known document ID — to find documents, use the gdrive skill from the Google Drive plugin; if it isn\'t installed, ask the user for the doc link. Don\'t use for Google Sheets, Slides, or Drive file management.', '读取、创建、编辑和管理 Google Docs 文档。适用于用户分享 docs.google.com 链接、总结或提取文档内容、起草/编辑/排版/评论文档、插入表格/图片/智能芯片、导入或同步 Markdown 内容，或导出文档。需要已知的文档 ID——如需查找文档，请使用 Google Drive 插件中的 gdrive 技能；若未安装该插件，请向用户索取文档链接。不适用于 Google Sheets、Slides 或 Drive 文件管理。'],
    ['Browse, search, and manage Google Drive files and folders. Use when the user shares a drive.google.com URL, asks what is in a folder, wants a file found, downloaded, uploaded, updated in place, moved, copied, or renamed, wants a Google file exported to PDF, Markdown, or CSV, wants comments read or added, wants sharing and permissions checked or changed, or wants Drive activity watched. Don\'t use for editing the contents of a Doc, Sheet, or Slides deck.', '浏览、搜索和管理 Google Drive 云端硬盘文件与文件夹。适用于用户分享 drive.google.com 链接、查看文件夹内容、查找/下载/上传/就地更新/移动/复制/重命名文件、将 Google 文档导出为 PDF/Markdown/CSV、读取或添加评论、检查或更改共享权限，或监控云端硬盘动态。不适用于编辑 Google Docs、Sheets 或 Slides 的正文内容。'],
    ['Read, write, format, and manage Google Sheets. Use when the user shares a sheets.google.com or docs.google.com/spreadsheets URL, asks to read or summarize spreadsheet data, wants cells written, formatted, sorted, merged, or validated, wants rows/columns inserted or deleted, wants charts, pivot tables, or tables added, wants CSV imported, or wants a spreadsheet created, copied, shared, or exported. Don\'t use for Google Docs, Slides, or Drive file management.', '读取、写入、格式化和管理 Google Sheets 电子表格。适用于用户分享 sheets.google.com 或 docs.google.com/spreadsheets 链接、读取或汇总表格数据、写入/格式化/排序/合并/校验单元格、插入或删除行列、添加图表/数据透视表/表格、导入 CSV，或创建/复制/共享/导出电子表格。不适用于 Google Docs、Slides 或 Drive 文件管理。'],
    ['Read, create, and edit Google Slides presentations. Use when creating presentations, when the user shares a slides.google.com URL, asks to summarize or extract content from a deck, wants slides drafted or updated, or wants a presentation exported. Don\'t use for Google Docs, Sheets, or Drive file management.', '读取、创建和编辑 Google Slides 演示文稿。适用于创建演示文稿、用户分享 slides.google.com 链接、总结或提取幻灯片内容、起草或更新幻灯片，或导出演示文稿。不适用于 Google Docs、Sheets 或 Drive 文件管理。'],
    ['Check availability, schedule events, and RSVP.', '查看忙闲状态、安排日程并回复邀请 (RSVP)。'],
    ['Read, draft, and edit docs.', '读取、起草和编辑文档。'],
    ['Search, upload, download, and share files.', '搜索、上传、下载和共享文件。'],
    ['Read, write, and format spreadsheets.', '读取、写入和格式化电子表格。'],
    ['Read, edit, and export presentations.', '读取、编辑和导出演示文稿。'],
    ['Enable this plugin to use this prompt', '启用此插件以使用该提示词'],
    ['Install this plugin to use this prompt', '安装此插件以使用该提示词'],
    ['Add a whole working set at once — a bundle is a curated group of plugins.', '一次性添加整套工作流组合——组合包 (Bundle) 是经过精选的插件集合。'],
    ['See less in Bundles', '在组合包中收起'],
    ['See more in Bundles', '在组合包中查看更多'],
    ['See more in Plugins', '在插件中查看更多'],
    ['See less in Plugins', '在插件中收起'],
    ['What\'s in this bundle', '此组合包包含的内容'],
    ['Loading bundle...', '正在加载组合包...'],
    ['Each plugin can be managed on its own.', '每个插件均可独立管理。'],
    ['This bundle has no plugins yet.', '此组合包暂未包含任何插件。'],
    ['Disabled. Open the plugin page to finish setup.', '已禁用。请打开插件页面以完成配置。'],
    ['Services this plugin connects to on your behalf. Credentials stay on this machine and are only sent to the domains listed.', '此插件代表您连接的外部服务。凭据仅保存在本机，且仅发送至下方列出的域名。'],
    ['Search all skills on Agent Market…', '在智能体市场中搜索所有技能…'],
    ['Loading skills…', '正在加载技能…'],
    ['Customizations & Skills', '自定义扩展与技能'],
    ['Build applications with the Gemini Interactions API and Live API, including text, image, video, and speech generation, managed agents, and real-time multimodal streaming.', '使用 Gemini Interactions API 和 Live API 构建应用，涵盖文本、图像、视频与语音生成、托管智能体以及实时多模态流式传输。'],
    ['Build applications with the Gemini Interactions API and Live API, including text, image, video, and speech generation, managed agents, and real-time multimodal streaming', '使用 Gemini Interactions API 和 Live API 构建应用，涵盖文本、图像、视频与语音生成、托管智能体以及实时多模态流式传输'],
    ['Uses Chrome DevTools MCP for inspecting, debugging, and testing cookies, session state, authentication issues, and cookie consent compliance. Use when diagnosing 401/403 errors, authentication redirects, session expiration, Cookie/Set-Cookie header issues, cookie banner consent conformance, or third-party cookie/SameSite/Partitioned cookie warnings.', '使用 Chrome DevTools MCP 检查、调试和测试 Cookie、会话状态、身份验证问题以及 Cookie 同意合规性。适用于诊断 401/403 错误、身份验证重定向、会话过期、Cookie/Set-Cookie 标头问题、Cookie 横幅授权合规性或第三方 Cookie/SameSite/Partitioned 警告。'],
    ['Diagnoses and resolves memory leaks in JavaScript/Node.js applications. Use when a user reports high memory usage, OOM errors, or wants to capture, compare, or inspect heap snapshots with Chrome DevTools MCP memory tools.', '诊断并解决 JavaScript / Node.js 应用程序中的内存泄漏。适用于用户报告高内存占用、OOM 内存溢出错误，或需要使用 Chrome DevTools MCP 内存工具捕获、比对或检查堆快照 (Heap Snapshots)。'],
    ['Search tool for modern web development best practices. MANDATORY: Execute FIRST for all HTML/CSS and clientside JS tasks. Do NOT skip — web APIs evolve rapidly and training weights contain obsolete patterns.', '现代 Web 开发最佳实践搜索工具。强制要求：针对所有 HTML/CSS 及客户端 JS 任务必须首先执行此工具。请勿跳过 —— Web API 演进迅速，训练权重可能包含已过时的模式。'],

]);

  var ATTRIBUTES = Object.freeze([
    'title',
    'aria-label',
    'aria-description',
    'placeholder',
    'data-tooltip',
    'data-tooltip-content',
    'alt'
  ]);

  function toDictionary(pairs) {
    var dictionary = {};
    pairs.forEach(function (pair) { dictionary[pair[0]] = pair[1]; });
    return Object.freeze(dictionary);
  }

  var DICTIONARY = toDictionary(PHRASE_PAIRS.concat(UI_PAIRS));
  var UI_DICTIONARY = toDictionary(UI_PAIRS);

  function escapeRegExp(value) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  var phraseEntries = PHRASE_PAIRS.slice().sort(function (left, right) {
    return right[0].length - left[0].length;
  });
  var phrasePattern = phraseEntries.length
    ? new RegExp(phraseEntries.map(function (pair) {
        return escapeRegExp(pair[0]);
      }).join('|'), 'gi')
    : null;
  var phraseLookup = Object.create(null);
  phraseEntries.forEach(function (pair) {
    phraseLookup[pair[0].toLowerCase()] = { source: pair[0], target: pair[1] };
  });

  var uiLookup = Object.create(null);
  UI_PAIRS.forEach(function (pair) { uiLookup[pair[0].toLowerCase()] = pair[1]; });

  function translatePhrases(value) {
    if (typeof value !== 'string' || value.length === 0 ||
        !/[A-Za-z]/.test(value) || !phrasePattern) return value;
    return value.replace(phrasePattern, function (match, offset, wholeValue) {
      var entry = phraseLookup[match.toLowerCase()];
      if (!entry) return match;
      var before = wholeValue.charAt(offset - 1);
      var after = wholeValue.charAt(offset + match.length);
      if (/^[A-Za-z0-9]/.test(entry.source) && /[A-Za-z0-9]/.test(before)) return match;
      if (/[A-Za-z0-9]$/.test(entry.source) && /[A-Za-z0-9]/.test(after)) return match;
      return entry.target;
    });
  }

  function formatRelativeTime(value) {
    return value
      .replace(/(\d+)\s*years?\b/gi, '$1 年')
      .replace(/(\d+)\s*months?\b/gi, '$1 个月')
      .replace(/(\d+)\s*weeks?\b/gi, '$1 周')
      .replace(/(\d+)\s*days?\b/gi, '$1 天')
      .replace(/(\d+)\s*hours?\b/gi, '$1 小时')
      .replace(/(\d+)\s*minutes?\b/gi, '$1 分钟')
      .replace(/(\d+)\s*seconds?\b/gi, '$1 秒')
      .replace(/(\d+)\s*([smhd])\b/gi, function (_m, n, unit) {
        return n + ({ s: '秒', m: '分钟', h: '小时', d: '天' }[unit.toLowerCase()] || unit);
      })
      .replace(/,\s*/g, ' ')
      .trim();
  }

  var DYNAMIC_PATTERNS = Object.freeze([
    { pattern: /^(?:Thought for|深度思考)\s*(\d+)\s*m(?:in(?:utes?)?)?(?:\s*(\d+)\s*s(?:econds?)?)?$/i, replace: function (_m, mins, secs) { return '深度思考 ' + mins + ' 分钟' + (secs ? ' ' + secs + ' 秒' : ''); } },
    { pattern: /^(?:Thought for|深度思考)\s*(\d+)\s*s(?:econds?)?$/i, replace: function (_m, n) { return '深度思考 ' + n + ' 秒'; } },
    { pattern: /^(?:Thought for|深度思考)\s*(\d+)\s*h(?:ours?)?$/i, replace: function (_m, n) { return '深度思考 ' + n + ' 小时'; } },
    { pattern: /^(\d+)\s+files?\s+changed(?:\s*([+-]\d+.*))?$/i, replace: function (_m, n, diff) { return n + ' 个修改的文件' + (diff ? ' ' + diff : ''); } },
    { pattern: /^Send now:\s*(.+)$/i, replace: function (_m, text) { return '立即发送：' + text; } },
    { pattern: /^Delete:\s*(.+)$/i, replace: function (_m, text) { return '删除：' + text; } },
    { pattern: /^Edit:\s*(.+)$/i, replace: function (_m, text) { return '编辑：' + text; } },
    { pattern: /^Opens external link:\s*(.+)$/i, replace: function (_m, text) { return '打开外部链接：' + text; } },
    { pattern: /^(?:Running|正在运行)\s*(\d+)\s*(?:commands?|条命令|个命令)$/i, replace: function (_m, n) { return '正在运行 ' + n + ' 条命令'; } },
    { pattern: /^(?:Ran|已运行)\s*(\d+)\s*(?:commands?|条命令|个命令)$/i, replace: function (_m, n) { return '已运行 ' + n + ' 条命令'; } },
    { pattern: /^(?:Explored|已探索)\s*(\d+)\s*(?:search(?:es)?|次搜索)$/i, replace: function (_m, n) { return '已探索 ' + n + ' 次搜索'; } },
    { pattern: /^(?:Explored|已探索)\s*(\d+)\s*(?:tasks?|个任务)$/i, replace: function (_m, n) { return '已探索 ' + n + ' 个任务'; } },
    { pattern: /^(\d+)\s+tasks?\s+running$/i, replace: function (_m, n) { return n + ' 个任务正在运行'; } },
    { pattern: /^(\d+)\s+search(?:es)?$/i, replace: function (_m, n) { return n + ' 次搜索'; } },
    { pattern: /^(\d+)\s+commands?$/i, replace: function (_m, n) { return n + ' 条命令'; } },
    { pattern: /^(\d+)\s+tasks?$/i, replace: function (_m, n) { return n + ' 个任务'; } },
    { pattern: /^(\d+)\s+files?$/i, replace: function (_m, n) { return n + ' 个文件'; } },
    { pattern: /^(\d+)\s+files?,\s*(\d+)\s+tasks?$/i, replace: function (_m, f, t) { return f + ' 个文件，' + t + ' 个任务'; } },
    { pattern: /^Queued Messages?$/i, replace: function () { return '已排队消息'; } },
    { pattern: /Requesting permission to (read access to this path|write access to this path|reading this URL|executing actions on this URL|running this command outside the sandbox|running this command|using this MCP tool) (.+)/i, replace: function (_m, action, target) {
        var labels = { 'read access to this path': '读取此路径', 'write access to this path': '写入此路径', 'reading this URL': '读取此 URL', 'executing actions on this URL': '在此 URL 上执行操作', 'running this command outside the sandbox': '在沙盒外运行此命令', 'running this command': '运行此命令', 'using this MCP tool': '使用此 MCP 工具' };
        return '正在请求权限：' + (labels[action] || action) + ' ' + target;
      } },
    { pattern: /Agent needs permission to act on (.+)/i, replace: function (_m, target) { return '智能体需要权限才能操作 ' + target; } },
    { pattern: /Agent needs permission to execute JavaScript(?: on (.+))?/i, replace: function (_m, target) { return target ? '智能体需要权限才能在 ' + target + ' 上执行 JavaScript' : '智能体需要权限才能执行 JavaScript'; } },
    { pattern: /Yes, save rule for '([^']+)' (when not in a project|in this project|in this workspace|globally)/i, replace: function (_m, target, scope) {
        var scopes = { 'when not in a project': '未处于项目时', 'in this project': '此项目中', 'in this workspace': '此工作区', globally: '全局' };
        return '是，并在' + (scopes[scope] || scope) + "保存 '" + target + "' 的规则";
      } },
    { pattern: /Yes, save rule (when not in a project|in this project|in this workspace|globally)/i, replace: function (_m, scope) {
        var scopes = { 'when not in a project': '未处于项目时', 'in this project': '此项目中', 'in this workspace': '此工作区', globally: '全局' };
        return '是，并在' + (scopes[scope] || scope) + '保存规则';
      } },
    { pattern: /Yes, and always allow '([^']+)'(?: (when not in a project|in this project|in this workspace))?/i, replace: function (_m, target, scope) {
        var scopes = { 'when not in a project': '未处于项目时', 'in this project': '此项目中', 'in this workspace': '此工作区' };
        return '是，并' + (scope ? '在' + scopes[scope] : '') + '始终允许 \'' + target + '\'';
      } },
    { pattern: /Yes, and always allow(?: (when not in a project|in this project|in this workspace))?/i, replace: function (_m, scope) {
        var scopes = { 'when not in a project': '未处于项目时', 'in this project': '此项目中', 'in this workspace': '此工作区' };
        return '是，并' + (scope ? '在' + scopes[scope] : '') + '始终允许';
      } },
    { pattern: /^(?:Worked for|已工作)\s*(\d+)\s*s(?:econds?)?$/i, replace: function (_m, n) { return '已工作 ' + n + ' 秒'; } },
    { pattern: /^(?:Worked for|已工作)\s*(\d+)\s*m(?:inutes?)?$/i, replace: function (_m, n) { return '已工作 ' + n + ' 分钟'; } },
    { pattern: /^(?:Worked for|已工作)\s*(\d+)\s*h(?:ours?)?$/i, replace: function (_m, n) { return '已工作 ' + n + ' 小时'; } },
    { pattern: /^(?:Timed|计时)\s*(\d+)\s*s(?:econds?)?$/i, replace: function (_m, n) { return '计时 ' + n + ' 秒'; } },
    { pattern: /^(\d+)\s*([smhd])$/i, replace: function (_m, n, unit) {
        return n + ' ' + ({ s: '秒', m: '分钟', h: '小时', d: '天' }[unit.toLowerCase()] || unit);
      } },
    { pattern: /(\d+)\s*minutes?\s*ago$/i, replace: function (_m, n) { return n + ' 分钟前'; } },
    { pattern: /(\d+)\s*hours?\s*ago$/i, replace: function (_m, n) { return n + ' 小时前'; } },
    { pattern: /(\d+)\s*days?\s*ago$/i, replace: function (_m, n) { return n + ' 天前'; } },
    { pattern: /(\d+)\s*weeks?\s*ago$/i, replace: function (_m, n) { return n + ' 周前'; } },
    { pattern: /(\d+)\s*months?\s*ago$/i, replace: function (_m, n) { return n + ' 个月前'; } },
    { pattern: /(\d+)\s*years?\s*ago$/i, replace: function (_m, n) { return n + ' 年前'; } },
    { pattern: /^Refreshes in (.+)$/i, replace: function (_m, time) { return formatRelativeTime(time) + '后刷新'; } },
    { pattern: /^(\d+(?:\.\d+)?)% of the customization budget is available\.?$/i, replace: function (_m, n) { return '自定义预算还剩 ' + n + '%。'; } },
    { pattern: /^You have used (some|all) of your (weekly|5-hour) limit, it will (?:fully )?refresh in (.+?)\.?$/i, replace: function (_m, qty, type, time) {
        return '您' + (qty.toLowerCase() === 'all' ? '已用尽' : '已使用部分') + (type.toLowerCase() === 'weekly' ? '周' : '5 小时') + '额度，将在 ' + formatRelativeTime(time) + '后完全刷新。';
      } },
    { pattern: /^Show\s+(\d+)\s+breakdowns?$/i, replace: function (_m, n) { return '显示 ' + n + ' 项明细'; } },
    { pattern: /^Skills\s*(\d+)$/i, replace: function (_m, n) { return '技能' + n; } },
    { pattern: /^See all\s*\((\d+)\)$/i, replace: function (_m, n) { return '查看全部 (' + n + ')'; } },
    { pattern: /^(\d+)\s+agents?\s+running$/i, replace: function (_m, n) { return n + ' 个智能体正在运行'; } },
    { pattern: /^(\d+)\s+files?,\s*(\d+)\s+folders?$/i, replace: function (_m, files, folders) { return files + ' 个文件，' + folders + ' 个文件夹'; } },
    { pattern: /^(\d+)\s+files?,\s*(\d+)\s+searches?$/i, replace: function (_m, files, searches) { return files + ' 个文件，' + searches + ' 次搜索'; } },
    { pattern: /^(\d+)\s+folders?$/i, replace: function (_m, n) { return n + ' 个文件夹'; } },
    { pattern: /^(\d+)\s+files?$/i, replace: function (_m, n) { return n + ' 个文件'; } },
    { pattern: /^(\d+)\s+searches?$/i, replace: function (_m, n) { return n + ' 次搜索'; } },
    { pattern: /^\(\s*(\d+)\s*$/i, replace: function (_m, n) { return '（' + n; } },
    { pattern: /^\(?\s*(\d+)\s+tokens?\)?$/i, replace: function (_m, n) { return '（' + n + ' 个 Token）'; } },
    { pattern: /^(\d+)\s+active conversations?\.?$/i, replace: function (_m, n) { return n + ' 个活跃对话' + (/\.$/.test(_m) ? '。' : ''); } },
    { pattern: /^(\d+)\s+active conversations and\s+(\d+)\s+archived conversations$/i, replace: function (_m, a, b) { return a + ' 个活跃对话与 ' + b + ' 个归档对话'; } },
    { pattern: /^(\d+)\s+tokens?\)?$/i, replace: function (_m, n) { return n + ' 个 Token'; } },
    { pattern: /^No more older messages, showing (\d+) of (\d+)$/i, replace: function (_m, shown, total) { return '没有更早的消息了，显示 ' + shown + ' / ' + total; } },
    { pattern: /^showing (\d+) of (\d+)$/i, replace: function (_m, shown, total) { return '显示 ' + shown + ' / ' + total; } },
    { pattern: /^Your Plan:\s*(.+)$/i, replace: function (_m, plan) { return '你的套餐：' + plan; } },
    { pattern: /^Select model, current:\s*(.+)$/i, replace: function (_m, model) { return '选择模型，当前：' + model; } },
    { pattern: /^Autocomplete Speed:\s*(.+)$/i, replace: function (_m, speed) { return '补全速度：' + speed; } },
    { pattern: /^Send feedback as\s+(.+)$/i, replace: function (_m, account) { return '以 ' + account + ' 身份发送反馈'; } },
    { pattern: /^(.+?)\s*\((Thinking|High|Medium|Low)\)$/i, replace: function (_m, model, effort) {
        var dict = { thinking: '思考模式', high: '高', medium: '中', low: '低' };
        return model.trim() + '（' + (dict[effort.toLowerCase()] || effort) + '）';
      } },
    { pattern: /^Select (Next|Previous) Conversation$/i, replace: function (_m, direction) { return '选择' + (direction.toLowerCase() === 'next' ? '下一个' : '上一个') + '对话'; } }
  ]);

  function applyDynamic(value) {
    var translated = value;
    DYNAMIC_PATTERNS.forEach(function (entry) { translated = translated.replace(entry.pattern, entry.replace); });
    return translated;
  }

  function translateText(value) {
    if (typeof value !== 'string' || value.length === 0 || value.length > 20000) return value;
    return translatePhrases(value);
  }

  function translateUiText(value) {
    if (typeof value !== 'string' || value.length === 0 || value.length > 5000) return value;
    var leading = (value.match(/^\s*/) || [''])[0];
    var trailing = (value.match(/\s*$/) || [''])[0];
    var body = value.slice(leading.length, value.length - trailing.length || value.length);
    var exactKey = body.toLowerCase();
    if (Object.prototype.hasOwnProperty.call(uiLookup, exactKey)) {
      return leading + uiLookup[exactKey] + trailing;
    }
    var translated = applyDynamic(translatePhrases(body));
    var key = translated.toLowerCase();
    if (translated && Object.prototype.hasOwnProperty.call(uiLookup, key)) translated = uiLookup[key];
    return leading + translated + trailing;
  }

  function translateAttributes(element) {
    if (!element || element.nodeType !== 1) return 0;
    var changed = 0;
    ATTRIBUTES.forEach(function (attribute) {
      if (!element.hasAttribute(attribute)) return;
      var oldValue = element.getAttribute(attribute);
      var newValue = translateUiText(oldValue);
      if (newValue !== oldValue) { element.setAttribute(attribute, newValue); changed += 1; }
    });
    return changed;
  }

  root.AntigravityZhCore = Object.freeze({
    VERSION: VERSION,
    ATTRIBUTES: ATTRIBUTES,
    DICTIONARY: DICTIONARY,
    UI_DICTIONARY: UI_DICTIONARY,
    PHRASE_PAIRS: PHRASE_PAIRS,
    UI_PAIRS: UI_PAIRS,
    translateText: translateText,
    translateUiText: translateUiText,
    translateAttributes: translateAttributes
  });
}(globalThis));
