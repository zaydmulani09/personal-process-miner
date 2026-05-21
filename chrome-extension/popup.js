'use strict';

const PPM_URL = 'http://localhost:7834/dom-events';

const toggleBtn = document.getElementById('toggleBtn');
const sendBtn = document.getElementById('sendBtn');
const counterEl = document.getElementById('counter');
const statusEl = document.getElementById('status');

function updateCounter() {
  chrome.runtime.sendMessage({ type: 'GET_COUNT' }, function (res) {
    if (res) counterEl.textContent = (res.count || 0) + ' events captured';
  });
}

function updateToggleUI(recording) {
  if (recording) {
    toggleBtn.textContent = '⏹ Stop Recording';
    toggleBtn.style.background = '#ef4444';
  } else {
    toggleBtn.textContent = '⏺ Start Recording';
    toggleBtn.style.background = '#3b82f6';
  }
}

chrome.storage.local.get(['recording'], function (res) {
  updateToggleUI(!!res.recording);
  updateCounter();
});

setInterval(updateCounter, 1500);

toggleBtn.addEventListener('click', function () {
  chrome.storage.local.get(['recording'], function (res) {
    const next = !res.recording;
    chrome.storage.local.set({ recording: next }, function () {
      updateToggleUI(next);
      if (!next) updateCounter();
    });
  });
});

sendBtn.addEventListener('click', function () {
  sendBtn.disabled = true;
  statusEl.textContent = 'Sending…';
  chrome.runtime.sendMessage({ type: 'GET_EVENTS' }, function (res) {
    const events = (res && res.events) || [];
    if (events.length === 0) {
      statusEl.textContent = 'No events to send.';
      sendBtn.disabled = false;
      return;
    }
    fetch(PPM_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ events }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        statusEl.textContent = '✓ Sent ' + (data.count || events.length) + ' events to PPM';
        counterEl.textContent = '0 events captured';
        sendBtn.disabled = false;
      })
      .catch(function () {
        statusEl.textContent = '✗ Could not reach PPM sidecar (port 7834)';
        sendBtn.disabled = false;
      });
  });
});
