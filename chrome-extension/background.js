'use strict';

const MAX_BUFFER = 500;
let _buffer = [];

chrome.runtime.onMessage.addListener(function (msg, sender, sendResponse) {
  if (msg.type === 'DOM_EVENT') {
    if (_buffer.length < MAX_BUFFER) _buffer.push(msg.event);
    return;
  }
  if (msg.type === 'GET_EVENTS') {
    const events = _buffer.slice();
    _buffer = [];
    sendResponse({ events });
    return true;
  }
  if (msg.type === 'GET_COUNT') {
    sendResponse({ count: _buffer.length });
    return true;
  }
  if (msg.type === 'CLEAR_EVENTS') {
    _buffer = [];
    sendResponse({ ok: true });
    return true;
  }
});
