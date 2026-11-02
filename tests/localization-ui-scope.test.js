"use strict";
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.join(__dirname, '..', 'src', 'localization-extension');
function element(tag, flags = {}) {
  return {
    nodeType: 1, tagName: tag, isContentEditable: !!flags.editable,
    closest(selector) {
      if (flags.dialog && selector.includes('[role="dialog"]')) return this;
      if (flags.message && selector.includes('[data-message-author-role]')) return this;
      if (flags.title && selector.includes('conversation-row-sidebar')) return this;
      if (tag === 'BUTTON' && selector.includes('button,')) return this;
      if (tag === 'A' && selector.includes('a[href]')) return this;
      if (flags.option && selector.includes('[role="option"]')) return this;
      return null;
    },
    hasAttribute() { return false; }, setAttribute() {}, getAttribute() { return null; }
  };
}
const fixtures = [
  ['Tool Permissions', element('DIV', {dialog:true})],
  ['Modify permissions for file, terminal, and MCP tools.', element('SPAN', {dialog:true})],
  ['Tool Permissions', element('SPAN', {message:true,dialog:true})],
  ['Tool Permissions', element('PRE', {dialog:true})],
  ['Tool Permissions', element('DIV', {editable:true,dialog:true})],
  ['agy-customizations', element('SPAN')],
  ['Automations', element('BUTTON')],
  ['Customizations', element('A')],
  ['Ask a quick question without interrupting the main conversation.', element('SPAN', {option:true})],
  ['goal', element('SPAN', {option:true})],
  ['Customizations', element('SPAN', {message:true})],
  ['Automations', element('SPAN', {title:true})],
  ['Run until the specified goal is completely finished.', element('PRE')],
  ['Automations', element('DIV', {editable:true})]
].map(([text, parent]) => ({nodeType:3,nodeValue:text,parentElement:parent}));
const document = {
  readyState:'complete', body:element('BODY'), documentElement:element('HTML'),
  head:{appendChild(){}}, getElementById(){return null;}, createElement:element,
  createTreeWalker(){let index=0;return {nextNode(){return fixtures[index++] || null;}};}
};
let observerCount = 0;
const context = {document,console,Node:{TEXT_NODE:3,ELEMENT_NODE:1,DOCUMENT_NODE:9,DOCUMENT_FRAGMENT_NODE:11},NodeFilter:{SHOW_ELEMENT:1,SHOW_TEXT:4},MutationObserver:class{constructor(){observerCount++;}observe(){}},setTimeout,clearTimeout,location:{search:''}};
context.globalThis=context;
vm.runInNewContext(fs.readFileSync(path.join(root,'translation-core.js'),'utf8'),context);
vm.runInNewContext(fs.readFileSync(path.join(root,'content.js'),'utf8'),context);
assert.deepStrictEqual(fixtures.map(n=>n.nodeValue),[
  '工具权限','修改文件、终端与 MCP 工具的访问权限。','Tool Permissions','Tool Permissions','Tool Permissions',
  'agy-customizations','自动化任务','自定义扩展','提出一个简短问题，不中断当前主对话。','goal',
  'Customizations','Automations','Run until the specified goal is completely finished.','Automations'
]);
console.log('localization-ui-scope.test.js: PASS (sidebar/menu translated; aliases/messages/titles/code/drafts preserved)');

// Reinjecting an upgrade must update labels and marker without a second observer.
fixtures[0].nodeValue = 'MCP Server Status';
vm.runInNewContext(fs.readFileSync(path.join(root,'content.js'),'utf8'),context);
assert.strictEqual(fixtures[0].nodeValue, 'MCP 服务状态');
assert.strictEqual(observerCount, 1);
