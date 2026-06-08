/**
 * CLM Session Logger — content script v4
 * Fixes SVGAnimatedString className bug.
 * Pushes all events to background service worker.
 */

let isRecording = false;
let lastMouseX = null;
let lastMouseY = null;
let inputTimers = {};
let sessionStartMs = null;

function ts() { return sessionStartMs ? Date.now() - sessionStartMs : 0; }
function normX(x) { return Math.round((x / window.innerWidth) * 100) / 100; }
function normY(y) { return Math.round((y / window.innerHeight) * 100) / 100; }

function elementId(el) {
  if (!el) return null;
  // className can be SVGAnimatedString on SVG elements — guard with typeof check
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

// ─── Click ────────────────────────────────────────────────────────────────────

document.addEventListener('click', e => {
  push({ timestamp_ms: ts(), event_type: 'click',
    element_id: elementId(e.target),
    x: normX(e.clientX), y: normY(e.clientY),
    value: null, screen_id: window.location.pathname,
    duration_ms: null, is_error: false,
    metadata: { tag: e.target?.tagName?.toLowerCase() } });
}, true);

// ─── Scroll ───────────────────────────────────────────────────────────────────

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

// ─── Input ────────────────────────────────────────────────────────────────────

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

// ─── Mouse trajectory (sampled every 500ms) ───────────────────────────────────

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

// ─── SPA navigation ───────────────────────────────────────────────────────────

let lastPath = window.location.pathname;
new MutationObserver(() => {
  if (window.location.pathname !== lastPath) {
    push({ timestamp_ms: ts(), event_type: 'navigation',
      element_id: null, x: null, y: null, value: null,
      screen_id: window.location.pathname, duration_ms: null, is_error: false,
      metadata: { from: lastPath, to: window.location.pathname } });
    lastPath = window.location.pathname;
  }
}).observe(document, { subtree: true, childList: true });

// ─── Messages from background ─────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'start') {
    isRecording = true;
    sessionStartMs = Date.now();
    sendResponse({ ok: true });
  }
  if (msg.action === 'stop') {
    isRecording = false;
    sendResponse({ ok: true });
  }
  return true;
});
