(function () {
  'use strict';

  function getCssSelector(el) {
    if (!el || el === document.body) return 'body';
    if (el.id) return '#' + el.id;
    const classes = [...el.classList].slice(0, 2);
    if (classes.length) return el.tagName.toLowerCase() + '.' + classes.join('.');
    // nth-child path, max 4 levels
    const path = [];
    let cur = el;
    let depth = 0;
    while (cur && cur !== document.body && depth < 4) {
      let sel = cur.tagName.toLowerCase();
      const parent = cur.parentElement;
      if (parent) {
        const siblings = [...parent.children].filter(c => c.tagName === cur.tagName);
        if (siblings.length > 1) sel += ':nth-child(' + (siblings.indexOf(cur) + 1) + ')';
      }
      path.unshift(sel);
      cur = parent;
      depth++;
    }
    return path.join(' > ');
  }

  function captureEvent(e) {
    chrome.storage.local.get(['recording'], function (res) {
      if (!res.recording) return;
      const el = e.target;
      const evt = {
        type: e.type,
        url: location.href,
        timestamp: Date.now(),
        selector: getCssSelector(el),
        element_tag: (el.tagName || '').toLowerCase(),
        element_id: el.id || null,
        element_class: el.className || null,
        element_text: (el.innerText || el.textContent || '').trim().slice(0, 80),
        value: el.value !== undefined ? el.value : null,
        key: e.key || null,
        x: e.clientX || null,
        y: e.clientY || null,
      };
      chrome.runtime.sendMessage({ type: 'DOM_EVENT', event: evt });
    });
  }

  ['click', 'input', 'submit', 'keydown'].forEach(function (evtType) {
    document.addEventListener(evtType, captureEvent, true);
  });
})();
