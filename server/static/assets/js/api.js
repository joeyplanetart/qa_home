/**
 * SQLite 后端 API 客户端
 * 内存缓存 + REST 同步
 */
const API_BASE = '/api';

let _cache = {
  memos: [],
  links: [],
  checklist: [],
  operations: [],
  snippets: [],
  tools: [],
  settings: { theme: 'light' },
  projectStats: {},
  githubTop10: { weekly: { items: [], fetchedAt: null }, monthly: { items: [], fetchedAt: null } },
  githubPeriod: 'weekly',
};

async function apiRequest(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(API_BASE + path, opts);
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

// ---------- Load ----------

async function loadAllData() {
  const [memos, links, checklist, operations, snippets, tools, settings] = await Promise.all([
    apiRequest('GET', '/memos'),
    apiRequest('GET', '/links'),
    apiRequest('GET', '/checklist'),
    apiRequest('GET', '/operations'),
    apiRequest('GET', '/snippets'),
    apiRequest('GET', '/tools'),
    apiRequest('GET', '/settings'),
  ]);
  _cache.memos = memos;
  _cache.links = links;
  _cache.checklist = checklist;
  _cache.operations = operations;
  _cache.snippets = snippets;
  _cache.tools = tools;
  _cache.settings = settings;

  try {
    _cache.projectStats = await apiRequest('GET', '/projects/stats');
  } catch (_) {
    _cache.projectStats = computeProjectStatsLocally();
  }
}

function computeProjectStatsLocally() {
  const stats = {};
  function bump(projectId, key) {
    if (projectId === null || projectId === undefined) return;
    const id = String(projectId);
    if (!stats[id]) stats[id] = { memos: 0, ops: 0, snippets: 0, tests: 0 };
    stats[id][key] += 1;
  }
  _cache.memos.forEach(m => bump(m.projectId, 'memos'));
  _cache.operations.forEach(o => bump(o.projectId, 'ops'));
  _cache.snippets.forEach(s => bump(s.projectId, 'snippets'));
  return stats;
}

async function refreshProjectStats() {
  try {
    _cache.projectStats = await apiRequest('GET', '/projects/stats');
  } catch (_) {
    _cache.projectStats = computeProjectStatsLocally();
  }
}

// ---------- Read ----------

function getMemos() { return _cache.memos; }
function getLinks() { return _cache.links; }
function getChecklist() { return _cache.checklist; }
function getOperations() { return _cache.operations; }
function getSnippets() { return _cache.snippets; }
function getTools() { return _cache.tools; }
function getSettings() { return _cache.settings; }
function getProjectStatsMap() {
  return _cache.projectStats || {};
}

// ---------- Settings ----------

async function saveSettings(settings) {
  const result = await apiRequest('PUT', '/settings', settings);
  _cache.settings = result;
  return result;
}

// ---------- Memos ----------

async function createMemo(data) {
  const item = await apiRequest('POST', '/memos', data);
  _cache.memos.unshift(item);
  await refreshProjectStats();
  return item;
}

async function updateMemo(id, data) {
  const item = await apiRequest('PUT', `/memos/${id}`, data);
  const idx = _cache.memos.findIndex(m => m.id === id);
  if (idx >= 0) _cache.memos[idx] = item;
  await refreshProjectStats();
  return item;
}

async function deleteMemoById(id) {
  await apiRequest('DELETE', `/memos/${id}`);
  _cache.memos = _cache.memos.filter(m => m.id !== id);
  await refreshProjectStats();
}

// ---------- Links ----------

async function createLink(data) {
  const item = await apiRequest('POST', '/links', data);
  _cache.links.push(item);
  return item;
}

async function updateLink(id, data) {
  const item = await apiRequest('PUT', `/links/${id}`, data);
  const idx = _cache.links.findIndex(l => l.id === id);
  if (idx >= 0) _cache.links[idx] = item;
  return item;
}

async function deleteLinkById(id) {
  await apiRequest('DELETE', `/links/${id}`);
  _cache.links = _cache.links.filter(l => l.id !== id);
}

// ---------- Checklist ----------

async function createChecklistItem(data) {
  const item = await apiRequest('POST', '/checklist', data);
  _cache.checklist.push(item);
  return item;
}

async function updateChecklistItem(id, data) {
  const item = await apiRequest('PUT', `/checklist/${id}`, data);
  const idx = _cache.checklist.findIndex(i => i.id === id);
  if (idx >= 0) _cache.checklist[idx] = item;
  return item;
}

async function deleteChecklistItemById(id) {
  await apiRequest('DELETE', `/checklist/${id}`);
  _cache.checklist = _cache.checklist.filter(i => i.id !== id);
}

async function resetChecklistAll() {
  const result = await apiRequest('POST', '/checklist/reset');
  _cache.checklist = result.items;
  return result.items;
}

// ---------- Operations ----------

async function createOperation(data) {
  const item = await apiRequest('POST', '/operations', data);
  _cache.operations.push(item);
  await refreshProjectStats();
  return item;
}

async function updateOperation(id, data) {
  const item = await apiRequest('PUT', `/operations/${id}`, data);
  const idx = _cache.operations.findIndex(o => o.id === id);
  if (idx >= 0) _cache.operations[idx] = item;
  await refreshProjectStats();
  return item;
}

async function deleteOperationById(id) {
  await apiRequest('DELETE', `/operations/${id}`);
  _cache.operations = _cache.operations.filter(o => o.id !== id);
  await refreshProjectStats();
}

// ---------- Snippets ----------

async function createSnippet(data) {
  const item = await apiRequest('POST', '/snippets', data);
  _cache.snippets.push(item);
  await refreshProjectStats();
  return item;
}

async function updateSnippet(id, data) {
  const item = await apiRequest('PUT', `/snippets/${id}`, data);
  const idx = _cache.snippets.findIndex(s => s.id === id);
  if (idx >= 0) _cache.snippets[idx] = item;
  await refreshProjectStats();
  return item;
}

async function deleteSnippetById(id) {
  await apiRequest('DELETE', `/snippets/${id}`);
  _cache.snippets = _cache.snippets.filter(s => s.id !== id);
  await refreshProjectStats();
}

// ---------- Tools ----------

async function createTool(data) {
  const item = await apiRequest('POST', '/tools', data);
  _cache.tools.push(item);
  return item;
}

async function updateTool(id, data) {
  const item = await apiRequest('PUT', `/tools/${id}`, data);
  const idx = _cache.tools.findIndex(t => t.id === id);
  if (idx >= 0) _cache.tools[idx] = item;
  return item;
}

async function deleteToolById(id) {
  await apiRequest('DELETE', `/tools/${id}`);
  _cache.tools = _cache.tools.filter(t => t.id !== id);
}

// ---------- GitHub Top10 ----------

function getGithubTop10(period) {
  return _cache.githubTop10[period] || { items: [], fetchedAt: null };
}

function getGithubPeriod() {
  return _cache.githubPeriod;
}

async function loadGithubTop10(period, refresh = false) {
  const data = await apiRequest('GET', `/github-top10?period=${period}${refresh ? '&refresh=true' : ''}`);
  _cache.githubTop10[period] = data;
  return data;
}

async function loadAllGithubTop10(refresh = false) {
  await Promise.all([
    loadGithubTop10('weekly', refresh),
    loadGithubTop10('monthly', refresh),
  ]);
}

async function refreshGithubTop10Api() {
  await apiRequest('POST', '/github-top10/refresh');
  await loadAllGithubTop10(false);
}

// ---------- Project Health ----------

let _healthCache = {};

function getExternalProjects() {
  return PROJECTS.filter(p => p.group !== 'planetart');
}

function getProjectHealth(projectId) {
  return _healthCache[String(projectId)] || null;
}

async function checkProjectsHealth(projects) {
  const items = projects.map(p => ({ id: p.id, url: getProjectUrl(p) }));
  if (!items.length) return {};
  const result = await apiRequest('POST', '/health-check', { items });
  _healthCache = { ..._healthCache, ...result };
  return result;
}
