/**
 * CLM Session Logger — background service worker v5
 *
 * Key fixes from v4:
 * 1. Global session clock: sessionStart is stored in chrome.storage.session
 *    and sent to every content script so timestamps are absolute across
 *    the full session, not relative to individual page loads.
 *
 * 2. chrome.webNavigation: replaces MutationObserver pathname detection.
 *    webNavigation.onCompleted fires on full page loads (traditional sites).
 *    webNavigation.onHistoryStateUpdated fires on SPA route changes
 *    (React, Vue, Angular, Next.js) where pathname may not change.
 *    Together they cover both traditional multi-page and SPA architectures.
 */

async function getState() {
  const data = await chrome.storage.session.get([
    'isRecording', 'events', 'sessionStart'
  ]);
  return {
    isRecording:  data.isRecording  || false,
    events:       data.events       || [],
    sessionStart: data.sessionStart || null,
  };
}

async function setState(patch) {
  await chrome.storage.session.set(patch);
}

// ─── Message handler ──────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  if (msg.action === 'push_event') {
    (async () => {
      const state = await getState();
      if (state.isRecording) {
        state.events.push(msg.event);
        await setState({ events: state.events });
      }
      sendResponse({ ok: true });
    })();
    return true;
  }

  if (msg.action === 'start') {
    (async () => {
      const sessionStart = Date.now();
      await setState({ isRecording: true, events: [], sessionStart });
      // Notify active tab with global session start time
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      for (const tab of tabs) {
        chrome.tabs.sendMessage(tab.id, { action: 'start', sessionStart })
          .catch(() => {});
      }
      sendResponse({ status: 'recording', sessionStart });
    })();
    return true;
  }

  if (msg.action === 'stop') {
    (async () => {
      const state = await getState();
      await setState({ isRecording: false });
      const tabs = await chrome.tabs.query({});
      for (const tab of tabs) {
        chrome.tabs.sendMessage(tab.id, { action: 'stop' }).catch(() => {});
      }
      sendResponse({ status: 'stopped', events: state.events });
    })();
    return true;
  }

  if (msg.action === 'status') {
    (async () => {
      const state = await getState();
      sendResponse({ isRecording: state.isRecording, eventCount: state.events.length });
    })();
    return true;
  }

  return true;
});

// ─── Navigation detection — traditional multi-page (onCompleted) ──────────────

chrome.webNavigation.onCompleted.addListener(async (details) => {
  // Only main frame, not iframes
  if (details.frameId !== 0) return;
  const state = await getState();
  if (!state.isRecording) return;

  // Tell the newly loaded content script to start recording
  // Pass the global sessionStart so timestamps are absolute
  chrome.tabs.sendMessage(details.tabId, {
    action: 'start',
    sessionStart: state.sessionStart,
  }).catch(() => {});

  // Push a navigation event from the background
  state.events.push({
    timestamp_ms: Date.now() - state.sessionStart,
    event_type: 'navigation',
    element_id: null,
    x: null,
    y: null,
    value: null,
    screen_id: new URL(details.url).pathname,
    duration_ms: null,
    is_error: false,
    metadata: { trigger: 'webNavigation.onCompleted', url: details.url },
  });
  await setState({ events: state.events });
});

// ─── Navigation detection — SPA route changes (onHistoryStateUpdated) ─────────

chrome.webNavigation.onHistoryStateUpdated.addListener(async (details) => {
  if (details.frameId !== 0) return;
  const state = await getState();
  if (!state.isRecording) return;

  state.events.push({
    timestamp_ms: Date.now() - state.sessionStart,
    event_type: 'navigation',
    element_id: null,
    x: null,
    y: null,
    value: null,
    screen_id: new URL(details.url).pathname,
    duration_ms: null,
    is_error: false,
    metadata: { trigger: 'webNavigation.onHistoryStateUpdated', url: details.url },
  });
  await setState({ events: state.events });
});