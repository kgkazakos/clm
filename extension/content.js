/**
 * CLM Session Logger — content script v5
 *
 * Uses global sessionStart timestamp received from background.js
 * so all events across the full multi-page session share an absolute
 * time reference, not a per-page-load relative one.
 */

let isRecording = false;
let sessionStartMs = null;   // absolute epoch ms from background service worker
let lastMouseX = null;
let lastMouseY = null;
let inputTimers = {};

function ts() {
  // Always relative to global session start, not page load
  return sessionStartMs ? Date.now() - sessionStartMs : 0;
}

function normX(x) { return Math.round((x / window.innerWidth)  * 100) / 100; }
function normY(y) { return Math.round((y / window.innerHeight) * 100) / 100; }

function elementId(el) {
  if (!el) return null;
  const cls = typeof el.className === 'string'
    ? (el.className.split(' ')[0] || null)
    : null;
  return el.id || el.name || el.getAttribute?.('data-testid') ||
    cls || el.tagName?.toLowerCase() || null;
}

function push(event) {
  if (!isRecording) return;
  chrome.runtime.sendMessage({ action: 'push_event', event }).catch(() => {});
}

// ─── Event listeners ──────────────────────────────────────────────────────────

document.addEventListener('click', e => {
  push({ timestamp_ms: ts(), event_type: 'click',
    element_id: elementId(e.target),
    x: normX(e.clientX), y: normY(e.clientY),
    value: null, screen_id: window.location.pathname,
    duration_ms: null, is_error: false,
    metadata: { tag: e.target?.tagName?.toLowerCase() } });
}, true);

let lastScroll = 0;
document.addEventListener('scroll', () => {
  const now = Date.now();
  if (now - lastScroll < 300) return;
  lastScroll = now;
  push({ timestamp_ms: ts(), event_type: 'scroll',
    element_id: null, x: null, y: null,
    value: String(Math.round(window.scrollY)),
    screen_id: window.location.pathname,
    duration_ms: null, is_error: false, metadata: {} });
}, true);

document.addEventListener('focusin', e => {
  if (!['INPUT','TEXTAREA','SELECT'].includes(e.target?.tagName)) return;
  inputTimers[elementId(e.target)] = Date.now();
}, true);

document.addEventListener('blur', e => {
  if (!['INPUT','TEXTAREA','SELECT'].includes(e.target?.tagName)) return;
  const id = elementId(e.target);
  const dwell = inputTimers[id] ? Date.now() - inputTimers[id] : null;
  delete inputTimers[id];
  push({ timestamp_ms: ts(), event_type: 'input',
    element_id: id, x: null, y: null,
    value: e.target.type === 'password' ? '[redacted]' : (e.target.value || null),
    screen_id: window.location.pathname,
    duration_ms: dwell, is_error: false,
    metadata: { input_type: e.target.type } });
}, true);

let mouseSampleTimer = null;
document.addEventListener('mousemove', e => {
  lastMouseX = e.clientX; lastMouseY = e.clientY;
  if (mouseSampleTimer) return;
  mouseSampleTimer = setTimeout(() => {
    push({ timestamp_ms: ts(), event_type: 'hover',
      element_id: elementId(document.elementFromPoint(lastMouseX, lastMouseY)),
      x: normX(lastMouseX), y: normY(lastMouseY),
      value: null, screen_id: window.location.pathname,
      duration_ms: null, is_error: false, metadata: {} });
    mouseSampleTimer = null;
  }, 500);
}, true);

// ─── Messages from background ─────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'start') {
    isRecording = true;
    // Use global session start from background — not Date.now()
    // This ensures all pages in a session share the same time reference
    sessionStartMs = msg.sessionStart || Date.now();
    sendResponse({ ok: true });
  }
  if (msg.action === 'stop') {
    isRecording = false;
    sendResponse({ ok: true });
  }
  return true;
});