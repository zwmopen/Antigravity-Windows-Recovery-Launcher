(function () {
  'use strict';

  // The CDP loader and the Chromium fallback can both reach the same
  // document during an upgrade.  Installing a second observer would make
  // every React update traverse the page more than once.
  var core = globalThis.AntigravityZhCore;
  if (!core) return;
  if (globalThis.__AntigravityZhContentInstalled) return;
  globalThis.__AntigravityZhContentInstalled = true;

  var DEBOUNCE_MS = 80;
  var MAX_WAIT_MS = 300;
  var pendingNodes = new Set();
  var debounceTimer = 0;
  var firstPendingAt = 0;
  var applying = false;
  var lastTextValues = new WeakMap();
  var lastAttributeValues = new WeakMap();

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
      'button, [role="button"], label, h1, h2, h3, h4, h5, h6, ' +
      '[role="heading"], [data-testid^="settings-nav-item-"]'
    );
  }

  function isSettingsSurface(element) {
    if (!element || isProtectedTextElement(element)) return false;
    if (closest(element, '[data-testid^="settings-nav-item-"]')) return true;
    return typeof location !== 'undefined' && /(?:^|[?&])settingsOpen=true(?:&|$)/i.test(location.search || '');
  }

  function shouldTranslateTextNode(node) {
    if (!node || node.nodeType !== Node.TEXT_NODE || !node.parentElement) return false;
    if (!isProtectedTextElement(node.parentElement)) return true;
    var row = closest(node.parentElement, '[data-testid="conversation-row-sidebar"]');
    return !!row && /^\s*\d+\s*(?:[smhd]|seconds?|minutes?|hours?|days?)\s*$/i.test(node.nodeValue || '');
  }

  function translateTextNode(node) {
    if (!shouldTranslateTextNode(node)) return 0;
    var oldValue = node.nodeValue;
    var rowTimestamp = closest(node.parentElement, '[data-testid="conversation-row-sidebar"]');
    var useUiTranslation = isUiTextElement(node.parentElement) ||
      isSettingsSurface(node.parentElement) || rowTimestamp;
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
      records.forEach(function (record) {
        if (record.type === 'attributes' || record.type === 'characterData') {
          requestFlush(record.target);
          return;
        }
        for (var i = 0; i < record.addedNodes.length; i += 1) {
          requestFlush(record.addedNodes[i]);
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

    requestFlush(document.body || document.documentElement);
    document.documentElement.setAttribute('data-antigravity-zhcn', core.VERSION);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', observeDocument, { once: true });
  } else {
    observeDocument();
  }
}());
