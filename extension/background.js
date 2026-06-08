/**
 * CLM Session Logger — background service worker v4
 *
 * Uses chrome.storage.session to persist recording state and events.
 * This survives service worker termination (a Chrome MV3 limitation
 * where in-memory variables are lost after ~30s of inactivity).
 */

async function getState() {
  const data = await chrome.storage.session.get(['isRecording', 'events', 'sessionStart']);
  return {
    isRecording: data.isRecording || false,
    events: data.events || [],
    sessionStart: data.sessionStart || null,
  };
}

async function setState(patch) {
  await chrome.storage.session.set(patch);
}

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
      await setState({ isRecording: true, events: [], sessionStart: Date.now() });
      // Tell the active tab's content script to start
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      for (const tab of tabs) {
        chrome.tabs.sendMessage(tab.id, { action: 'start' }).catch(() => {});
      }
      sendResponse({ status: 'recording' });
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

// When a new page loads mid-session, tell its content script to start
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo) => {
  if (changeInfo.status === 'complete') {
    const state = await getState();
    if (state.isRecording) {
      chrome.tabs.sendMessage(tabId, { action: 'start' }).catch(() => {});
    }
  }
});
