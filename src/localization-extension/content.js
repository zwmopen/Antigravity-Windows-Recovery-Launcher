(function () {
  'use strict';

  // ── 永久隐藏右上角"安装 IDE"/"打开 IDE"/骨架加载按钮 ──────────────────
  // 必须在 guard 之前执行，确保每次汉化加载器重注入时都能保证样式存在
  (function injectHideIdeStyle() {
    var style = document.getElementById('__agy_hide_ide_btn__');
    if (!style) {
      style = document.createElement('style');
      style.id = '__agy_hide_ide_btn__';
      style.textContent = [
        'button[data-testid="install-editor"]',
        'button[data-testid^="open-editor"]',
        'button[data-testid="editor-loading"]',
        'a[data-testid="install-editor"]',
        'a[data-testid^="open-editor"]'
      ].join(',\n') + ' { display: none !important; }';
      (document.head || document.documentElement).appendChild(style);
    }
  })();
  // ─────────────────────────────────────────────────────────────────────────

  // Command names are display labels; never change slash-command values or drafts.
  // This small observer also bridges already-open pages using the older text runtime.
  (function installCommandLabels() {
    if (globalThis.__AntigravityZhCommandLabels) {
      globalThis.__AntigravityZhCommandLabels.scan(document.body);
      return;
    }
    var labels = Object.freeze({
      'btw': 'btw（顺便问）',
      'goal': 'goal（目标）',
      'compact': 'compact（压缩对话）',
      'schedule': 'schedule（定时任务）',
      'browser': 'browser（浏览器）',
      '浏览器': 'browser（浏览器）',
      'plan': 'plan（规划）',
      '套餐计划': 'plan（规划）',
      '规划': 'plan（规划）',
      'grill-me': 'grill-me（深入访谈）',
      'teamwork': 'teamwork（团队协作）'
    });
    var selector = '[data-testid="menu-option-label"]';
    function translateLabel(label) {
      if (!label || !label.closest('[role="option"]') ||
          label.closest('[contenteditable="true"], [data-message-author-role], [data-testid*="message" i], [class*="markdown" i], pre, code, textarea')) return;
      var walker = document.createTreeWalker(label, NodeFilter.SHOW_TEXT);
      var node;
      while ((node = walker.nextNode())) {
        var value = node.nodeValue;
        var key = value.trim().toLowerCase();
        if (!Object.prototype.hasOwnProperty.call(labels, key)) continue;
        node.nodeValue = value.replace(value.trim(), labels[key]);
      }
    }
    function scan(root) {
      if (!root) return;
      var element = root.nodeType === 1 ? root : root.parentElement;
      if (!element) return;
      var label = element.closest(selector);
      if (label) translateLabel(label);
      if (root.querySelectorAll) {
        Array.prototype.forEach.call(root.querySelectorAll(selector), translateLabel);
      }
    }
    function handleRecords(records) {
      records.forEach(function (record) {
        if (record.type === 'characterData') scan(record.target);
        else Array.prototype.forEach.call(record.addedNodes || [], scan);
      });
    }
    // Fresh documents share the general observer below. Only legacy live pages
    // need this narrow bridge, because their observer callback cannot be replaced.
    if (globalThis.__AntigravityZhContentInstalled) {
      var observer = new MutationObserver(handleRecords);
      observer.observe(document.documentElement, {subtree: true, childList: true, characterData: true});
    }
    globalThis.__AntigravityZhCommandLabels = {scan: scan, handleRecords: handleRecords};
    scan(document.body);
  }());

  // The CDP loader and the Chromium fallback can both reach the same
  // document during an upgrade.  Installing a second observer would make
  // every React update traverse the page more than once.
  var core = globalThis.AntigravityZhCore;
  if (!core) return;
  var DEBOUNCE_MS = 80;
  var MAX_WAIT_MS = 300;
  var pendingNodes = new Set();
  var debounceTimer = 0;
  var firstPendingAt = 0;
  var applying = false;
  var lastTextValues = new WeakMap();
  var lastAttributeValues = new WeakMap();

  // Live upgrades reuse the observer and refresh the UI scope predicate.
  globalThis.__AntigravityZhUiScope = isUiTextElement;
  globalThis.__AntigravityAutoDismissNotice = function () {
    return autoDismissSecurityNotice(document);
  };
  if (globalThis.__AntigravityZhContentInstalled) {
    if (typeof globalThis.__AntigravityZhForceTranslate === 'function') {
      globalThis.__AntigravityZhForceTranslate();
    }
    translateSubtree(document.body || document.documentElement);
    autoDismissSecurityNotice(document);
    document.documentElement.setAttribute('data-antigravity-zhcn', core.VERSION);
    return;
  }
  globalThis.__AntigravityZhContentInstalled = true;

  function closest(element, selector) {
    return element && element.closest ? element.closest(selector) : null;
  }

  function isConversationTitle(element) {
    if (!element || element.nodeType !== 1) return false;
    return !!closest(element, '[data-testid="conversation-row-sidebar"]') &&
      !!closest(element, 'a[href^="/c/"], a[href*="/c/"]');
  }

  function isProtectedTextElement(element) {
    if (!element || element.nodeType !== 1) return true;

    var tagName = element.tagName.toUpperCase();
    if (tagName === 'SCRIPT' || tagName === 'STYLE' || tagName === 'NOSCRIPT' ||
        tagName === 'TEMPLATE' || tagName === 'TEXTAREA' || tagName === 'INPUT' ||
        tagName === 'PRE' || tagName === 'CODE') {
      return true;
    }
    if (element.isContentEditable) return true;

    // The visible title is a sibling of the absolute conversation link in
    // Antigravity's virtualized rows, so protect the whole row's text. The
    // timestamp is handled separately in shouldTranslateTextNode.
    if (closest(element, '[data-testid="conversation-row-sidebar"]')) return true;

    return !!closest(element,
      '[contenteditable="true"], [data-message-author-role], [data-testid*="message" i], ' +
      '[class*="markdown" i], [class*="monaco" i], [class*="editor" i], ' +
      '[class*="message-content" i], [class*="agent-response" i]'
    );
  }

  function isProtectedAttributeElement(element) {
    if (!element || element.nodeType !== 1) return true;
    var tagName = element.tagName.toUpperCase();
    if (tagName === 'SCRIPT' || tagName === 'STYLE' || tagName === 'NOSCRIPT' ||
        tagName === 'TEMPLATE' || tagName === 'PRE' || tagName === 'CODE') {
      return true;
    }
    if (isConversationTitle(element)) return true;
    return !!closest(element,
      '[data-message-author-role], [data-testid*="message" i], ' +
      '[class*="markdown" i], [class*="monaco" i], [class*="editor" i], ' +
      '[class*="message-content" i], [class*="agent-response" i]'
    );
  }

  function isUiTextElement(element) {
    if (!element || isProtectedTextElement(element)) return false;
    return !!closest(element,
      '[class*="overlay" i], [class*="popover" i], [class*="dropdown" i], [data-radix-popper-content-wrapper], [data-radix-menu-content], ' +
      'button, a[href], [role="button"], [role="menuitem"], [role="menuitemcheckbox"], ' +
      '[role="menuitemradio"], [role="menu"], [role="option"], [role="tab"], ' +
      'label, h1, h2, h3, h4, h5, h6, [role="heading"], [data-testid^="settings-nav-item-"], ' +
      '[role="dialog"], [role="alertdialog"], [role="tooltip"], [aria-modal="true"], ' +
      '[data-testid*="onboarding" i], [data-testid*="welcome" i], [class*="max-w-xl" i], [class*="max-w-[560px]" i]'
    );
  }

  function isSettingsSurface(element) {
    if (!element || isProtectedTextElement(element)) return false;
    if (closest(element, '[data-testid^="settings-nav-item-"]')) return true;
    return typeof location !== 'undefined' && /(?:^|[?&])settingsOpen=true(?:&|$)/i.test(location.search || '');
  }

  function isCustomizationsSurface(element) {
    if (!element || isProtectedTextElement(element)) return false;
    if (closest(element, '[data-testid*="customiz" i], [class*="customiz" i]')) return true;
    return typeof location !== 'undefined' && (
      (typeof location.pathname === 'string' && location.pathname.startsWith('/customizations')) ||
      /(?:^|[?&])customizationsOpen=true(?:&|$)/i.test(location.search || '')
    );
  }

  function isInstantUiNode(node) {
    if (!node) return false;
    var el = node.nodeType === 1 ? node : node.parentElement;
    if (!el || isProtectedTextElement(el)) return false;
    if (closest(el, '[role="dialog"], [role="menu"], [aria-modal="true"], [data-testid*="settings" i], [class*="modal" i], [class*="settings" i], [data-testid^="settings-nav-item-"], [data-testid*="onboarding" i], [data-testid*="welcome" i], [class*="max-w-xl" i]')) {
      return true;
    }
    return isSettingsSurface(el) || isCustomizationsSurface(el) || isUiTextElement(el);
  }

  function isToolOrStatusPillText(text) {
    if (!text || typeof text !== 'string') return false;
    var trimmed = text.trim();
    if (/^(?:Sends after agent finishes working|Error Verification Required|Verification Required|Drag to select a region to comment|Untitled Conversation|CLI Project|Working|Exploring|Analyzed|Preview|Raw)$/i.test(trimmed)) return true;
    if (/^\d+\s+tasks?\s+running$/i.test(trimmed)) return true;
    if (/^\d+\s+files?\s+changed(?:\s*[+-]\d+.*)?$/i.test(trimmed)) return true;
    if (/^(?:Running|Ran|Explored|正在运行|已运行|已探索)?\s*\d+\s*(?:search(?:es)?|commands?|tasks?|files?|条命令|次搜索|个任务|个文件)(?:,\s*\d+\s*(?:search(?:es)?|commands?|tasks?|files?|条命令|次搜索|个任务|个文件))*$/i.test(trimmed)) return true;
    return false;
  }

  function shouldTranslateTextNode(node) {
    if (!node || node.nodeType !== Node.TEXT_NODE || !node.parentElement) return false;
    var raw = node.nodeValue;
    if (!raw || raw.length > 5000) return false;
    var val = raw.trim();
    if (val === 'Queued Messages' || val === 'Queued Message' || val === 'Queued') return true;
    if (isToolOrStatusPillText(val)) return true;
    if (!isProtectedTextElement(node.parentElement)) return true;
    var row = closest(node.parentElement, '[data-testid="conversation-row-sidebar"]');
    return !!row && /^\s*\d+\s*(?:[smhd]|seconds?|minutes?|hours?|days?)\s*$/i.test(val);
  }

  function translateTextNode(node) {
    if (!shouldTranslateTextNode(node)) return 0;
    var oldValue = node.nodeValue;
    var rowTimestamp = closest(node.parentElement, '[data-testid="conversation-row-sidebar"]');
    var isPill = isToolOrStatusPillText(oldValue);
    var useUiTranslation = (globalThis.__AntigravityZhUiScope || isUiTextElement)(node.parentElement) ||
      isSettingsSurface(node.parentElement) || isCustomizationsSurface(node.parentElement) || rowTimestamp || isPill;
    var previous = lastTextValues.get(node);
    if (previous && previous.value === oldValue && previous.useUi === !!useUiTranslation) return 0;
    var newValue = useUiTranslation
      ? core.translateUiText(oldValue)
      : core.translateText(oldValue);
    lastTextValues.set(node, { value: newValue, useUi: !!useUiTranslation });
    if (newValue === oldValue) return 0;
    node.nodeValue = newValue;
    return 1;
  }

  function translateElementAttributes(element) {
    if (isProtectedAttributeElement(element)) return 0;
    var changed = 0;
    var previous = lastAttributeValues.get(element) || Object.create(null);
    core.ATTRIBUTES.forEach(function (attribute) {
      if (!element.hasAttribute(attribute)) {
        delete previous[attribute];
        return;
      }
      var oldValue = element.getAttribute(attribute);
      if (previous[attribute] === oldValue) return;
      var newValue = core.translateUiText(oldValue);
      previous[attribute] = newValue;
      if (newValue !== oldValue) {
        element.setAttribute(attribute, newValue);
        changed += 1;
      }
    });
    lastAttributeValues.set(element, previous);
    return changed;
  }

  function translateSubtree(root) {
    if (!root) return 0;
    if (root.nodeType === Node.TEXT_NODE) return translateTextNode(root);
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE &&
        root.nodeType !== Node.DOCUMENT_FRAGMENT_NODE) return 0;

    var changed = 0;
    if (root.nodeType === Node.ELEMENT_NODE) {
      changed += translateElementAttributes(root);
    }

    // Walk elements and text in one pass.  The former implementation walked
    // all text and then queried all descendants again for attributes, which
    // became very expensive when Settings replaced a large React subtree.
    var walker = document.createTreeWalker(
      root,
      NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT
    );
    var current;
    while ((current = walker.nextNode())) {
      if (current.nodeType === Node.TEXT_NODE) {
        changed += translateTextNode(current);
      } else {
        changed += translateElementAttributes(current);
      }
    }
    return changed;
  }

  globalThis.__AntigravityZhForceTranslate = function () {
    core = globalThis.AntigravityZhCore || core;
    lastTextValues = new WeakMap();
    lastAttributeValues = new WeakMap();
    if (document.body) translateSubtree(document.body);
    autoDismissSecurityNotice(document);
  };

  function contains(ancestor, node) {
    if (!ancestor || !node) return false;
    if (ancestor === node) return true;
    return typeof ancestor.contains === 'function' && ancestor.contains(node);
  }

  function hasPendingAncestor(node) {
    var current = node && node.parentNode;
    while (current) {
      if (pendingNodes.has(current)) return true;
      current = current.parentNode;
    }
    return false;
  }

  function requestFlush(node) {
    if (node && !hasPendingAncestor(node)) {
      pendingNodes.forEach(function (pending) {
        if (contains(node, pending)) pendingNodes.delete(pending);
      });
      pendingNodes.add(node);
    }
    if (!firstPendingAt) firstPendingAt = Date.now();
    if (debounceTimer) clearTimeout(debounceTimer);
    var elapsed = Date.now() - firstPendingAt;
    var delay = Math.max(0, Math.min(DEBOUNCE_MS, MAX_WAIT_MS - elapsed));
    debounceTimer = setTimeout(flush, delay);
  }

  function flush() {
    debounceTimer = 0;
    if (applying || pendingNodes.size === 0) {
      if (pendingNodes.size === 0) firstPendingAt = 0;
      return;
    }

    var nodes = Array.from(pendingNodes);
    pendingNodes.clear();
    firstPendingAt = 0;
    applying = true;
    try {
      nodes.forEach(translateSubtree);
    } finally {
      applying = false;
    }
  }

  function observeDocument() {
    if (!document.documentElement) return;
    if (document.documentElement.lang !== 'zh-CN') {
      document.documentElement.lang = 'zh-CN';
    }

    var observer = new MutationObserver(function (records) {
      if (applying) return;
      globalThis.__AntigravityZhCommandLabels.handleRecords(records);
      autoDismissSecurityNotice(document);
      records.forEach(function (record) {
        if (record.type === 'attributes' || record.type === 'characterData') {
          if (isInstantUiNode(record.target)) {
            applying = true;
            try { translateSubtree(record.target); }
            finally { applying = false; }
          } else {
            requestFlush(record.target);
          }
          return;
        }
        for (var i = 0; i < record.addedNodes.length; i += 1) {
          var added = record.addedNodes[i];
          if (isInstantUiNode(added)) {
            applying = true;
            try { translateSubtree(added); }
            finally { applying = false; }
          } else {
            requestFlush(added);
          }
        }
      });
    });

    observer.observe(document.documentElement, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: core.ATTRIBUTES
    });

    applying = true;
    try {
      translateSubtree(document.body || document.documentElement);
    } finally {
      applying = false;
    }
    document.documentElement.setAttribute('data-antigravity-zhcn', core.VERSION);

    // ── 自动穿透免责声明与安全须知弹窗 (无需人工点击确认) ────────────────────────
    autoDismissSecurityNotice(document);
    var dismissAttempts = 0;
    var dismissPoll = function () {
      if (autoDismissSecurityNotice(document)) return;
      dismissAttempts++;
      if (dismissAttempts < 25 && typeof setTimeout === 'function') {
        setTimeout(dismissPoll, 200);
      }
    };
    if (typeof setTimeout === 'function') {
      setTimeout(dismissPoll, 200);
    }
    // ──────────────────────────────────────────────────────────────────────────
  }

  // ── 自动穿透免责声明与安全须知弹窗 (Auto-Dismiss Security Notice Modal) ────
  function autoDismissSecurityNotice(doc) {
    if (!doc || typeof doc.querySelectorAll !== 'function') return false;
    try {
      var dialogs = Array.from(doc.querySelectorAll(
        '[role="dialog"], [role="alertdialog"], [aria-modal="true"], ' +
        '[data-testid*="onboarding" i], [data-testid*="welcome" i], [class*="modal" i], ' +
        '[class*="max-w-xl" i], [class*="max-w-[560px]" i]'
      ));
      if (!dialogs.length) return false;

      for (var d = 0; d < dialogs.length; d++) {
        var modal = dialogs[d];
        var text = (modal.innerText || modal.textContent || '').toLowerCase();

        var isNotice = text.includes('security notice') ||
          text.includes('安全须知') ||
          text.includes('terms of service') ||
          text.includes('服务条款') ||
          text.includes('getting started') ||
          text.includes('开始使用') ||
          text.includes('data use') ||
          text.includes('数据使用') ||
          (modal.dataset && (modal.dataset.testid || '').toLowerCase().includes('onboarding')) ||
          (modal.dataset && (modal.dataset.testid || '').toLowerCase().includes('welcome'));

        if (!isNotice) continue;

        if (typeof modal.querySelectorAll === 'function') {
          var checkboxes = modal.querySelectorAll('input[type="checkbox"]');
          Array.prototype.forEach.call(checkboxes, function (cb) {
            if (!cb.checked && cb.offsetParent !== null && !cb.disabled) {
              try {
                cb.click();
                cb.checked = true;
                if (typeof Event === 'function') {
                  cb.dispatchEvent(new Event('change', { bubbles: true }));
                }
              } catch (e) {}
            }
          });

          var buttons = Array.from(modal.querySelectorAll('button, [role="button"], a[role="button"]'));
          for (var b = 0; b < buttons.length; b++) {
            var btn = buttons[b];
            var btnText = (btn.innerText || btn.textContent || '').trim().toLowerCase();

            if (
              btnText === 'accept and continue' ||
              btnText === '接受并继续' ||
              btnText === '确认并继续' ||
              btnText.indexOf('accept and continue') !== -1 ||
              btnText.indexOf('接受并继续') !== -1 ||
              btnText.indexOf('确认并继续') !== -1 ||
              btnText === 'confirm and continue' ||
              btnText === 'agree and continue' ||
              btnText === '同意并继续' ||
              btnText === 'accept all' ||
              btnText === '接受全部' ||
              btnText === 'get started' ||
              btnText === '开始使用' ||
              btnText === 'got it' ||
              btnText === '知道了' ||
              btnText === 'accept' ||
              btnText === '接受' ||
              btnText === 'continue' ||
              btnText === '继续' ||
              btnText === '确认' ||
              btnText === '确定'
            ) {
              if (btn.offsetParent !== null && !btn.disabled && !btn.getAttribute('aria-disabled')) {
                try {
                  btn.focus();
                  if (typeof MouseEvent === 'function') {
                    btn.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                    btn.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                  }
                  btn.click();
                  return true;
                } catch (e) {}
              }
            }
          }
        }
      }
    } catch (e) {}
    return false;
  }

  globalThis.__AntigravityAutoDismissNotice = function () {
    return autoDismissSecurityNotice(document);
  };

  globalThis.__AntigravityAutoResume = async function (maxCount, resumeText) {
    maxCount = typeof maxCount === 'number' ? maxCount : 3;
    resumeText = typeof resumeText === 'string' ? resumeText : '1';

    var rows = Array.from(document.querySelectorAll('[data-testid="conversation-row-sidebar"]'));
    if (rows.length === 0) {
      return { success: false, reason: 'no_conversations_found' };
    }

    var targetCount = Math.min(maxCount, rows.length);
    var results = [];

    for (var i = 0; i < targetCount; i++) {
      var row = rows[i];
      var a = row.querySelector('a');
      var href = a ? a.getAttribute('href') : null;
      if (!a) {
        results.push({ index: i + 1, success: false, reason: 'no_anchor' });
        continue;
      }

      a.click();
      await new Promise(function (res) { setTimeout(res, 800); });

      var stopButton = document.querySelector('button[aria-label*="Stop"], button[data-testid*="stop"]');
      if (stopButton) {
        results.push({ index: i + 1, href: href, skipped: true, reason: 'task_currently_running' });
        continue;
      }

      var editable = document.querySelector('[data-lexical-editor="true"]');
      if (!editable) {
        results.push({ index: i + 1, href: href, success: false, reason: 'editor_not_found' });
        continue;
      }

      var currentText = (editable.textContent || '').trim();
      if (currentText.length > 0 && currentText !== resumeText) {
        results.push({ index: i + 1, href: href, skipped: true, reason: 'draft_exists' });
        continue;
      }

      editable.focus();
      document.execCommand('insertText', false, resumeText);
      await new Promise(function (res) { setTimeout(res, 200); });

      var sendBtn = document.querySelector('button[data-testid="send-button"]');
      if (sendBtn && !sendBtn.disabled) {
        sendBtn.click();
        results.push({ index: i + 1, href: href, success: true, text: resumeText });
      } else {
        results.push({ index: i + 1, href: href, success: false, reason: 'send_button_disabled' });
      }

      await new Promise(function (res) { setTimeout(res, 600); });
    }

    if (rows.length > 0) {
      var firstLink = rows[0].querySelector('a');
      if (firstLink) firstLink.click();
    }

    return {
      success: true,
      processed: results.length,
      results: results
    };
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', observeDocument, { once: true });
  } else {
    observeDocument();
  }
}());

