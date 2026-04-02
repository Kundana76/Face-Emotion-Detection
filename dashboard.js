/**
 * FEIS Dashboard Controller
 * Handles: webcam, detection API calls, overlay drawing, charts, alerts
 */

'use strict';

// ──────────────────────────────────────────────────────────────
// Constants
// ──────────────────────────────────────────────────────────────

const EMOTIONS = ['happy', 'sad', 'angry', 'surprise', 'fear', 'disgust', 'neutral'];

const EMO_EMOJIS = {
  happy: '😊', sad: '😢', angry: '😠',
  surprise: '😲', fear: '😨', disgust: '🤢', neutral: '😐'
};

const EMO_COLORS = {
  happy:    '#ffd700',
  sad:      '#6eb5ff',
  angry:    '#ff4444',
  surprise: '#ff9900',
  fear:     '#bb86fc',
  disgust:  '#4caf50',
  neutral:  '#90a4ae'
};

const CAPTURE_W = 640;
const CAPTURE_H = 480;

// ──────────────────────────────────────────────────────────────
// State
// ──────────────────────────────────────────────────────────────

let isRunning         = false;
let stream            = null;
let detectionTimer    = null;
let statsTimer        = null;
let logsTimer         = null;
let sessionTimer      = null;
let sessionSeconds    = 0;
let detectionInterval = 200;   // ms between API calls
let frameCount        = 0;
let lastFpsTime       = Date.now();
let fps               = 0;

// ──────────────────────────────────────────────────────────────
// DOM References
// ──────────────────────────────────────────────────────────────

const video            = document.getElementById('webcam');
const overlay          = document.getElementById('overlay');
const overlayCtx       = overlay.getContext('2d');
const camPlaceholder   = document.getElementById('camPlaceholder');
const uploadedImg      = document.getElementById('uploadedImg');
const faceCountBadge   = document.getElementById('faceCountBadge');
const liveIndicator    = document.getElementById('liveIndicator');
const fpsDisplay       = document.getElementById('fpsDisplay');
const detectorBadge    = document.getElementById('detectorBadge');
const engineLabel      = document.getElementById('engineLabel');
const skipLabel        = document.getElementById('skipLabel');
const sessionTime      = document.getElementById('sessionTime');
const emotionBarsDiv   = document.getElementById('emotionBars');
const logTableBody     = document.getElementById('logTableBody');
const logCount         = document.getElementById('logCount');
const alertsContainer  = document.getElementById('alertsContainer');

// Stats
const statTotal    = document.getElementById('statTotal');
const statFaces    = document.getElementById('statFaces');
const statDominant = document.getElementById('statDominant');
const statConf     = document.getElementById('statConf');

// Capture canvas (hidden)
const captureCanvas = document.createElement('canvas');
captureCanvas.width  = CAPTURE_W;
captureCanvas.height = CAPTURE_H;
const captureCtx = captureCanvas.getContext('2d');

// ──────────────────────────────────────────────────────────────
// Chart.js setup
// ──────────────────────────────────────────────────────────────

Chart.defaults.color = '#8b949e';
Chart.defaults.borderColor = '#30363d';
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";

// Timeline chart data
const timelineData = {
  labels: [],
  datasets: EMOTIONS.map(e => ({
    label: `${EMO_EMOJIS[e]} ${e.charAt(0).toUpperCase() + e.slice(1)}`,
    data: [],
    borderColor:     EMO_COLORS[e],
    backgroundColor: EMO_COLORS[e] + '20',
    tension: 0.4,
    borderWidth: 2,
    pointRadius: 0,
    fill: false
  }))
};

const timelineChart = new Chart(
  document.getElementById('timelineChart').getContext('2d'),
  {
    type: 'line',
    data: timelineData,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 0 },
      scales: {
        x: {
          grid: { color: '#30363d' },
          ticks: { maxTicksLimit: 8, maxRotation: 0 }
        },
        y: {
          min: 0, max: 100,
          grid: { color: '#30363d' },
          ticks: { callback: v => v + '%' }
        }
      },
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: { boxWidth: 10, font: { size: 10 }, padding: 8 }
        },
        tooltip: {
          callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y}%` }
        }
      }
    }
  }
);

// Pie chart
const pieChart = new Chart(
  document.getElementById('pieChart').getContext('2d'),
  {
    type: 'doughnut',
    data: {
      labels: EMOTIONS.map(e => `${EMO_EMOJIS[e]} ${e.charAt(0).toUpperCase() + e.slice(1)}`),
      datasets: [{
        data: new Array(EMOTIONS.length).fill(0),
        backgroundColor: EMOTIONS.map(e => EMO_COLORS[e]),
        borderColor: '#161b22',
        borderWidth: 2,
        hoverBorderWidth: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '60%',
      animation: { duration: 400 },
      plugins: {
        legend: {
          position: 'right',
          labels: { boxWidth: 10, font: { size: 10 }, padding: 6 }
        },
        tooltip: {
          callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed}` }
        }
      }
    }
  }
);

// ──────────────────────────────────────────────────────────────
// Emotion bars init
// ──────────────────────────────────────────────────────────────

function buildEmotionBars() {
  emotionBarsDiv.innerHTML = '';
  EMOTIONS.forEach(e => {
    emotionBarsDiv.insertAdjacentHTML('beforeend', `
      <div class="emo-row" id="row-${e}">
        <div class="emo-label">${EMO_EMOJIS[e]} ${e.charAt(0).toUpperCase()+e.slice(1)}</div>
        <div class="emo-bar-track">
          <div class="emo-bar-fill emo-${e}" id="bar-${e}" style="width:0%"></div>
        </div>
        <div class="emo-pct" id="pct-${e}">0%</div>
      </div>
    `);
  });
}
buildEmotionBars();

// ──────────────────────────────────────────────────────────────
// Webcam controls
// ──────────────────────────────────────────────────────────────

async function startWebcam() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: CAPTURE_W, height: CAPTURE_H, facingMode: 'user' }
    });
    video.srcObject = stream;
    await video.play();

    // Show video, hide placeholders
    video.classList.add('active');
    camPlaceholder.style.display = 'none';
    uploadedImg.style.display    = 'none';

    // Sync overlay size to video display size
    syncOverlaySize();

    isRunning = true;
    liveIndicator.className = 'live-dot on';
    document.getElementById('btnStart').disabled = true;
    document.getElementById('btnStop').disabled  = false;

    // Start loops
    scheduleDetection();
    startSessionTimer();
  } catch (err) {
    showAlert({
      level:   'danger',
      message: `Camera error: ${err.message}. Try uploading an image instead.`
    });
    console.error('Camera error:', err);
  }
}

function stopWebcam() {
  isRunning = false;

  if (stream) {
    stream.getTracks().forEach(t => t.stop());
    stream = null;
  }

  clearTimeout(detectionTimer);
  clearInterval(sessionTimer);
  sessionSeconds = 0;

  video.classList.remove('active');
  camPlaceholder.style.display = '';
  overlayCtx.clearRect(0, 0, overlay.width, overlay.height);

  liveIndicator.className = 'live-dot off';
  fpsDisplay.textContent  = '0 FPS';
  faceCountBadge.textContent = '0 faces';

  document.getElementById('btnStart').disabled = false;
  document.getElementById('btnStop').disabled  = true;
}

function syncOverlaySize() {
  const rect = video.getBoundingClientRect();
  overlay.width  = rect.width  || video.offsetWidth  || CAPTURE_W;
  overlay.height = rect.height || video.offsetHeight || CAPTURE_H;
}

// ──────────────────────────────────────────────────────────────
// Detection loop
// ──────────────────────────────────────────────────────────────

function scheduleDetection() {
  if (!isRunning) return;
  detectFrame().finally(() => {
    detectionTimer = setTimeout(scheduleDetection, detectionInterval);
  });
}

async function detectFrame() {
  if (!isRunning || video.readyState < 2) return;

  // Draw video → capture canvas
  captureCtx.drawImage(video, 0, 0, CAPTURE_W, CAPTURE_H);
  const imageData = captureCanvas.toDataURL('image/jpeg', 0.75);

  try {
    const resp = await fetch('/api/detect', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ image: imageData })
    });
    const data = await resp.json();

    if (data.success) {
      syncOverlaySize();
      drawOverlay(data.results);
      updateEmotionBars(data.results);
      updateFaceCount(data.results.length);

      // Alerts
      (data.alerts || []).forEach(a => showAlert(a));

      // FPS calculation
      frameCount++;
      const now = Date.now();
      if (now - lastFpsTime >= 1000) {
        fps = Math.round(frameCount * 1000 / (now - lastFpsTime));
        fpsDisplay.textContent = `${fps} FPS`;
        frameCount  = 0;
        lastFpsTime = now;
      }
    }
  } catch (err) {
    console.warn('Detection request failed:', err);
  }
}

// ──────────────────────────────────────────────────────────────
// Canvas overlay drawing
// ──────────────────────────────────────────────────────────────

function drawOverlay(results) {
  overlayCtx.clearRect(0, 0, overlay.width, overlay.height);

  if (!results.length) return;

  // Scale from capture space (640x480) to display space
  const scaleX = overlay.width  / CAPTURE_W;
  const scaleY = overlay.height / CAPTURE_H;

  results.forEach(r => {
    const { x, y, w, h } = r.box;
    const dx = x * scaleX, dy = y * scaleY;
    const dw = w * scaleX, dh = h * scaleY;
    const col = EMO_COLORS[r.emotion] || '#ffffff';

    // Box
    overlayCtx.strokeStyle = col;
    overlayCtx.lineWidth   = 2.5;
    overlayCtx.strokeRect(dx, dy, dw, dh);

    // Corner accents
    const cs = 14;
    overlayCtx.lineWidth = 3;
    [[dx,dy],[dx+dw,dy],[dx,dy+dh],[dx+dw,dy+dh]].forEach(([cx,cy], i) => {
      overlayCtx.beginPath();
      overlayCtx.moveTo(cx + (i%2===0 ? cs : -cs), cy);
      overlayCtx.lineTo(cx, cy);
      overlayCtx.lineTo(cx, cy + (i<2 ? cs : -cs));
      overlayCtx.stroke();
    });

    // Label background
    const label = `${r.emoji || ''} ${r.emotion.toUpperCase()}  ${r.confidence}%`;
    overlayCtx.font = 'bold 12px sans-serif';
    const tw  = overlayCtx.measureText(label).width;
    const lx  = dx;
    const ly  = Math.max(dy - 26, 2);

    overlayCtx.fillStyle = col + 'cc';
    overlayCtx.beginPath();
    overlayCtx.roundRect(lx, ly, tw + 12, 22, 4);
    overlayCtx.fill();

    // Label text
    overlayCtx.fillStyle = '#000';
    overlayCtx.fillText(label, lx + 6, ly + 15);

    // Face ID
    overlayCtx.fillStyle = col;
    overlayCtx.font = '11px sans-serif';
    overlayCtx.fillText(`#${r.face_id}`, dx + 4, dy + dh - 6);
  });
}

// ──────────────────────────────────────────────────────────────
// UI updaters
// ──────────────────────────────────────────────────────────────

function updateEmotionBars(results) {
  // Aggregate all_emotions across detected faces
  const avg = {};
  if (!results.length) {
    EMOTIONS.forEach(e => {
      setBar(e, 0, false);
    });
    statFaces.textContent = '0';
    statConf.textContent  = '—';
    return;
  }

  EMOTIONS.forEach(e => { avg[e] = 0; });
  results.forEach(r => {
    EMOTIONS.forEach(e => {
      avg[e] += (r.all_emotions?.[e] || 0);
    });
  });
  EMOTIONS.forEach(e => { avg[e] = avg[e] / results.length; });

  // Find dominant
  const dominant = results[0]?.emotion || 'neutral';

  EMOTIONS.forEach(e => {
    setBar(e, Math.round(avg[e]), e === dominant);
  });

  statFaces.textContent    = results.length;
  statDominant.textContent = dominant.charAt(0).toUpperCase() + dominant.slice(1);
  statConf.textContent     = `${results[0]?.confidence || 0}%`;
}

function setBar(emotion, value, isDominant) {
  const bar = document.getElementById(`bar-${emotion}`);
  const pct = document.getElementById(`pct-${emotion}`);
  const row = document.getElementById(`row-${emotion}`);
  if (!bar) return;
  bar.style.width         = `${Math.min(value, 100)}%`;
  pct.textContent         = `${value}%`;
  row.className           = `emo-row ${isDominant ? 'dominant' : ''}`;
}

function updateFaceCount(n) {
  faceCountBadge.textContent = `${n} face${n !== 1 ? 's' : ''}`;
}

// ──────────────────────────────────────────────────────────────
// Session timer
// ──────────────────────────────────────────────────────────────

function startSessionTimer() {
  sessionSeconds = 0;
  sessionTimer   = setInterval(() => {
    sessionSeconds++;
    const m = String(Math.floor(sessionSeconds / 60)).padStart(2, '0');
    const s = String(sessionSeconds % 60).padStart(2, '0');
    sessionTime.textContent = `${m}:${s}`;
  }, 1000);
}

// ──────────────────────────────────────────────────────────────
// Stats & charts polling
// ──────────────────────────────────────────────────────────────

async function refreshStats() {
  try {
    const resp = await fetch('/api/stats');
    const data = await resp.json();
    if (!data.success) return;

    const stats = data.stats;
    statTotal.textContent = stats.total_detections || 0;
    if (!isRunning) {
      statDominant.textContent =
        (stats.dominant_emotion || 'none').charAt(0).toUpperCase() +
        (stats.dominant_emotion || 'none').slice(1);
    }

    // Update pie chart
    const cnts = stats.emotion_counts || {};
    pieChart.data.datasets[0].data = EMOTIONS.map(e => cnts[e] || 0);
    pieChart.update('none');

    // Update timeline
    const tl = data.timeline || [];
    refreshTimeline(tl);

  } catch (err) {
    console.warn('Stats refresh failed:', err);
  }
}

function refreshTimeline(timeline) {
  if (!timeline.length) return;

  // Take last 30 time buckets
  const recent = timeline.slice(-30);
  const labels = recent.map(t => t.time.slice(11, 19)); // HH:MM:SS

  timelineData.labels = labels;
  EMOTIONS.forEach((e, i) => {
    timelineData.datasets[i].data = recent.map(t => t.emotions?.[e] || 0);
  });
  timelineChart.update('none');
}

async function refreshLogs() {
  try {
    const resp = await fetch('/api/logs?limit=40');
    const data = await resp.json();
    if (!data.success) return;

    const logs = data.logs || [];
    logCount.textContent = `${logs.length} recent entries`;

    if (!logs.length) {
      logTableBody.innerHTML =
        '<tr><td colspan="6" class="text-center py-3 text-muted">No detections yet</td></tr>';
      return;
    }

    logTableBody.innerHTML = logs.map(lg => {
      const ts  = (lg.timestamp || '').replace('T', ' ').slice(0, 19);
      const emo = lg.emotion || 'unknown';
      const col = EMO_COLORS[emo] || '#ccc';
      return `
        <tr>
          <td>${lg.id}</td>
          <td style="font-size:0.72rem; color:#8b949e;">${ts}</td>
          <td><span style="color:${col};">#${lg.face_id}</span></td>
          <td>
            <span class="emo-chip"
                  style="background:${col}22; color:${col}; border:1px solid ${col}44;">
              ${EMO_EMOJIS[emo] || '?'} ${emo.charAt(0).toUpperCase()+emo.slice(1)}
            </span>
          </td>
          <td style="font-variant-numeric:tabular-nums;">${lg.confidence}%</td>
          <td style="font-size:0.7rem; color:#8b949e;">${lg.session_id || ''}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.warn('Log refresh failed:', err);
  }
}

// ──────────────────────────────────────────────────────────────
// Image upload
// ──────────────────────────────────────────────────────────────

async function uploadImage(event) {
  const file = event.target.files[0];
  if (!file) return;

  // If webcam is running, stop it
  if (isRunning) stopWebcam();

  // Show image in UI
  const url = URL.createObjectURL(file);
  uploadedImg.src     = url;
  uploadedImg.style.display = 'block';
  camPlaceholder.style.display = 'none';
  video.classList.remove('active');

  // Send to API
  const formData = new FormData();
  formData.append('image', file);

  try {
    const resp = await fetch('/api/detect-image', { method: 'POST', body: formData });
    const data = await resp.json();

    if (data.success) {
      // Show annotated version
      uploadedImg.src = data.annotated_image;
      updateEmotionBars(data.results);
      updateFaceCount(data.results.length);

      // Sync overlay (clear it since image already has annotations)
      syncOverlayToImage();

      showAlert({
        level:   'warning',
        message: `✅ Image analysed: ${data.face_count} face(s) detected.`
      });
    } else {
      showAlert({ level: 'danger', message: `Error: ${data.error}` });
    }
  } catch (err) {
    showAlert({ level: 'danger', message: `Upload failed: ${err.message}` });
  }

  // Reset input so same file can be re-uploaded
  event.target.value = '';
}

function syncOverlayToImage() {
  // Clear overlay — annotations are baked into returned image
  overlayCtx.clearRect(0, 0, overlay.width, overlay.height);
}

// ──────────────────────────────────────────────────────────────
// Report download
// ──────────────────────────────────────────────────────────────

async function downloadReport() {
  showAlert({ level: 'warning', message: '📄 Generating report...' });
  try {
    const resp = await fetch('/api/report');
    if (!resp.ok) {
      const err = await resp.json();
      showAlert({ level: 'danger', message: `Report error: ${err.error}` });
      return;
    }
    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `FEIS_Report_${new Date().toISOString().slice(0,10)}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    showAlert({ level: 'warning', message: '✅ Report downloaded!' });
  } catch (err) {
    showAlert({ level: 'danger', message: `Download failed: ${err.message}` });
  }
}

// ──────────────────────────────────────────────────────────────
// Clear logs
// ──────────────────────────────────────────────────────────────

async function clearLogs() {
  if (!confirm('Clear all detection logs? This cannot be undone.')) return;
  try {
    await fetch('/api/logs', { method: 'DELETE' });
    EMOTIONS.forEach(e => setBar(e, 0, false));
    statTotal.textContent    = '0';
    statDominant.textContent = '—';
    statConf.textContent     = '—';
    pieChart.data.datasets[0].data = new Array(EMOTIONS.length).fill(0);
    pieChart.update();
    logTableBody.innerHTML =
      '<tr><td colspan="6" class="text-center py-3 text-muted">Logs cleared</td></tr>';
    showAlert({ level: 'warning', message: '🗑️ All logs cleared.' });
  } catch (err) {
    showAlert({ level: 'danger', message: `Clear failed: ${err.message}` });
  }
}

// ──────────────────────────────────────────────────────────────
// Alerts
// ──────────────────────────────────────────────────────────────

const shownAlerts = new Set();

function showAlert(alert) {
  const key = alert.message;
  if (shownAlerts.has(key)) return;
  shownAlerts.add(key);
  setTimeout(() => shownAlerts.delete(key), 6000);

  const div = document.createElement('div');
  div.className = `alert-toast ${alert.level || 'warning'}`;
  div.innerHTML = `
    <span>${alert.message}</span>
    <span class="close-btn" onclick="this.parentElement.remove()">✕</span>
  `;
  alertsContainer.appendChild(div);
  setTimeout(() => div.remove(), 5000);
}

// ──────────────────────────────────────────────────────────────
// Settings save
// ──────────────────────────────────────────────────────────────

async function saveSettings() {
  const frameSkip = parseInt(document.getElementById('frameSkipRange').value);
  detectionInterval = parseInt(document.getElementById('intervalSelect').value);
  skipLabel.textContent = frameSkip;

  const thresholds = {
    angry:   { confidence: parseInt(document.getElementById('threshAngry').value), duration: 3 },
    fear:    { confidence: parseInt(document.getElementById('threshFear').value),  duration: 3 },
    sad:     { confidence: parseInt(document.getElementById('threshSad').value),   duration: 5 }
  };

  try {
    await fetch('/api/config', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ frame_skip: frameSkip, thresholds })
    });
    showAlert({ level: 'warning', message: '✅ Settings saved.' });
    bootstrap.Offcanvas.getInstance(document.getElementById('settingsPanel'))?.hide();
  } catch (err) {
    showAlert({ level: 'danger', message: `Settings error: ${err.message}` });
  }
}

// ──────────────────────────────────────────────────────────────
// Fetch initial config
// ──────────────────────────────────────────────────────────────

async function loadConfig() {
  try {
    const resp = await fetch('/api/config');
    const data = await resp.json();
    detectorBadge.textContent = `Engine: ${data.detector || 'unknown'}`;
    engineLabel.textContent   = data.detector || '—';
    skipLabel.textContent     = data.frame_skip || 3;
    document.getElementById('frameSkipRange').value = data.frame_skip || 3;
    document.getElementById('frameSkipVal').textContent = data.frame_skip || 3;
  } catch (err) {
    detectorBadge.textContent = 'Engine: unknown';
  }
}

// ──────────────────────────────────────────────────────────────
// Window resize handler
// ──────────────────────────────────────────────────────────────

window.addEventListener('resize', () => {
  if (isRunning) syncOverlaySize();
});

// ──────────────────────────────────────────────────────────────
// Bootstrap / Init
// ──────────────────────────────────────────────────────────────

(function init() {
  loadConfig();
  refreshStats();
  refreshLogs();

  // Poll stats every 3 seconds, logs every 5 seconds
  setInterval(refreshStats, 3000);
  setInterval(refreshLogs,  5000);
})();
