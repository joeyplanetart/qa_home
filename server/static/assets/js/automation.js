/**
 * UI 自动化管理页
 */
const API = '/api/automation';
const CONFIG_STORAGE_KEY = 'qa-automation-run-config';

const DEFAULT_RUN_CONFIG = {
  headed: false,
  browser: 'chromium',
  viewportWidth: 1280,
  viewportHeight: 720,
  slowMo: 0,
  timeout: 30000,
  device: '',
  video: 'off',
  tracing: 'off',
  locale: 'en-US',
};

let _suites = [];
let _runs = [];
let _selectedSuite = 'cafepress';
let _selectedRunId = null;
let _selectedCaseFile = null;
let _selectedCaseName = null;
let _casesData = null;
let _pollTimer = null;
let _activePanel = 'cases';
let _collapsedCaseFiles = new Set();
let _checkedTests = new Set();
let _defaultsAppliedForSuite = null;

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

function formatConfigSummary(config, options = {}) {
  if (!config) return '';
  const { includeSelected = true } = options;
  const parts = [];
  parts.push(config.headed ? '有头' : '无头');
  parts.push(config.browser || 'chromium');
  if (config.device) {
    parts.push(config.device);
  } else {
    parts.push(`${config.viewportWidth || 1280}×${config.viewportHeight || 720}`);
  }
  if (config.slowMo > 0) parts.push(`慢动作 ${config.slowMo}ms`);
  if (config.video && config.video !== 'off') parts.push(`录像:${config.video}`);
  if (config.tracing && config.tracing !== 'off') parts.push(`trace:${config.tracing}`);
  if (includeSelected && config.selectedTests?.length) {
    parts.push(`${config.selectedTests.length} 个选用例`);
  }
  return parts.join(' · ');
}

function loadRunConfig() {
  try {
    const saved = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (saved) return { ...DEFAULT_RUN_CONFIG, ...JSON.parse(saved) };
  } catch (_) {}
  return { ...DEFAULT_RUN_CONFIG };
}

function saveRunConfig(config) {
  localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(config));
}

function getRunConfigFromUI() {
  const headed = document.querySelector('input[name="cfgHeaded"]:checked')?.value === '1';
  return {
    headed,
    browser: $('cfgBrowser')?.value || 'chromium',
    viewportWidth: parseInt($('cfgViewportWidth')?.value, 10) || 1280,
    viewportHeight: parseInt($('cfgViewportHeight')?.value, 10) || 720,
    slowMo: parseInt($('cfgSlowMo')?.value, 10) || 0,
    timeout: parseInt($('cfgTimeout')?.value, 10) || 30000,
    device: $('cfgDevice')?.value || '',
    video: $('cfgVideo')?.value || 'off',
    tracing: $('cfgTracing')?.value || 'off',
    locale: $('cfgLocale')?.value || 'en-US',
  };
}

function applyRunConfigToUI(config) {
  const cfg = { ...DEFAULT_RUN_CONFIG, ...config };
  document.querySelectorAll('input[name="cfgHeaded"]').forEach(el => {
    el.checked = el.value === (cfg.headed ? '1' : '0');
  });
  if ($('cfgBrowser')) $('cfgBrowser').value = cfg.browser;
  if ($('cfgViewportWidth')) $('cfgViewportWidth').value = cfg.viewportWidth;
  if ($('cfgViewportHeight')) $('cfgViewportHeight').value = cfg.viewportHeight;
  if ($('cfgSlowMo')) $('cfgSlowMo').value = cfg.slowMo;
  if ($('cfgTimeout')) $('cfgTimeout').value = cfg.timeout;
  if ($('cfgDevice')) $('cfgDevice').value = cfg.device || '';
  if ($('cfgVideo')) $('cfgVideo').value = cfg.video;
  if ($('cfgTracing')) $('cfgTracing').value = cfg.tracing;
  if ($('cfgLocale')) $('cfgLocale').value = cfg.locale;
  syncViewportPreset();
  onDeviceChange(false);
}

function syncViewportPreset() {
  const w = parseInt($('cfgViewportWidth')?.value, 10);
  const h = parseInt($('cfgViewportHeight')?.value, 10);
  const preset = `${w}x${h}`;
  const select = $('cfgViewportPreset');
  if (!select) return;
  const match = Array.from(select.options).find(opt => opt.value === preset);
  select.value = match ? preset : 'custom';
}

function applyViewportPreset() {
  const preset = $('cfgViewportPreset')?.value;
  if (!preset || preset === 'custom') return;
  const [w, h] = preset.split('x').map(Number);
  if ($('cfgViewportWidth')) $('cfgViewportWidth').value = w;
  if ($('cfgViewportHeight')) $('cfgViewportHeight').value = h;
  if ($('cfgDevice')) $('cfgDevice').value = '';
  onDeviceChange(false);
  saveRunConfig(getRunConfigFromUI());
}

function onDeviceChange(save = true) {
  const device = $('cfgDevice')?.value;
  const customRow = $('cfgViewportCustom');
  const presetSelect = $('cfgViewportPreset');
  const disabled = Boolean(device);
  if (customRow) customRow.style.opacity = disabled ? '0.45' : '1';
  if (presetSelect) presetSelect.disabled = disabled;
  if ($('cfgViewportWidth')) $('cfgViewportWidth').disabled = disabled;
  if ($('cfgViewportHeight')) $('cfgViewportHeight').disabled = disabled;
  if (save) saveRunConfig(getRunConfigFromUI());
}

function toggleRunConfig() {
  $('runConfigPanel')?.classList.toggle('collapsed');
}

function resetRunConfig() {
  applyRunConfigToUI(DEFAULT_RUN_CONFIG);
  saveRunConfig(DEFAULT_RUN_CONFIG);
  toast('已恢复默认运行配置', 'info');
}

function bindRunConfigEvents() {
  const panel = $('runConfigPanel');
  if (!panel) return;
  panel.querySelectorAll('input, select').forEach(el => {
    el.addEventListener('change', () => {
      if (el.id === 'cfgViewportWidth' || el.id === 'cfgViewportHeight') {
        syncViewportPreset();
      }
      saveRunConfig(getRunConfigFromUI());
    });
  });
}

const MARKER_LABELS = {
  selected: '默认',
  smoke: '冒烟',
};

function formatMarkerLabel(marker) {
  return MARKER_LABELS[marker] || marker;
}

function renderCaseMarkers(markers) {
  if (!markers || !markers.length) return '';
  return `<div class="auto-case-item-markers">${markers.map(marker => `
    <span class="auto-case-marker ${marker === 'selected' ? 'selected' : ''}">${escapeHtml(formatMarkerLabel(marker))}</span>
  `).join('')}</div>`;
}

function applyDefaultCaseSelection() {
  if (!_casesData || _defaultsAppliedForSuite === _selectedSuite) return;
  let changed = false;
  _casesData.files.forEach(file => {
    file.cases.forEach(c => {
      if (c.selected) {
        _checkedTests.add(testCaseKey(file.path, c.name));
        if (_collapsedCaseFiles.has(file.path)) {
          _collapsedCaseFiles.delete(file.path);
          changed = true;
        }
      }
    });
  });
  _defaultsAppliedForSuite = _selectedSuite;
  if (changed) saveCollapsedCaseFiles();
}

function getSuiteTestCount() {
  const suite = _suites.find(s => s.id === _selectedSuite);
  return suite?.testCount || _casesData?.testCount || 0;
}

function updateRunButtons() {
  const count = _checkedTests.size;
  const suiteTotal = getSuiteTestCount();

  const casesBtn = $('runSelectedCasesBtn');
  if (casesBtn) {
    casesBtn.disabled = count === 0;
    casesBtn.textContent = count > 0
      ? `▶ 运行选中 (${count}${suiteTotal ? `/${suiteTotal}` : ''})`
      : '▶ 运行选中';
  }

  const sidebarBtn = $('runSelectedBtn');
  if (sidebarBtn && !sidebarBtn.disabled) {
    sidebarBtn.textContent = count > 0
      ? `▶ 运行选中 (${count}${suiteTotal ? `/${suiteTotal}` : ''})`
      : (suiteTotal > 0 ? `▶ 运行套件 (${suiteTotal})` : '▶ 运行套件');
  }
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

const ARTIFACT_LABELS = {
  action: '操作',
  email: 'Email',
  password: 'Password',
  customer_id: 'Customer ID',
  site_id: '页面 Site ID',
  site_code: '站点代码',
  page_url: '页面 URL',
  expected_site_id: '期望 Site ID',
  order_id: '订单号',
  order_email: '下单 Email',
  total: '订单金额',
  status: '订单状态',
};

function formatArtifactLabel(key) {
  return ARTIFACT_LABELS[key] || key;
}

function renderArtifacts(artifacts) {
  if (!artifacts || !Object.keys(artifacts).length) return '';
  const rows = Object.entries(artifacts)
    .filter(([key, value]) => key !== 'screenshots' && value !== null && value !== undefined && value !== '')
    .map(([key, value]) => `
      <div class="auto-result-artifact-row">
        <span class="auto-result-artifact-label">${escapeHtml(formatArtifactLabel(key))}</span>
        <span class="auto-result-artifact-value">${escapeHtml(String(value))}</span>
      </div>
    `).join('');
  if (!rows) return '';
  return `<div class="auto-result-artifacts"><div class="auto-result-artifacts-title">测试数据</div>${rows}</div>`;
}

function renderScreenshots(runId, result) {
  const shots = result.screenshots?.length
    ? result.screenshots
    : (result.screenshot ? [{ file: result.screenshot, label: '截图' }] : []);
  if (!shots.length) return '';
  return `
    <div class="auto-result-shots">
      <div class="auto-result-shots-title">步骤截图</div>
      <div class="auto-result-shots-grid">
        ${shots.map(shot => `
          <figure class="auto-result-shot-card">
            <img src="${API}/runs/${runId}/screenshots/${encodeURIComponent(shot.file)}"
                 alt="${escapeAttr(shot.label || shot.file)}"
                 loading="lazy"
                 onclick="window.open(this.src,'_blank')">
            <figcaption>${escapeHtml(shot.label || shot.file)}</figcaption>
          </figure>
        `).join('')}
      </div>
    </div>`;
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
    updateRunButtons();
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
        ${r.config ? `<div class="auto-history-meta">${escapeHtml(formatConfigSummary(r.config))}</div>` : ''}
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

  const configSummary = formatConfigSummary(run.config, { includeSelected: false });
  const selectedCount = run.config?.selectedTests?.length || 0;
  const scopeParts = [];
  if (selectedCount > 0) {
    let scopeText = `本次运行 ${selectedCount} 个选用例`;
    if (run.total !== selectedCount && run.status !== 'running') {
      scopeText += `（结果 ${run.total} 个，请确认是否误点了「运行套件」）`;
    }
    scopeParts.push(scopeText);
  }
  if (configSummary) scopeParts.push(configSummary);
  const scopeHint = scopeParts.length
    ? `<div class="auto-run-scope-hint">${escapeHtml(scopeParts.join(' · '))}</div>`
    : '';
  summaryEl.innerHTML = `
    <div class="auto-stat-card"><div class="auto-stat-value">${run.total}</div><div class="auto-stat-label">总计</div></div>
    <div class="auto-stat-card passed"><div class="auto-stat-value">${run.passed}</div><div class="auto-stat-label">通过</div></div>
    <div class="auto-stat-card failed"><div class="auto-stat-value">${run.failed}</div><div class="auto-stat-label">失败</div></div>
    <div class="auto-stat-card skipped"><div class="auto-stat-value">${run.skipped}</div><div class="auto-stat-label">跳过</div></div>
    ${scopeHint}
  `;

  const configBadge = $('runConfigBadge');
  if (configBadge) configBadge.style.display = 'none';

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
        ${renderArtifacts(r.artifacts)}
        ${r.errorMessage ? `<div class="auto-result-error">${escapeHtml(r.errorMessage)}</div>` : ''}
        ${renderScreenshots(run.id, r)}
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
  _selectedCaseFile = null;
  _selectedCaseName = null;
  _checkedTests.clear();
  _defaultsAppliedForSuite = null;
  renderSuites();
  if (_activePanel === 'cases') {
    loadCases();
  } else {
    updateRunButtons();
  }
}

async function loadCases() {
  const el = $('casesList');
  loadCollapsedCaseFiles();
  try {
    _casesData = await api('GET', `/suites/${encodeURIComponent(_selectedSuite)}/cases`);
    applyDefaultCaseSelection();
    renderCasesList();
    if (_selectedCaseFile) {
      await viewTestFile(_selectedCaseFile, _selectedCaseName);
    } else if (_casesData.files.length) {
      const first = _casesData.files[0];
      if (first.cases.length) {
        await viewTestFile(first.path, first.cases[0].name, first.cases[0].line);
      } else {
        await viewTestFile(first.path);
      }
    }
  } catch (err) {
    el.innerHTML = `<div class="auto-empty"><div class="auto-empty-icon">⚠️</div>${escapeHtml(err.message)}</div>`;
  }
}

function testCaseKey(filePath, caseName) {
  return `${filePath}::${caseName}`;
}

function updateCasesToolbar() {
  updateRunButtons();
}

function toggleCaseSelection(filePath, caseName, event) {
  event.stopPropagation();
  const key = testCaseKey(filePath, caseName);
  if (_checkedTests.has(key)) {
    _checkedTests.delete(key);
  } else {
    _checkedTests.add(key);
  }
  renderCasesList();
}

function toggleFileSelection(filePath, caseNames, event) {
  event.stopPropagation();
  const keys = caseNames.map(name => testCaseKey(filePath, name));
  const allChecked = keys.every(key => _checkedTests.has(key));
  keys.forEach(key => {
    if (allChecked) _checkedTests.delete(key);
    else _checkedTests.add(key);
  });
  renderCasesList();
}

function clearCaseSelection() {
  _checkedTests.clear();
  renderCasesList();
}

function isFileChecked(file, keys) {
  if (!file.cases.length) return false;
  return keys.every(key => _checkedTests.has(key));
}

function isFileIndeterminate(file, keys) {
  if (!file.cases.length) return false;
  const checkedCount = keys.filter(key => _checkedTests.has(key)).length;
  return checkedCount > 0 && checkedCount < keys.length;
}

function collapsedCasesStorageKey() {
  return `qa-automation-collapsed-${_selectedSuite}`;
}

function loadCollapsedCaseFiles() {
  try {
    const saved = localStorage.getItem(collapsedCasesStorageKey());
    _collapsedCaseFiles = saved ? new Set(JSON.parse(saved)) : new Set();
  } catch (_) {
    _collapsedCaseFiles = new Set();
  }
}

function saveCollapsedCaseFiles() {
  localStorage.setItem(
    collapsedCasesStorageKey(),
    JSON.stringify([..._collapsedCaseFiles]),
  );
}

function toggleCaseFile(filePath, event) {
  event.stopPropagation();
  if (_collapsedCaseFiles.has(filePath)) {
    _collapsedCaseFiles.delete(filePath);
  } else {
    _collapsedCaseFiles.add(filePath);
  }
  saveCollapsedCaseFiles();
  renderCasesList();
}

function renderCasesList() {
  const el = $('casesList');
  if (!_casesData || !_casesData.files.length) {
    el.innerHTML = '<div class="auto-empty"><div class="auto-empty-icon">📭</div>该套件暂无测试文件</div>';
    return;
  }

  el.innerHTML = `
    <div class="auto-cases-toolbar">
      <div class="auto-cases-toolbar-left">
        <span class="auto-cases-suite-meta">${escapeHtml(_casesData.suiteName)} · ${_casesData.testCount} 个用例</span>
      </div>
      <div class="auto-cases-toolbar-actions">
        <button type="button" class="auto-cases-tool-btn" id="runSelectedCasesBtn" disabled onclick="runCheckedCases()">▶ 运行选中</button>
        <button type="button" class="auto-cases-tool-btn subtle" onclick="clearCaseSelection()">清除</button>
      </div>
    </div>
    ${_casesData.files.map(file => {
      const collapsed = _collapsedCaseFiles.has(file.path);
      const caseKeys = file.cases.map(c => testCaseKey(file.path, c.name));
      const fileChecked = isFileChecked(file, caseKeys);
      const fileIndeterminate = isFileIndeterminate(file, caseKeys);
      return `
      <div class="auto-case-file${collapsed ? ' collapsed' : ''}">
        <div class="auto-case-file-head">
          <button type="button" class="auto-case-toggle" title="${collapsed ? '展开' : '收起'}"
                  onclick="toggleCaseFile('${escapeAttr(file.path)}', event)" aria-expanded="${!collapsed}">
            <span class="auto-case-chevron">▼</span>
          </button>
          <label class="auto-case-file-check" onclick="event.stopPropagation()">
            <input type="checkbox" ${fileChecked ? 'checked' : ''}
                   ${fileIndeterminate ? 'data-indeterminate="1"' : ''}
                   onchange="toggleFileSelection('${escapeAttr(file.path)}', [${file.cases.map(c => `'${escapeAttr(c.name)}'`).join(',')}], event)">
          </label>
          <div class="auto-case-file-info" onclick="viewTestFile('${escapeAttr(file.path)}')">
            <div class="auto-case-file-name">📄 ${escapeHtml(file.name)}</div>
            <div class="auto-case-file-meta">${file.cases.length} 用例 · ${file.lineCount} 行</div>
            ${file.moduleDoc ? `<div class="auto-case-file-doc">${escapeHtml(file.moduleDoc)}</div>` : ''}
          </div>
          <button type="button" class="auto-case-run-btn" title="运行此文件"
                  onclick="runTestFile('${escapeAttr(file.path)}', event)">▶</button>
        </div>
        <div class="auto-case-items">
          ${file.cases.map(c => {
            const key = testCaseKey(file.path, c.name);
            return `
            <div class="auto-case-item ${_selectedCaseFile === file.path && _selectedCaseName === c.name ? 'active' : ''}">
              <label class="auto-case-check" onclick="event.stopPropagation()">
                <input type="checkbox" ${_checkedTests.has(key) ? 'checked' : ''}
                       onchange="toggleCaseSelection('${escapeAttr(file.path)}', '${escapeAttr(c.name)}', event)">
              </label>
              <div class="auto-case-item-body"
                   onclick="viewTestFile('${escapeAttr(file.path)}', '${escapeAttr(c.name)}', ${c.line})">
                <div class="auto-case-item-name" title="${escapeAttr(c.name)}">${escapeHtml(c.name)}</div>
                ${renderCaseMarkers(c.markers)}
                ${c.doc ? `<div class="auto-case-item-doc">${escapeHtml(c.doc)}</div>` : ''}
                <div class="auto-case-item-line">Line ${c.line}</div>
              </div>
              <button type="button" class="auto-case-run-btn" title="运行此用例"
                      onclick="runSingleCase('${escapeAttr(file.path)}', '${escapeAttr(c.name)}', event)">▶</button>
            </div>`;
          }).join('')}
        </div>
      </div>`;
    }).join('')}
  `;

  el.querySelectorAll('input[data-indeterminate="1"]').forEach(input => {
    input.indeterminate = true;
  });
  updateCasesToolbar();
}

async function viewTestFile(filePath, caseName = null, highlightLine = null) {
  _selectedCaseFile = filePath;
  _selectedCaseName = caseName;
  if (caseName) {
    _collapsedCaseFiles.delete(filePath);
    saveCollapsedCaseFiles();
  }
  renderCasesList();

  try {
    const file = await api('GET', `/suites/${encodeURIComponent(_selectedSuite)}/files/${filePath}`);
    const header = $('codeHeader');
    header.textContent = `${_selectedSuite}/${file.path}${caseName ? ' · ' + caseName : ''}`;

    const targetLine = highlightLine || (caseName
      ? (file.cases.find(c => c.name === caseName)?.line || null)
      : null);

    renderHighlightedCode(file.content, targetLine);
  } catch (err) {
    $('codeHeader').textContent = '加载失败';
    renderHighlightedCode('# ' + err.message, null);
  }
}

function renderHighlightedCode(content, targetLine) {
  const preEl = $('codeBox');
  const codeEl = $('codeContent');

  // 清除上次渲染残留，否则 line-numbers 插件不会重新生成行号
  preEl.querySelectorAll('.line-highlight').forEach(el => el.remove());
  preEl.querySelectorAll('.line-numbers-rows, .line-numbers-sizer').forEach(el => el.remove());
  preEl.classList.remove('line-numbers', 'linkable-line-numbers');
  preEl.removeAttribute('data-line');

  codeEl.textContent = content;
  codeEl.className = 'language-python line-numbers';

  if (targetLine) {
    preEl.setAttribute('data-line', String(targetLine));
  }

  if (window.Prism) {
    Prism.highlightElement(codeEl);
  }

  // line-highlight 插件在 complete hook 里异步执行，需延迟定位/滚动
  if (targetLine) {
    setTimeout(() => {
      if (Prism?.plugins?.lineHighlight) {
        Prism.plugins.lineHighlight.highlightLines(preEl);
      }
      const row = Prism?.plugins?.lineNumbers?.getLine(preEl, targetLine);
      const marker = preEl.querySelector('.line-highlight');
      (row || marker)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }, 30);
  }
}

function escapeAttr(str) {
  return String(str).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

async function selectRun(id) {
  _selectedRunId = id;
  renderHistory();
  if (_activePanel === 'results') await renderRunDetail();
  else switchPanel(_activePanel);
}

async function startTestRun(tests, label) {
  const config = getRunConfigFromUI();
  saveRunConfig(config);
  const body = { suite: _selectedSuite, config };
  if (tests && tests.length) body.tests = tests;

  const result = await api('POST', '/run', body);
  _selectedRunId = result.runId;
  toast(`已开始运行: ${label}`, 'success');
  await loadRuns();
  await loadStatus();
  switchPanel('results');
  await renderRunDetail();
}

async function runCheckedCases() {
  if (!_checkedTests.size) {
    toast('请先勾选要运行的用例', 'error');
    return;
  }
  try {
    await startTestRun([..._checkedTests], `${_checkedTests.size} 个用例`);
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function runSingleCase(filePath, caseName, event) {
  event.stopPropagation();
  try {
    await startTestRun([testCaseKey(filePath, caseName)], caseName);
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function runTestFile(filePath, event) {
  event.stopPropagation();
  try {
    await startTestRun([filePath], filePath);
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function runSelectedSuite() {
  try {
    if (_checkedTests.size > 0) {
      await runCheckedCases();
      return;
    }
    const suiteTotal = getSuiteTestCount();
    const label = suiteTotal > 0 ? `${_selectedSuite} (${suiteTotal} 个用例)` : _selectedSuite;
    await startTestRun(null, label);
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function runAllSuites() {
  try {
    const config = getRunConfigFromUI();
    saveRunConfig(config);
    const result = await api('POST', '/run', { suite: 'all', config });
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
  } else if (name === 'cases') {
    loadCases();
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
  applyRunConfigToUI(loadRunConfig());
  bindRunConfigEvents();
  try {
    await Promise.all([loadStatus(), loadSuites(), loadRuns()]);
    switchPanel('cases');
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
window.viewTestFile = viewTestFile;
window.toggleCaseFile = toggleCaseFile;
window.toggleCaseSelection = toggleCaseSelection;
window.toggleFileSelection = toggleFileSelection;
window.clearCaseSelection = clearCaseSelection;
window.runCheckedCases = runCheckedCases;
window.runSingleCase = runSingleCase;
window.runTestFile = runTestFile;
window.toggleRunConfig = toggleRunConfig;
window.resetRunConfig = resetRunConfig;
window.applyViewportPreset = applyViewportPreset;
window.onDeviceChange = onDeviceChange;

document.addEventListener('DOMContentLoaded', init);
