/**
 * UI 自动化管理页
 */
const API = '/api/automation';

let _suites = [];
let _runs = [];
let _selectedSuite = 'cafepress';
let _selectedRunId = null;
let _pollTimer = null;
let _activePanel = 'results';

function $(id) {
  return document.getElementById(id);
}

function toast(msg, type = 'info') {
  const container = $('toastContainer');
  if (!container) return;
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    let msg = `请求失败 (${res.status})`;
    try {
      const err = await res.json();
      msg = err.detail || msg;
    } catch (_) {}
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  return res.json();
}

function formatTime(ts) {
  if (!ts) return '-';
  return new Date(ts).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function formatDuration(ms) {
  if (!ms) return '-';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function statusLabel(status) {
  const map = {
    running: '运行中',
    passed: '通过',
    failed: '失败',
    error: '异常',
    pending: '等待',
  };
  return map[status] || status;
}

function statusClass(status) {
  if (status === 'passed') return 'passed';
  if (status === 'failed' || status === 'error') return 'failed';
  if (status === 'running') return 'running';
  return 'skipped';
}

async function loadStatus() {
  const status = await api('GET', '/status');
  const dot = $('statusDot');
  const text = $('statusText');
  const runBtn = $('runSelectedBtn');
  const banner = $('envBanner');

  if (!status.canRun) {
    dot.className = 'auto-status-dot error';
    text.textContent = status.message;
    runBtn.disabled = true;
    banner.style.display = 'block';
    banner.textContent = status.message;
    if (status.needsBrowserInstall) {
      banner.innerHTML = `${escapeHtml(status.message)}<br><code style="margin-top:6px;display:inline-block;">./scripts/install-playwright.sh</code>`;
    }
  } else if (status.running) {
    dot.className = 'auto-status-dot running';
    text.textContent = '测试运行中…';
    runBtn.disabled = true;
    banner.style.display = 'none';
    startPolling(status.currentRunId);
  } else {
    dot.className = 'auto-status-dot';
    text.textContent = '就绪';
    runBtn.disabled = false;
    banner.style.display = 'none';
    stopPolling();
  }
  return status;
}

async function loadSuites() {
  _suites = await api('GET', '/suites');
  if (!_suites.find(s => s.id === _selectedSuite) && _suites.length) {
    _selectedSuite = _suites[0].id;
  }
  renderSuites();
}

async function loadRuns() {
  _runs = await api('GET', '/runs?limit=50');
  if (!_selectedRunId && _runs.length) {
    _selectedRunId = _runs[0].id;
  }
  renderHistory();
}

function renderSuites() {
  const el = $('suiteList');
  if (!_suites.length) {
    el.innerHTML = '<div class="auto-empty"><div class="auto-empty-icon">📭</div>暂无测试套件</div>';
    return;
  }
  el.innerHTML = _suites.map(s => `
    <div class="auto-suite-card ${_selectedSuite === s.id ? 'active' : ''}" onclick="selectSuite('${s.id}')">
      <div class="auto-suite-name">${escapeHtml(s.name)}</div>
      <div class="auto-suite-desc">${escapeHtml(s.description || s.id)}</div>
      <div class="auto-suite-meta">
        <span>${s.testCount} 个用例</span>
        <span>${s.id}</span>
      </div>
    </div>
  `).join('');
}

function renderHistory() {
  const el = $('historyList');
  if (!_runs.length) {
    el.innerHTML = '<div class="auto-empty"><div class="auto-empty-icon">📋</div>暂无运行记录</div>';
    return;
  }
  el.innerHTML = _runs.map(r => `
    <div class="auto-history-item ${_selectedRunId === r.id ? 'active' : ''}" onclick="selectRun('${r.id}')">
      <div class="auto-history-left">
        <div class="auto-history-title">${escapeHtml(r.suiteName || r.suite)}</div>
        <div class="auto-history-meta">${formatTime(r.startedAt)} · ${statusLabel(r.status)} · ${formatDuration(r.durationMs)}</div>
      </div>
      <div class="auto-history-stats">
        <span style="color:var(--success)">${r.passed}</span> /
        <span style="color:var(--danger)">${r.failed}</span> /
        <span>${r.total}</span>
      </div>
    </div>
  `).join('');
}

async function renderRunDetail() {
  const summaryEl = $('runSummary');
  const resultsEl = $('resultsList');
  const logEl = $('logBox');
  const reportFrame = $('reportFrame');

  if (!_selectedRunId) {
    summaryEl.innerHTML = '';
    resultsEl.innerHTML = '<div class="auto-empty"><div class="auto-empty-icon">▶️</div>选择或运行测试套件查看结果</div>';
    logEl.textContent = '暂无日志';
    reportFrame.src = 'about:blank';
    return;
  }

  const run = await api('GET', `/runs/${_selectedRunId}`);

  summaryEl.innerHTML = `
    <div class="auto-stat-card"><div class="auto-stat-value">${run.total}</div><div class="auto-stat-label">总计</div></div>
    <div class="auto-stat-card passed"><div class="auto-stat-value">${run.passed}</div><div class="auto-stat-label">通过</div></div>
    <div class="auto-stat-card failed"><div class="auto-stat-value">${run.failed}</div><div class="auto-stat-label">失败</div></div>
    <div class="auto-stat-card skipped"><div class="auto-stat-value">${run.skipped}</div><div class="auto-stat-label">跳过</div></div>
  `;

  if (!run.results || !run.results.length) {
    resultsEl.innerHTML = run.status === 'running'
      ? '<div class="auto-empty"><div class="auto-empty-icon">⏳</div>测试运行中，请稍候…</div>'
      : '<div class="auto-empty"><div class="auto-empty-icon">📭</div>无用例结果</div>';
  } else {
    resultsEl.innerHTML = run.results.map(r => `
      <div class="auto-result-item ${r.status}">
        <div class="auto-result-head">
          <div class="auto-result-name">${escapeHtml(r.testName)}</div>
          <span class="auto-result-badge ${r.status}">${r.status}</span>
        </div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:4px;">
          ${escapeHtml(r.className || '')} · ${formatDuration(r.durationMs)}
        </div>
        ${r.errorMessage ? `<div class="auto-result-error">${escapeHtml(r.errorMessage)}</div>` : ''}
        ${r.screenshot ? `
          <div class="auto-result-shot">
            <img src="${API}/runs/${run.id}/screenshots/${encodeURIComponent(r.screenshot)}"
                 alt="screenshot" onclick="window.open(this.src,'_blank')">
          </div>` : ''}
      </div>
    `).join('');
  }

  try {
    const logData = await api('GET', `/runs/${_selectedRunId}/log`);
    logEl.textContent = logData.log || '（空日志）';
  } catch (_) {
    logEl.textContent = '无法加载日志';
  }

  if (run.hasReport && run.status !== 'running') {
    reportFrame.src = `${API}/runs/${_selectedRunId}/report`;
  } else {
    reportFrame.src = 'about:blank';
  }

  if (run.status === 'running') {
    startPolling(run.id);
  }
}

function selectSuite(id) {
  _selectedSuite = id;
  renderSuites();
}

async function selectRun(id) {
  _selectedRunId = id;
  renderHistory();
  if (_activePanel === 'results') await renderRunDetail();
  else switchPanel(_activePanel);
}

async function runSelectedSuite() {
  try {
    const result = await api('POST', '/run', { suite: _selectedSuite });
    _selectedRunId = result.runId;
    toast(`已开始运行: ${_selectedSuite}`, 'success');
    await loadRuns();
    await loadStatus();
    switchPanel('results');
    await renderRunDetail();
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function runAllSuites() {
  try {
    const result = await api('POST', '/run', { suite: 'all' });
    _selectedRunId = result.runId;
    toast('已开始运行全部套件', 'success');
    await loadRuns();
    await loadStatus();
    switchPanel('results');
    await renderRunDetail();
  } catch (err) {
    toast(err.message, 'error');
  }
}

function switchPanel(name) {
  _activePanel = name;
  document.querySelectorAll('.auto-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.panel === name);
  });
  document.querySelectorAll('.auto-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === `panel-${name}`);
  });
  if (name === 'results' || name === 'log' || name === 'report') {
    renderRunDetail();
  }
}

function startPolling(runId) {
  if (_pollTimer) return;
  _pollTimer = setInterval(async () => {
    try {
      await loadRuns();
      await loadStatus();
      if (_selectedRunId === runId || !_selectedRunId) {
        _selectedRunId = runId;
        await renderRunDetail();
        const run = _runs.find(r => r.id === runId);
        if (run && run.status !== 'running') {
          stopPolling();
          toast(`测试完成: ${statusLabel(run.status)}`, run.status === 'passed' ? 'success' : 'error');
        }
      }
    } catch (_) {}
  }, 2500);
}

function stopPolling() {
  if (_pollTimer) {
    clearInterval(_pollTimer);
    _pollTimer = null;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function initTheme() {
  const saved = localStorage.getItem('qa-theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
  const btn = $('themeBtn');
  if (btn) btn.textContent = saved === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('qa-theme', next);
  $('themeBtn').textContent = next === 'dark' ? '☀️' : '🌙';
}

async function init() {
  initTheme();
  try {
    await Promise.all([loadStatus(), loadSuites(), loadRuns()]);
    await renderRunDetail();
  } catch (err) {
    toast('加载失败: ' + err.message, 'error');
  }
}

window.selectSuite = selectSuite;
window.selectRun = selectRun;
window.runSelectedSuite = runSelectedSuite;
window.runAllSuites = runAllSuites;
window.switchPanel = switchPanel;
window.toggleTheme = toggleTheme;

document.addEventListener('DOMContentLoaded', init);
