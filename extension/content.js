/**
 * CLM Session Logger — content script v5.1
 *
 * PII handling:
 * Input field VALUES are never logged. The content script captures
 * only element_id (which field was interacted with) and duration_ms
 * (how long the user spent in the field). These two signals are
 * sufficient for the dwell_time and input_retry calculators.
 *
 * Raw input text — including email addresses, names, search terms,
 * and any other typed content — is discarded at capture time and
 * never written to the session JSON or sent to any API.
 *
 * Scroll values (scroll delta in pixels) are retained as they contain
 * no PII and are required for the scroll_behaviour signal calculator.
 *
 * Researchers are responsible for obtaining appropriate consent from
 * participants before deploying the CLM Logger, consistent with their
 * institutional IRB requirements and applicable data protection law.
 */

let isRecording = false;
let sessionStartMs = null;
let lastMouseX = null;
let lastMouseY = null;
let inputTimers = {};

function ts() {
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

// ─── Click ────────────────────────────────────────────────────────────────────

document.addEventListener('click', e => {
  push({
    timestamp_ms: ts(), event_type: 'click',
    element_id: elementId(e.target),
    x: normX(e.clientX), y: normY(e.clientY),
    value: null,
    screen_id: window.location.pathname,
    duration_ms: null, is_error: false,
    metadata: { tag: e.target?.tagName?.toLowerCase() },
  });
}, true);

// ─── Scroll (delta in px — no PII) ───────────────────────────────────────────

let lastScroll = 0;
document.addEventListener('scroll', () => {
  const now = Date.now();
  if (now - lastScroll < 300) return;
  lastScroll = now;
  push({
    timestamp_ms: ts(), event_type: 'scroll',
    element_id: null, x: null, y: null,
    value: String(Math.round(window.scrollY)),   // pixel offset — not PII
    screen_id: window.location.pathname,
    duration_ms: null, is_error: false, metadata: {},
  });
}, true);

// ─── Input (element_id and dwell only — value is never logged) ────────────────

document.addEventListener('focusin', e => {
  if (!['INPUT','TEXTAREA','SELECT'].includes(e.target?.tagName)) return;
  inputTimers[elementId(e.target)] = Date.now();
}, true);

document.addEventListener('blur', e => {
  if (!['INPUT','TEXTAREA','SELECT'].includes(e.target?.tagName)) return;
  const id = elementId(e.target);
  const dwell = inputTimers[id] ? Date.now() - inputTimers[id] : null;
  delete inputTimers[id];
  push({
    timestamp_ms: ts(), event_type: 'input',
    element_id: id,
    x: null, y: null,
    value: null,       // input text is intentionally not captured
    screen_id: window.location.pathname,
    duration_ms: dwell,
    is_error: false,
    metadata: { input_type: e.target.type },
  });
}, true);

// ─── Mouse trajectory (sampled every 500ms) ───────────────────────────────────

let mouseSampleTimer = null;
document.addEventListener('mousemove', e => {
  lastMouseX = e.clientX; lastMouseY = e.clientY;
  if (mouseSampleTimer) return;
  mouseSampleTimer = setTimeout(() => {
    push({
      timestamp_ms: ts(), event_type: 'hover',
      element_id: elementId(document.elementFromPoint(lastMouseX, lastMouseY)),
      x: normX(lastMouseX), y: normY(lastMouseY),
      value: null, screen_id: window.location.pathname,
      duration_ms: null, is_error: false, metadata: {},
    });
    mouseSampleTimer = null;
  }, 500);
}, true);

// ─── Messages from background ─────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'start') {
    isRecording = true;
    sessionStartMs = msg.sessionStart || Date.now();
    sendResponse({ ok: true });
  }
  if (msg.action === 'stop') {
    isRecording = false;
    sendResponse({ ok: true });
  }
  return true;
});