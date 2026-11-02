'use strict';
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync('src/localization-extension/content.js', 'utf8');
const start = source.indexOf('  (function installCommandLabels()');
const end = source.indexOf('  // The CDP loader', start);
const runtime = source.slice(start, end);
let callbacks = [], observed = 0;
const nodes = ['btw','goal','compact','schedule','browser','plan','grill-me','teamwork','浏览器','套餐计划','unknown-plugin'].map(text => {
  const label = {
    nodeType:1,
    closest(selector) {return selector === '[role="option"]' || selector === '[data-testid="menu-option-label"]' ? this : null;},
    querySelectorAll(){return [];}
  };
  const node = {nodeType:3,nodeValue:text,parentElement:label};
  label.textNodes=[node];
  return {label,node,identifier:text};
});
const body={nodeType:1,closest(){return null;},querySelectorAll(){return nodes.map(x=>x.label);}};
const context={__AntigravityZhContentInstalled:true,document:{body,documentElement:{},createTreeWalker(label){let i=0;return {nextNode(){return (label.textNodes||[])[i++]||null;}};}},NodeFilter:{SHOW_TEXT:4},MutationObserver:class{constructor(cb){callbacks.push(cb);}observe(){observed++;}}};
context.globalThis=context;
vm.runInNewContext(runtime,context);
assert.deepStrictEqual(nodes.map(x=>x.node.nodeValue),['btw（顺便问）','goal（目标）','compact（压缩对话）','schedule（定时任务）','browser（浏览器）','plan（规划）','grill-me（深入访谈）','teamwork（团队协作）','browser（浏览器）','plan（规划）','unknown-plugin']);
assert.strictEqual(nodes[1].identifier,'goal');
vm.runInNewContext(runtime,context);
assert.strictEqual(observed,1);
assert.strictEqual(nodes[1].node.nodeValue,'goal（目标）');
// React can reuse a menu row and replace its text after the menu is opened.
nodes[1].node.nodeValue='goal';
callbacks[0]([{type:'characterData',target:nodes[1].node}]);
assert.strictEqual(nodes[1].node.nodeValue,'goal（目标）');
// A similarly named label in a message/code/draft is protected.
const protectedNode=nodes[0];
protectedNode.node.nodeValue='btw';
protectedNode.label.closest=selector=>selector.includes('[contenteditable')||selector==='[role="option"]'||selector==='[data-testid="menu-option-label"]'?protectedNode.label:null;
callbacks[0]([{type:'characterData',target:protectedNode.node}]);
assert.strictEqual(protectedNode.node.nodeValue,'btw');
console.log('localization-command-labels.test.js: PASS (bilingual labels, dynamic updates, idempotence, command identifiers and protected content)');
