let pollTimer = null;
let capturedEvents = [];

// ─── Range slider live values ──────────────────────────────────────────────────

['mental','physical','temporal','performance','effort','frustration'].forEach(dim => {
  document.getElementById(dim).addEventListener('input', function() {
    document.getElementById('val-' + dim).textContent = this.value;
  });
});

// ─── Task description required — enable Start only when filled in ──────────────

document.getElementById('taskDesc').addEventListener('input', function() {
  const hasTask = this.value.trim().length > 0;
  document.getElementById('startBtn').disabled = !hasTask;
  document.getElementById('hint').textContent = hasTask
    ? 'Ready to record'
    : 'Enter a task description to begin';
});

// Initialise button state
document.getElementById('startBtn').disabled = true;
document.getElementById('hint').textContent = 'Enter a task description to begin';

// ─── On popup open — restore UI if already recording ─────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  const status = await chrome.runtime.sendMessage({ action: 'status' });
  if (status && status.isRecording) {
    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
    document.getElementById('dot').className = 'dot recording';
    document.getElementById('statusText').textContent = 'Recording across all pages...';
    document.getElementById('taskDesc').disabled = true;
    document.getElementById('participantId').disabled = true;
    document.getElementById('eventCount').textContent = status.eventCount + ' events';

    pollTimer = setInterval(async () => {
      const s = await chrome.runtime.sendMessage({ action: 'status' });
      if (s) document.getElementById('eventCount').textContent = s.eventCount + ' events';
    }, 1000);
  }
});

// ─── Start recording ──────────────────────────────────────────────────────────

document.getElementById('startBtn').addEventListener('click', async () => {
  const taskDesc = document.getElementById('taskDesc').value.trim();
  if (!taskDesc) return;

  const resp = await chrome.runtime.sendMessage({ action: 'start' });
  if (!resp) {
    document.getElementById('hint').textContent = 'Error starting — try reloading the extension.';
    return;
  }
  document.getElementById('startBtn').disabled = true;
  document.getElementById('stopBtn').disabled = false;
  document.getElementById('dot').className = 'dot recording';
  document.getElementById('statusText').textContent = 'Recording across all pages...';
  document.getElementById('taskDesc').disabled = true;
  document.getElementById('participantId').disabled = true;

  pollTimer = setInterval(async () => {
    const s = await chrome.runtime.sendMessage({ action: 'status' });
    if (s) document.getElementById('eventCount').textContent = s.eventCount + ' events';
  }, 1000);
});

// ─── Stop + show NASA-TLX ─────────────────────────────────────────────────────

document.getElementById('stopBtn').addEventListener('click', async () => {
  clearInterval(pollTimer);
  const resp = await chrome.runtime.sendMessage({ action: 'stop' });
  if (!resp || !resp.events) return;
  capturedEvents = resp.events;

  document.getElementById('recordingView').style.display = 'none';
  document.getElementById('tlxView').style.display = 'block';
});

// ─── Export ───────────────────────────────────────────────────────────────────

document.getElementById('exportBtn').addEventListener('click', () => {
  const dims = ['mental','physical','temporal','performance','effort','frustration'];
  const vals = dims.map(d => parseInt(document.getElementById(d).value));
  const weighted_score = Math.round(vals.reduce((a, b) => a + b, 0) / vals.length);

  const nasa_tlx = {
    mental_demand:   vals[0],
    physical_demand: vals[1],
    temporal_demand: vals[2],
    performance:     vals[3],
    effort:          vals[4],
    frustration:     vals[5],
    weighted_score,
  };

  const participantId = document.getElementById('participantId').value || 'P01';

  const output = {
    task_description: document.getElementById('taskDesc').value.trim(),
    participant_id:   participantId,
    recorded_at:      new Date().toISOString(),
    event_count:      capturedEvents.length,
    nasa_tlx,
    events: capturedEvents,
  };

  const blob = new Blob([JSON.stringify(output, null, 2)], { type: 'application/json' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  const filename = `clm_session_${participantId}_${Date.now()}.json`;
  a.href = url;
  a.download = filename;
  a.click();

  document.getElementById('tlxHint').textContent = '✓ ' + filename;
  document.getElementById('exportBtn').textContent = 'Exported ✓';
  document.getElementById('exportBtn').disabled = true;
});