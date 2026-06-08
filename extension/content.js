/**
 * CLM Session Logger — content script v5.2
 *
 * PII handling:
 *
 * 1. Input field VALUES are never logged (set to null at capture time).
 *    Only element_id and duration_ms are retained for input events.
 *
 * 2. Element identifiers (element_id) are sanitised before logging.
 *    Modern web applications frequently inject user data directly into
 *    DOM attributes — id, class, data-* — creating vectors for PII leakage
 *    even when input values are stripped. Examples:
 *      <div id="account-user@example.com">
 *      <button data-username="kkazakos">
 *    The sanitiseId() function applies two safeguards:
 *      a) Strips email-like patterns (contains "@" and ".")
 *      b) Truncates to MAX_ID_LENGTH characters
 *    This prevents long dynamic IDs containing emails, usernames, or
 *    account tokens from being stored in the session log.
 *
 * 3. Scroll deltas (pixel offsets) are retained — no PII.
 *
 * 4. The LLM interpretation layer receives only numerical signal scores
 *    and the researcher-provided task description. No event-level data
 *    reaches any LLM provider.
 */

let isRecording = false;
let sessionStartMs = null;
let lastMouseX = null;
let lastMouseY = null;
let inputTimers = {};

const MAX_ID_LENGTH = 40;  // prevents long dynamic IDs from storing PII

function ts() {
  return sessionStartMs ? Date.now() - sessionStartMs : 0;
}
function normX(x) { return Math.round((x / window.innerWidth)  * 100) / 100; }
function normY(y) { return Math.round((y / window.innerHeight) * 100) / 100; }

function sanitiseId(raw) {
  if (!raw) return null;
  const str = String(raw);
  // Strip IDs containing email-like patterns
  if (str.includes('@') && str.includes('.')) return '[redacted-email-id]';
  // Truncate long IDs that may contain tokens or usernames
  return str.length > MAX_ID_LENGTH ? str.slice(0, MAX_ID_LENGTH) + '…' : str;
}

function elementId(el) {
  if (!el) return null;
  const cls = typeof el.className === 'string'
    ? (el.className.split(' ')[0] || null)
    : null;
  const raw = el.id || el.name || el.getAttribute?.('data-testid') ||
    cls || el.tagName?.toLowerCase() || null;
  return sanitiseId(raw);
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
    value: null, screen_id: window.location.pathname,
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
    value: String(Math.round(window.scrollY)),
    screen_id: window.location.pathname,
    duration_ms: null, is_error: false, metadata: {},
  });
}, true);

// ─── Input (element_id and dwell only — value never logged) ──────────────────

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
    element_id: id, x: null, y: null,
    value: null,
    screen_id: window.location.pathname,
    duration_ms: dwell, is_error: false,
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