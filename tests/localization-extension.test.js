'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const projectRoot = path.resolve(__dirname, '..');
const extensionRoot = path.join(projectRoot, 'src', 'localization-extension');
const manifest = JSON.parse(fs.readFileSync(path.join(extensionRoot, 'manifest.json'), 'utf8'));
const coreSource = fs.readFileSync(path.join(extensionRoot, 'translation-core.js'), 'utf8');
const contentSource = fs.readFileSync(path.join(extensionRoot, 'content.js'), 'utf8');
const loaderSource = fs.readFileSync(path.join(projectRoot, 'src', 'Antigravity-CdpLocalizationLoader.cs'), 'utf8');

assert.strictEqual(manifest.manifest_version, 3);
assert.strictEqual(manifest.version, '0.4.0');
assert.deepStrictEqual(manifest.content_scripts[0].js, ['translation-core.js', 'content.js']);
assert.ok(manifest.content_scripts[0].matches.includes('https://127.0.0.1/*'));
assert.ok(contentSource.includes('DEBOUNCE_MS = 80'));
assert.ok(contentSource.includes('MAX_WAIT_MS = 300'));
assert.ok(contentSource.includes('MutationObserver'));
assert.ok(contentSource.includes('attributeFilter: core.ATTRIBUTES'));
assert.ok(contentSource.includes('conversation-row-sidebar'));
assert.ok(contentSource.includes('isProtectedTextElement'));
assert.ok(contentSource.includes('translateUiText'));
assert.ok(contentSource.includes('__AntigravityZhContentInstalled'));
assert.ok(contentSource.includes('lastTextValues'));
assert.ok(contentSource.includes('lastAttributeValues'));
assert.ok(contentSource.includes('hasPendingAncestor'));
assert.ok(contentSource.includes('NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT'));
assert.ok(loaderSource.includes('DevToolsActivePort'));
assert.ok(loaderSource.includes('Page.addScriptToEvaluateOnNewDocument'));
assert.ok(loaderSource.includes('Runtime.evaluate'));

const context = { console, Set, Date, Object, RegExp, globalThis: null };
context.globalThis = context;
vm.runInNewContext(coreSource, context, { filename: 'translation-core.js' });
const core = context.AntigravityZhCore;
assert.ok(core);

const requiredTranslations = {
  'New Conversation': '新建对话',
  'Projects': '项目管理',
  'Scheduled Tasks': '定时任务',
  'Skills & Customizations': '技能与自定义扩展',
  'Settings': '软件设置',
  'Subagents': '子智能体',
  'Background Tasks': '后台任务',
  'Artifacts': '方案产物',
  'Files Changed': '修改文件',
  'Terminals': '终端控制台',
  'Implementation Plan': '方案实施规划书',
  'Walkthrough': '任务交付复盘',
  'Choose the active Gemini model': '选择当前会话使用的 Gemini 思考与推理模型',
  'Controls whether terminal commands require approval before running': '设置 AI 在运行终端命令或脚本时是否需要用户审批',
  'Run agent commands inside a restricted sandbox environment for added security': '在受限沙箱中运行命令，防止意外修改主机系统以提高安全性',
  'Controls whether the agent can read or write files outside the current workspace root': '控制 AI 是否可以读取或写入当前项目工作区目录之外的文件',
  'Controls whether the agent can make network requests': '控制 AI 是否可以通过网络发起外部 HTTP 请求或抓取网页',
  'Define global allow/deny rules for specific files, commands, and URLs': '为特定的文件路径、终端命令及网址定义全局允许/拒绝规则',
  'Keep computer awake during long-running tasks': '当有长时间任务在后台运行时，阻止电脑自动进入睡眠模式',
  'Run in background when the window is closed': '关闭主窗口后保持在 Windows 系统托盘后台静默运行',
  'Auto-check for updates': '自动检查版本更新',
  'always-proceed': '始终自动执行',
  'request-review': '执行前请求确认',
  'proceed-in-sandbox': '在沙箱中执行',
  'Planning Mode': '规划模式',
  'Waiting for user input': '等待用户输入'
};

for (const [source, target] of Object.entries(requiredTranslations)) {
  assert.strictEqual(core.DICTIONARY[source], target, source);
  if (core.PHRASE_PAIRS.some((pair) => pair[0] === source)) {
    assert.strictEqual(core.translateText(`  ${source}  `), `  ${target}  `, source);
  } else {
    assert.strictEqual(core.translateUiText(`  ${source}  `), `  ${target}  `, source);
  }
}

assert.strictEqual(
  core.translateUiText('New Conversation / always-proceed'),
  '新建对话 / always-proceed'
);
assert.strictEqual(
  core.translateText('Conversation General On Off Running'),
  'Conversation General On Off Running'
);
assert.strictEqual(core.translateText('safe Settings inside a code block'), 'safe Settings inside a code block');
assert.strictEqual(core.translateUiText('Agent Settings'), '智能体设置');
assert.strictEqual(core.translateUiText('Show 40 breakdowns'), '显示 40 项明细');
assert.strictEqual(core.translateUiText('See all (7)'), '查看全部 (7)');
assert.strictEqual(core.translateUiText('Inherit General'), '继承常规设置');
assert.strictEqual(core.translateUiText('Local Permissions'), '本地权限');
assert.strictEqual(core.translateUiText('Also includes'), '在此项目中工作时还包括');
assert.strictEqual(core.translateUiText('when working in this project.'), '。');
assert.strictEqual(core.translateUiText('to be installed.'), '才能运行。');
assert.strictEqual(core.translateUiText('Danger Zone'), '危险区域');
assert.strictEqual(core.translateUiText('Permanently delete'), '永久删除');
assert.strictEqual(core.translateUiText('including'), '包括');
assert.strictEqual(core.translateUiText('(351 tokens)'), '（351 个 Token）');
assert.strictEqual(core.translateUiText('(351'), '（351');
assert.strictEqual(core.translateUiText('.'), '。');
assert.strictEqual(core.translateUiText('Learn more.'), '了解更多。');
assert.strictEqual(core.translateUiText('25 active conversations'), '25 个活跃对话');
assert.strictEqual(core.translateUiText('25 active conversations.'), '25 个活跃对话。');
assert.strictEqual(core.translateUiText('Open Editor Settings'), '打开编辑器设置');
assert.strictEqual(
  core.translateUiText('Manage Project Folders, agent settings, and permissions.'),
  '管理项目文件夹、智能体设置和权限。'
);
assert.strictEqual(core.translateUiText('2h'), '2 小时');
assert.strictEqual(core.translateUiText('Select model, current: Gemini 3.7 Flash High'), '选择模型，当前：Gemini 3.7 Flash High');
assert.strictEqual(
  core.translateUiText("Yes, and always allow 'npm test' in this workspace"),
  "是，并在此工作区始终允许 'npm test'"
);
assert.strictEqual(core.translateUiText('General Greeting Conversation'), 'General Greeting Conversation');
assert.strictEqual(
  core.translateText('Configure the agent\'s visual theme and display preferences.'),
  '配置智能体的视觉主题与显示偏好。'
);
assert.ok(core.ATTRIBUTES.includes('aria-label'));
assert.ok(core.ATTRIBUTES.includes('placeholder'));
assert.ok(core.PHRASE_PAIRS.length >= 300);
assert.ok(core.UI_PAIRS.length >= 500);

console.log('localization-extension.test.js: PASS');
