'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const assistant = fs.readFileSync(path.join(root, 'src', 'Antigravity-Chinese-Assistant.cs'), 'utf8');
const build = fs.readFileSync(path.join(root, 'build-shareable.ps1'), 'utf8');
const guide = fs.readFileSync(path.join(root, 'docs', 'SHAREABLE-README.txt'), 'utf8');

assert.ok(assistant.includes('启动中文版'));
assert.ok(assistant.includes('恢复英文原版'));
assert.ok(assistant.includes('AssemblyFileVersion("0.4.0.0")'));
assert.ok(assistant.includes('CreateDesktopShortcut'));
assert.ok(assistant.includes('--remote-debugging-port=0'));
assert.ok(assistant.includes('Antigravity-CdpLocalizationLoader.exe'));
assert.ok(assistant.includes('localization-extension'));
assert.ok(!assistant.includes('17897'));
assert.ok(!assistant.includes('Clash'));
assert.ok(!assistant.includes('AccountWatcher'));
assert.ok(!assistant.includes('HTTP_PROXY'));
assert.ok(build.includes('Compress-Archive'));
assert.ok(build.includes('文件校验.json'));
assert.ok(guide.includes('不修改系统或 Clash 代理'));
assert.ok(guide.includes('恢复英文原版'));

console.log('shareable-assistant.test.js: PASS');
