'use strict';

// Read-only live check for a running local Antigravity window. It does not
// click, type, send a model request, or modify the page.
const fs = require('fs');
const path = require('path');

const devToolsPortFile = path.join(
  process.env.APPDATA || '',
  'Antigravity',
  'DevToolsActivePort'
);

const requiredChinese = [
  '新建对话',
  '项目管理',
  '定时任务',
  '技能与自定义扩展',
  '软件设置',
  '子智能体',
  '后台任务',
  '方案产物',
  '修改文件',
  '终端控制台',
  '方案实施规划书',
  '任务交付复盘',
  '对话历史',
  '已固定对话',
  '智能体设置',
  '安全预设',
  '智能体行为',
  '产物审核策略',
  '文件访问规则',
  '网络访问规则',
  '终端与工具权限',
  '模型与用量',
  '模型积分',
  '模型额度',
  '自定义扩展',
  '防止睡眠',
  '插件市场',
  '浏览器设置',
  '键盘快捷键',
  '账户',
  '规划模式',
  '等待用户输入'
];

const forbiddenMixed = [
  'Agent 软件设置',
  '开启 方案产物',
  'File Access 规则',
  'Commands Outside 沙箱',
  '模型 Context Protocol',
  '模型 & Usage',
  '模型 Credits',
  '模型 Quota',
  'Manage 项目文件夹, agent settings, and permissions.',
  'Local Permissions',
  'Also includes 全局设置 when working in this project.',
  'Google Chrome to be installed.',
  'Open 编辑器设置',
  'Permanently delete',
  'Danger Zone',
  'Notification 软件设置',
  '键盘快捷键 for quick navigation and control.'
];

function cdpCall(webSocketUrl, method, params) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(webSocketUrl);
    const id = 1;
    const timer = setTimeout(() => {
      socket.close();
      reject(new Error('cdp_timeout'));
    }, 5000);

    socket.addEventListener('error', (event) => {
      clearTimeout(timer);
      reject(event.error || new Error('cdp_connection_error'));
    });
    socket.addEventListener('open', () => {
      socket.send(JSON.stringify({ id, method, params }));
    });
    socket.addEventListener('message', (event) => {
      const message = JSON.parse(event.data);
      if (message.id !== id) return;
      clearTimeout(timer);
      socket.close();
      resolve(message);
    });
  });
}

async function main() {
  if (!fs.existsSync(devToolsPortFile)) {
    throw new Error('DevToolsActivePort_missing');
  }
  const port = fs.readFileSync(devToolsPortFile, 'utf8').split(/\r?\n/)[0].trim();
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const target = targets.find((item) => item.type === 'page' && /^https?:\/\/(127\.0\.0\.1|localhost)/.test(item.url));
  if (!target) throw new Error('page_target_missing');

  const expression = `(() => {
    const text = document.body ? document.body.innerText : '';
    const chinese = ${JSON.stringify(requiredChinese)};
    const forbiddenMixed = ${JSON.stringify(forbiddenMixed)};
    const protectedTitles = [...document.querySelectorAll('[data-testid="conversation-row-sidebar"] span.truncate')]
      .map((node) => node.innerText.trim())
      .filter(Boolean);
    return {
      url: location.href,
      title: document.title,
      marker: document.documentElement.getAttribute('data-antigravity-zhcn'),
      chineseMatches: chinese.filter((value) => text.includes(value)),
      forbiddenMixed: forbiddenMixed.filter((value) => text.includes(value)),
      protectedTitles,
      titlePollution: protectedTitles.filter((value) => /^(常规|软件设置|模型|开启|关闭|规则)\s/.test(value))
    };
  })()`;

  const message = await cdpCall(target.webSocketDebuggerUrl, 'Runtime.evaluate', {
    returnByValue: true,
    awaitPromise: true,
    expression
  });
  if (message.error) throw new Error(JSON.stringify(message.error));
  const value = message.result.result.value;
  if (value.marker !== '0.4.0') throw new Error('localization_marker_mismatch:' + value.marker);
  if (value.forbiddenMixed.length > 0) throw new Error('mixed_translation_detected:' + value.forbiddenMixed.join('|'));
  if (value.titlePollution.length > 0) throw new Error('conversation_title_pollution:' + value.titlePollution.join('|'));
  console.log(JSON.stringify(value, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
