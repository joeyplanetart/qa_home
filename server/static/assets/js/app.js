// ========================================
//  Utilities
// ========================================
function $(id) {
  return document.getElementById(id);
}

function toast(msg) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  $('toastContainer').appendChild(el);
  setTimeout(() => el.remove(), 2500);
}

function closeModal(id) {
  $(id).classList.remove('show');
}

function openModal(id) {
  $(id).classList.add('show');
}

document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', function (e) {
    if (e.target === this) closeModal(this.id);
  });
});

document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.show').forEach(o => o.classList.remove('show'));
    $('searchDropdown').classList.remove('show');
  }
});

// ========================================
//  State
// ========================================
let currentMemoFilter = 'all';
let currentToolFilter = 'all';
let currentGroupFilter = 'all';
let currentProjectFilter = null; // null = all projects
let projectSearchQuery = '';

// ========================================
//  Theme
// ========================================
function initTheme() {
  applyTheme(getSettings().theme || 'light');
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  $('themeBtn').textContent = theme === 'dark' ? '☀️' : '🌙';
}

async function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  const next = current === 'light' ? 'dark' : 'light';
  applyTheme(next);
  try {
    await saveSettings({ theme: next });
  } catch (e) {
    toast('⚠️ 主题保存失败');
  }
}

// ========================================
//  Project Helpers
// ========================================
function projectLabel(projectId) {
  if (projectId === null || projectId === undefined || projectId === '') return '通用';
  const p = getProjectById(projectId);
  return p ? p.short_name : `ID:${projectId}`;
}

function projectTagHtml(projectId) {
  const label = projectLabel(projectId);
  if (label === '通用') return '<span class="memo-project-tag">🌐 通用</span>';
  const p = getProjectById(projectId);
  const icon = p ? p.icon : '📦';
  return `<span class="memo-project-tag">${icon} ${escapeHTML(label)}</span>`;
}

function normalizeProjectId(id) {
  if (id === null || id === undefined || id === '') return null;
  const n = Number(id);
  return Number.isNaN(n) ? null : n;
}

function belongsToProject(itemProjectId, projectId) {
  const itemPid = normalizeProjectId(itemProjectId);
  const pid = normalizeProjectId(projectId);
  return itemPid !== null && pid !== null && itemPid === pid;
}

function matchesProjectFilter(item) {
  if (currentProjectFilter === null) return true;
  return belongsToProject(item.projectId, currentProjectFilter);
}

function getProjectStats(projectId) {
  const statsMap = getProjectStatsMap() || {};
  const stats = statsMap[String(projectId)] || { memos: 0, ops: 0, snippets: 0, tests: 0 };
  return {
    memos: stats.memos || 0,
    ops: stats.ops || 0,
    snippets: stats.snippets || 0,
    tests: stats.tests || 0,
    total: (stats.memos || 0) + (stats.ops || 0) + (stats.snippets || 0) + (stats.tests || 0),
  };
}

function setProjectFilter(projectId) {
  currentProjectFilter = projectId === 'all' || projectId === null ? null : Number(projectId);
  updateProjectFilterUI();
  renderAllContent();
  if (currentProjectFilter !== null) {
    const p = getProjectById(currentProjectFilter);
    toast(p ? `已筛选项目: ${p.short_name}` : '已清除项目筛选');
  }
}

function clearProjectFilter() {
  currentProjectFilter = null;
  updateProjectFilterUI();
  renderAllContent();
}

function updateProjectFilterUI() {
  const select = $('projectFilter');
  if (select) select.value = currentProjectFilter === null ? 'all' : String(currentProjectFilter);

  const badge = $('activeProjectBadge');
  if (badge) {
    if (currentProjectFilter === null) {
      badge.style.display = 'none';
    } else {
      const p = getProjectById(currentProjectFilter);
      badge.style.display = 'flex';
      badge.innerHTML = `
        <span>${p ? p.icon + ' ' + escapeHTML(p.short_name) : '项目筛选'}</span>
        <button onclick="clearProjectFilter()" title="清除筛选">✕</button>
      `;
    }
  }

  document.querySelectorAll('.project-card').forEach(card => {
    const id = Number(card.dataset.projectId);
    card.classList.toggle('selected', currentProjectFilter === id);
  });
}

function populateProjectSelects() {
  const options = '<option value="">🌐 通用 (跨项目)</option>' +
    PROJECT_GROUPS.map(g => {
      const projects = getProjectsByGroup(g.id);
      return `<optgroup label="${g.icon} ${g.name}">` +
        projects.map(p => `<option value="${p.id}">${p.icon} ${p.short_name} — ${p.domain}</option>`).join('') +
        '</optgroup>';
    }).join('');

  ['memoProject', 'opsProject', 'snippetProject'].forEach(id => {
    const el = $(id);
    if (el) el.innerHTML = options;
  });

  const headerSelect = $('projectFilter');
  if (headerSelect) {
    headerSelect.innerHTML = '<option value="all">📦 全部项目</option>' + options;
  }
}

// ========================================
//  Date/Time
// ========================================
function updateDateTime() {
  const now = new Date();
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  $('headerDate').textContent = `${days[now.getDay()]}, ${now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })}`;
}

// ========================================
//  Quick Links
// ========================================
function renderQuickLinks() {
  const links = getLinks();
  const container = $('quickLinksList');
  if (!links.length) {
    container.innerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:8px;">暂无快捷链接，点击 + 添加</div>';
    return;
  }
  container.innerHTML = links.sort((a, b) => a.sortOrder - b.sortOrder).map(link => `
    <div class="quick-link-item" onclick="window.open('${escapeHTML(link.url)}', '_blank')">
      <span class="quick-link-icon">${link.icon || '🔗'}</span>
      <span class="quick-link-name">${escapeHTML(link.name)}</span>
      <span class="quick-link-actions" onclick="event.stopPropagation()">
        <button class="btn-xs" onclick="editLink('${link.id}')" title="编辑">✎</button>
        <button class="btn-xs danger" onclick="removeLink('${link.id}')" title="删除">✕</button>
      </span>
    </div>
  `).join('');
}

function openLinkModal(id) {
  if (id) {
    const link = getLinks().find(l => l.id === id);
    if (!link) return;
    $('linkEditId').value = link.id;
    $('linkName').value = link.name;
    $('linkUrl').value = link.url;
    $('linkIcon').value = link.icon || '🔗';
    $('linkModalTitle').textContent = '编辑快捷链接';
  } else {
    $('linkEditId').value = '';
    $('linkName').value = '';
    $('linkUrl').value = '';
    $('linkIcon').value = '🔗';
    $('linkModalTitle').textContent = '新建快捷链接';
  }
  openModal('linkModalOverlay');
}

function editLink(id) { openLinkModal(id); }

async function saveLink() {
  const id = $('linkEditId').value;
  const name = $('linkName').value.trim();
  const url = $('linkUrl').value.trim();
  const icon = $('linkIcon').value.trim() || '🔗';
  if (!name || !url) { toast('⚠️ 名称和 URL 不能为空'); return; }
  const data = { name, url, icon, sortOrder: getLinks().length };
  try {
    if (id) {
      const existing = getLinks().find(l => l.id === id);
      await updateLink(id, { ...data, sortOrder: existing ? existing.sortOrder : 0 });
    } else {
      await createLink(data);
    }
    closeModal('linkModalOverlay');
    renderQuickLinks();
    toast(id ? '✅ 链接已更新' : '✅ 链接已添加');
  } catch (e) {
    toast('⚠️ 保存失败: ' + e.message);
  }
}

async function removeLink(id) {
  try {
    await deleteLinkById(id);
    renderQuickLinks();
    toast('🗑 链接已删除');
  } catch (e) {
    toast('⚠️ 删除失败: ' + e.message);
  }
}

// ========================================
//  Daily Checklist
// ========================================
function renderChecklist() {
  const items = getChecklist();
  const container = $('checklistItems');
  if (!items.length) {
    container.innerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:8px;">暂无任务，点击 + 添加</div>';
    $('checklistBar').style.width = '0%';
    return;
  }
  const done = items.filter(i => i.completed).length;
  $('checklistBar').style.width = Math.round((done / items.length) * 100) + '%';

  container.innerHTML = items.sort((a, b) => a.sortOrder - b.sortOrder).map(item => `
    <div class="checklist-item ${item.completed ? 'done' : ''}" onclick="toggleChecklistItem('${item.id}')">
      <div class="checklist-checkbox">${item.completed ? '✓' : ''}</div>
      <span class="checklist-text">${escapeHTML(item.text)}</span>
      <span style="margin-left:auto;display:flex;gap:2px;opacity:0.5">
        <button class="btn-xs" onclick="event.stopPropagation();editChecklistItem('${item.id}')" title="编辑">✎</button>
        <button class="btn-xs danger" onclick="event.stopPropagation();removeChecklistItem('${item.id}')" title="删除">✕</button>
      </span>
    </div>
  `).join('');
}

async function toggleChecklistItem(id) {
  const item = getChecklist().find(i => i.id === id);
  if (!item) return;
  const completed = !item.completed;
  try {
    await updateChecklistItem(id, {
      completed,
      completedAt: completed ? Date.now() : null,
    });
    renderChecklist();
  } catch (e) {
    toast('⚠️ 更新失败: ' + e.message);
  }
}

function openChecklistModal(id) {
  if (id) {
    const item = getChecklist().find(i => i.id === id);
    if (!item) return;
    $('checklistEditId').value = item.id;
    $('checklistText').value = item.text;
    $('checklistModalTitle').textContent = '编辑任务';
  } else {
    $('checklistEditId').value = '';
    $('checklistText').value = '';
    $('checklistModalTitle').textContent = '新建任务';
  }
  openModal('checklistModalOverlay');
}

function editChecklistItem(id) { openChecklistModal(id); }

async function saveChecklistItem() {
  const id = $('checklistEditId').value;
  const text = $('checklistText').value.trim();
  if (!text) { toast('⚠️ 任务内容不能为空'); return; }
  try {
    if (id) {
      await updateChecklistItem(id, { text });
    } else {
      await createChecklistItem({ text, sortOrder: getChecklist().length });
    }
    closeModal('checklistModalOverlay');
    renderChecklist();
    toast(id ? '✅ 任务已更新' : '✅ 任务已添加');
  } catch (e) {
    toast('⚠️ 保存失败: ' + e.message);
  }
}

async function removeChecklistItem(id) {
  try {
    await deleteChecklistItemById(id);
    renderChecklist();
  } catch (e) {
    toast('⚠️ 删除失败: ' + e.message);
  }
}

async function resetChecklist() {
  try {
    await resetChecklistAll();
    renderChecklist();
    toast('🔄 清单已重置');
  } catch (e) {
    toast('⚠️ 重置失败: ' + e.message);
  }
}

// ========================================
//  GitHub Top10
// ========================================
let githubPeriod = 'weekly';

function switchGithubPeriod(period) {
  githubPeriod = period;
  _cache.githubPeriod = period;
  document.querySelectorAll('.github-period-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.period === period);
  });
  renderGithubTop10();
}

async function refreshGithubTop10() {
  const btn = document.querySelector('.github-refresh-btn');
  if (btn) btn.textContent = '…';
  try {
    await refreshGithubTop10Api();
    renderGithubTop10();
    toast('✅ GitHub Top10 已更新');
  } catch (e) {
    toast('⚠️ 刷新失败: ' + e.message);
  } finally {
    if (btn) btn.textContent = '↻';
  }
}

function renderGithubTop10() {
  const list = $('githubTop10List');
  const meta = $('githubTop10Meta');
  if (!list) return;

  const data = getGithubTop10(githubPeriod);
  const items = data.items || [];

  if (meta) {
    meta.textContent = data.fetchedAt
      ? `更新于 ${timeAgo(data.fetchedAt)}`
      : '等待首次抓取…';
  }

  if (!items.length) {
    list.innerHTML = '<div style="font-size:12px;color:var(--text-muted);padding:8px;">暂无数据，点击 ↻ 刷新</div>';
    return;
  }

  list.innerHTML = `<div class="github-top10-list">${items.slice(0, 10).map(repo => `
    <a class="github-repo-item" href="${escapeHTML(repo.url)}" target="_blank" rel="noopener noreferrer" title="${escapeHTML((repo.description ? repo.description + ' — ' : '') + repo.fullName)}">
      <span class="github-repo-rank">${repo.rank}</span>
      <div class="github-repo-body">
        <div class="github-repo-name">${escapeHTML(repo.fullName)}</div>
        <div class="github-repo-meta">
          ${repo.language ? `<span>${escapeHTML(repo.language)}</span>` : ''}
          ${repo.stars ? `<span>⭐${formatStars(repo.stars)}</span>` : ''}
        </div>
      </div>
    </a>
  `).join('')}</div>`;
}

function formatStars(n) {
  if (n >= 1000) return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
  return String(n);
}

async function initGithubTop10() {
  try {
    await loadAllGithubTop10(false);
  } catch (e) {
    console.error('GitHub Top10 load failed:', e);
  }
  renderGithubTop10();
}

// ========================================
//  Projects Tab
// ========================================
function renderProjects() {
  const container = $('projectsContainer');
  if (!container) return;

  try {
    const query = projectSearchQuery.toLowerCase();

    let groups = PROJECT_GROUPS;
    if (currentGroupFilter !== 'all') {
      groups = groups.filter(g => g.id === currentGroupFilter);
    }

    let html = '';
    let hasResults = false;

    groups.forEach(group => {
      let projects = getProjectsByGroup(group.id);

      if (query) {
        projects = projects.filter(p =>
          p.short_name.toLowerCase().includes(query) ||
          p.domain.toLowerCase().includes(query) ||
          String(p.id).includes(query)
        );
      }

      if (!projects.length) return;
      hasResults = true;

      html += `
        <div class="project-group">
          <div class="project-group-header">
            <span class="project-group-icon">${group.icon}</span>
            <span class="project-group-title">${escapeHTML(group.name)}</span>
            <span class="project-group-desc">${escapeHTML(group.description)} · ${projects.length} 个项目</span>
          </div>
          <div class="project-grid">
            ${projects.map(p => renderProjectCard(p)).join('')}
          </div>
        </div>
      `;
    });

    if (!hasResults) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🔍</div>
          <div class="empty-state-text">未找到匹配的项目</div>
        </div>`;
      return;
    }

    container.innerHTML = html;
    updateProjectFilterUI();
  } catch (e) {
    console.error('renderProjects failed:', e);
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <div class="empty-state-text">项目列表加载失败，请刷新页面</div>
      </div>`;
  }
}

function renderProjectCard(p) {
  const stats = getProjectStats(p.id);
  const url = getProjectUrl(p);
  const selected = currentProjectFilter === p.id ? 'selected' : '';
  const healthHtml = p.group !== 'planetart' ? renderProjectHealth(p) : '';

  return `
    <div class="project-card ${selected}" data-project-id="${p.id}" onclick="selectProjectFromCard(${p.id})">
      <span class="project-env-badge ${p.env.toLowerCase()}">${p.env}</span>
      <div class="project-card-top">
        <div class="project-card-icon">${p.icon}</div>
        <div>
          <div class="project-card-name">${escapeHTML(p.short_name)}</div>
          <div class="project-card-id">ID: ${p.id}</div>
        </div>
      </div>
      <div class="project-card-domain" title="${escapeHTML(p.domain)}">
        <a href="${url}" target="_blank" onclick="event.stopPropagation()">${escapeHTML(p.domain)}</a>
      </div>
      ${healthHtml}
      <div class="project-card-stats">
        <span class="project-stat ${stats.memos ? 'has-items' : ''}">📝 ${stats.memos}</span>
        <span class="project-stat ${stats.ops ? 'has-items' : ''}">⚙️ ${stats.ops}</span>
        <span class="project-stat ${stats.snippets ? 'has-items' : ''}">💻 ${stats.snippets}</span>
        <span class="project-stat ${stats.tests ? 'has-items' : ''}" title="UI 自动化用例">🤖 ${stats.tests}</span>
      </div>
      <div class="project-card-actions" onclick="event.stopPropagation()">
        <button class="btn-sm primary" onclick="selectProjectAndTab(${p.id}, 'memos')">备忘录</button>
        <button class="btn-sm" onclick="selectProjectAndTab(${p.id}, 'operations')">流程</button>
        <button class="btn-sm" onclick="window.open('${url}', '_blank')">访问站点</button>
      </div>
    </div>
  `;
}

function selectProjectFromCard(projectId) {
  setProjectFilter(projectId);
}

function selectProjectAndTab(projectId, tab) {
  setProjectFilter(projectId);
  switchTab(tab);
}

function filterProjectGroups(groupId) {
  currentGroupFilter = groupId;
  document.querySelectorAll('.group-filter-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.group === groupId);
  });
  renderProjects();
}

function handleProjectSearch() {
  projectSearchQuery = $('projectSearch').value.trim();
  renderProjects();
}

function renderProjectHealth(p) {
  const h = getProjectHealth(p.id);
  if (!h || h.status === 'checking') {
    return '<div class="project-health checking"><span class="health-dot"></span>检查中...</div>';
  }
  if (h.status === 'healthy') {
    return `<div class="project-health healthy"><span class="health-dot"></span>正常 · HTTP ${h.statusCode} · ${h.latencyMs}ms</div>`;
  }
  const detail = h.error ? escapeHTML(h.error) : (h.statusCode ? `HTTP ${h.statusCode}` : '无法连接');
  return `<div class="project-health unhealthy"><span class="health-dot"></span>异常 · ${detail}</div>`;
}

let _healthCheckRunning = false;
let _healthCheckTimer = null;
const HEALTH_CHECK_INTERVAL_MS = 5 * 60 * 1000;

function isProjectsTabActive() {
  return document.getElementById('tab-projects')?.classList.contains('active');
}

async function refreshProjectHealth(silent = false) {
  const external = getExternalProjects();
  if (!external.length) {
    if (!silent) toast('没有需要检查的外部项目');
    return;
  }
  if (_healthCheckRunning) return;

  _healthCheckRunning = true;
  if (!silent) {
    external.forEach(p => {
      _healthCache[String(p.id)] = { status: 'checking' };
    });
    renderProjects();
  }

  const btn = document.querySelector('.health-refresh-btn');
  if (btn) btn.classList.add(silent ? 'auto-checking' : 'loading');

  try {
    await checkProjectsHealth(external);
    if (isProjectsTabActive()) renderProjects();
    if (!silent) {
      const healthy = external.filter(p => getProjectHealth(p.id)?.status === 'healthy').length;
      toast(`🩺 健康检查完成：${healthy}/${external.length} 正常`);
    }
  } catch (e) {
    if (!silent) {
      external.forEach(p => delete _healthCache[String(p.id)]);
      if (isProjectsTabActive()) renderProjects();
      toast('⚠️ 健康检查失败: ' + e.message);
    }
  } finally {
    _healthCheckRunning = false;
    if (btn) btn.classList.remove('loading', 'auto-checking');
  }
}

function startHealthCheckInterval() {
  if (_healthCheckTimer) clearInterval(_healthCheckTimer);
  _healthCheckTimer = setInterval(() => refreshProjectHealth(true), HEALTH_CHECK_INTERVAL_MS);
}

// ========================================
//  Memos
// ========================================
function renderMemos() {
  let memos = getMemos().filter(matchesProjectFilter);
  if (currentMemoFilter !== 'all') {
    memos = memos.filter(m => m.category === currentMemoFilter);
  }
  memos.sort((a, b) => {
    if (a.pinned && !b.pinned) return -1;
    if (!a.pinned && b.pinned) return 1;
    return b.updatedAt - a.updatedAt;
  });

  const grid = $('memoGrid');
  if (!memos.length) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1;">
        <div class="empty-state-icon">📝</div>
        <div class="empty-state-text">${currentProjectFilter !== null ? '该项目暂无备忘录' : '暂无备忘录，点击右上角 📝 创建'}</div>
      </div>`;
    return;
  }

  grid.innerHTML = memos.map(memo => `
    <div class="memo-card color-${memo.color} ${memo.pinned ? 'pinned' : ''}" onclick="editMemo('${memo.id}')">
      ${projectTagHtml(memo.projectId)}
      <div class="memo-title">${escapeHTML(memo.title)}</div>
      <div class="memo-content">${escapeHTML(memo.content)}</div>
      <div class="memo-footer">
        <span class="memo-category">${memo.category}</span>
        <span class="memo-actions" onclick="event.stopPropagation()">
          <button class="btn-xs" onclick="editMemo('${memo.id}')" title="编辑">✎</button>
          <button class="btn-xs danger" onclick="removeMemo('${memo.id}')" title="删除">✕</button>
        </span>
        <span style="font-size:10px">${timeAgo(memo.updatedAt)}</span>
      </div>
    </div>
  `).join('');
}

function filterMemos(cat) {
  currentMemoFilter = cat;
  document.querySelectorAll('.memo-filter-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.cat === cat);
  });
  renderMemos();
}

function openMemoModal(id) {
  if (id) {
    const memo = getMemos().find(m => m.id === id);
    if (!memo) return;
    $('memoEditId').value = memo.id;
    $('memoTitle').value = memo.title;
    $('memoContent').value = memo.content;
    $('memoCategory').value = memo.category;
    $('memoColor').value = memo.color;
    $('memoPinned').checked = memo.pinned;
    $('memoProject').value = memo.projectId !== null && memo.projectId !== undefined ? memo.projectId : '';
    $('memoModalTitle').textContent = '编辑备忘录';
    $('memoDeleteBtn').style.display = 'inline-block';
  } else {
    $('memoEditId').value = '';
    $('memoTitle').value = '';
    $('memoContent').value = '';
    $('memoCategory').value = 'general';
    $('memoColor').value = 'yellow';
    $('memoPinned').checked = false;
    $('memoProject').value = currentProjectFilter !== null ? currentProjectFilter : '';
    $('memoModalTitle').textContent = '新建备忘录';
    $('memoDeleteBtn').style.display = 'none';
  }
  openModal('memoModalOverlay');
}

function editMemo(id) { openMemoModal(id); }

async function saveMemo() {
  const id = $('memoEditId').value;
  const title = $('memoTitle').value.trim();
  const content = $('memoContent').value.trim();
  const category = $('memoCategory').value;
  const color = $('memoColor').value;
  const pinned = $('memoPinned').checked;
  const projectVal = $('memoProject').value;
  const projectId = projectVal === '' ? null : Number(projectVal);

  if (!title) { toast('⚠️ 标题不能为空'); return; }

  const data = { title, content, category, color, pinned, projectId };
  try {
    if (id) {
      await updateMemo(id, data);
    } else {
      await createMemo(data);
    }
    closeModal('memoModalOverlay');
    renderMemos();
    renderProjects();
    toast(id ? '✅ 备忘录已更新' : '✅ 备忘录已创建');
  } catch (e) {
    toast('⚠️ 保存失败: ' + e.message);
  }
}

async function deleteMemo() {
  const id = $('memoEditId').value;
  if (!id) return;
  try {
    await deleteMemoById(id);
    closeModal('memoModalOverlay');
    renderMemos();
    renderProjects();
    toast('🗑 备忘录已删除');
  } catch (e) {
    toast('⚠️ 删除失败: ' + e.message);
  }
}

async function removeMemo(id) {
  try {
    await deleteMemoById(id);
    renderMemos();
    renderProjects();
    toast('🗑 备忘录已删除');
  } catch (e) {
    toast('⚠️ 删除失败: ' + e.message);
  }
}

// ========================================
//  Operations
// ========================================
function renderOperations() {
  const ops = getOperations().filter(matchesProjectFilter);
  const container = $('opsList');

  if (!ops.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚙️</div>
        <div class="empty-state-text">${currentProjectFilter !== null ? '该项目暂无操作流程' : '暂无操作流程，点击右上角 ⚙️ 添加'}</div>
      </div>`;
    return;
  }

  container.innerHTML = ops.map(op => `
    <div class="ops-card" id="ops-${op.id}">
      <div class="ops-header" onclick="toggleOperation('${op.id}')">
        <div class="ops-title-wrap">
          <div class="ops-title">${escapeHTML(op.title)}</div>
          <div class="ops-meta">${projectTagHtml(op.projectId).replace(/<span /g, '<span style="font-size:11px;" ')} · ${op.steps.length} 步</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
          <button class="btn-xs" onclick="event.stopPropagation();editOperation('${op.id}')" title="编辑">✎</button>
          <button class="btn-xs danger" onclick="event.stopPropagation();removeOperation('${op.id}')" title="删除">✕</button>
          <span class="ops-arrow">▼</span>
        </div>
      </div>
      <div class="ops-body">
        <div class="ops-description">${escapeHTML(op.description || '暂无描述')}</div>
        ${op.steps.map((s, i) => `
          <div class="ops-step">
            <span class="ops-step-num">${i + 1}</span>
            <span>${escapeHTML(s)}</span>
          </div>
        `).join('')}
        ${op.tags && op.tags.length ? `
          <div class="ops-tags">
            ${op.tags.filter(t => t).map(t => `<span class="ops-tag">${escapeHTML(t.trim())}</span>`).join('')}
          </div>
        ` : ''}
      </div>
    </div>
  `).join('');
}

function toggleOperation(id) {
  const card = document.getElementById('ops-' + id);
  if (card) card.classList.toggle('open');
}

function openOpsModal(id) {
  if (id) {
    const op = getOperations().find(o => o.id === id);
    if (!op) return;
    $('opsEditId').value = op.id;
    $('opsTitle').value = op.title;
    $('opsDescription').value = op.description || '';
    $('opsSteps').value = op.steps.join('\n');
    $('opsTags').value = (op.tags || []).join(', ');
    $('opsProject').value = op.projectId !== null && op.projectId !== undefined ? op.projectId : '';
    $('opsModalTitle').textContent = '编辑操作流程';
    $('opsDeleteBtn').style.display = 'inline-block';
  } else {
    $('opsEditId').value = '';
    $('opsTitle').value = '';
    $('opsDescription').value = '';
    $('opsSteps').value = '';
    $('opsTags').value = '';
    $('opsProject').value = currentProjectFilter !== null ? currentProjectFilter : '';
    $('opsModalTitle').textContent = '新建操作流程';
    $('opsDeleteBtn').style.display = 'none';
  }
  openModal('opsModalOverlay');
}

function editOperation(id) { openOpsModal(id); }

async function saveOperation() {
  const id = $('opsEditId').value;
  const title = $('opsTitle').value.trim();
  const description = $('opsDescription').value.trim();
  const steps = $('opsSteps').value.split('\n').map(s => s.trim()).filter(s => s);
  const tags = $('opsTags').value.split(',').map(t => t.trim()).filter(t => t);
  const projectVal = $('opsProject').value;
  const projectId = projectVal === '' ? null : Number(projectVal);

  if (!title || !steps.length) { toast('⚠️ 标题和至少一个步骤不能为空'); return; }

  const data = { title, description, steps, tags, projectId };
  try {
    if (id) {
      await updateOperation(id, data);
    } else {
      await createOperation(data);
    }
    closeModal('opsModalOverlay');
    renderOperations();
    renderProjects();
    toast(id ? '✅ 流程已更新' : '✅ 流程已添加');
  } catch (e) {
    toast('⚠️ 保存失败: ' + e.message);
  }
}

async function deleteOperation() {
  const id = $('opsEditId').value;
  if (!id) return;
  try {
    await deleteOperationById(id);
    closeModal('opsModalOverlay');
    renderOperations();
    renderProjects();
    toast('🗑 流程已删除');
  } catch (e) {
    toast('⚠️ 删除失败: ' + e.message);
  }
}

async function removeOperation(id) {
  try {
    await deleteOperationById(id);
    renderOperations();
    renderProjects();
    toast('🗑 流程已删除');
  } catch (e) {
    toast('⚠️ 删除失败: ' + e.message);
  }
}

// ========================================
//  Snippets
// ========================================
function renderSnippets() {
  const snippets = getSnippets().filter(matchesProjectFilter);
  const container = $('snippetList');

  if (!snippets.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">💻</div>
        <div class="empty-state-text">${currentProjectFilter !== null ? '该项目暂无代码片段' : '暂无代码片段，点击右上角 💻 添加'}</div>
      </div>`;
    return;
  }

  container.innerHTML = snippets.map(s => `
    <div class="snippet-card">
      <div class="snippet-header">
        <div class="snippet-title-wrap">
          <div class="snippet-title">${escapeHTML(s.title)}</div>
          <div class="snippet-meta">${projectTagHtml(s.projectId).replace(/<span /g, '<span style="font-size:11px;" ')}</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-shrink:0;">
          <span class="snippet-lang">${escapeHTML(s.language)}</span>
          <button class="btn-xs" onclick="editSnippet('${s.id}')" title="编辑">✎</button>
          <button class="btn-xs danger" onclick="removeSnippet('${s.id}')" title="删除">✕</button>
        </div>
      </div>
      <div class="snippet-code-wrapper">
        <pre class="snippet-code">${escapeHTML(s.code)}</pre>
        <button class="btn-copy" onclick="copySnippet(this, '${escapeAttr(s.id)}')">📋 复制</button>
      </div>
      ${s.description ? `<div class="snippet-desc">${escapeHTML(s.description)}</div>` : ''}
      ${s.tags && s.tags.length ? `<div class="snippet-desc" style="padding-top:0;">${s.tags.filter(t => t).map(t => `<span class="ops-tag">${escapeHTML(t.trim())}</span>`).join(' ')}</div>` : ''}
    </div>
  `).join('');
}

function copySnippet(btn, id) {
  const snippet = getSnippets().find(s => s.id === id);
  if (!snippet) return;
  navigator.clipboard.writeText(snippet.code).then(() => {
    btn.textContent = '✅ 已复制';
    btn.classList.add('copied');
    setTimeout(() => { btn.textContent = '📋 复制'; btn.classList.remove('copied'); }, 2000);
  }).catch(() => toast('⚠️ 复制失败'));
}

function openSnippetModal(id) {
  if (id) {
    const s = getSnippets().find(sn => sn.id === id);
    if (!s) return;
    $('snippetEditId').value = s.id;
    $('snippetTitle').value = s.title;
    $('snippetLanguage').value = s.language;
    $('snippetCode').value = s.code;
    $('snippetDescription').value = s.description || '';
    $('snippetTags').value = (s.tags || []).join(', ');
    $('snippetProject').value = s.projectId !== null && s.projectId !== undefined ? s.projectId : '';
    $('snippetModalTitle').textContent = '编辑代码片段';
    $('snippetDeleteBtn').style.display = 'inline-block';
  } else {
    $('snippetEditId').value = '';
    $('snippetTitle').value = '';
    $('snippetLanguage').value = 'sql';
    $('snippetCode').value = '';
    $('snippetDescription').value = '';
    $('snippetTags').value = '';
    $('snippetProject').value = currentProjectFilter !== null ? currentProjectFilter : '';
    $('snippetModalTitle').textContent = '新建代码片段';
    $('snippetDeleteBtn').style.display = 'none';
  }
  openModal('snippetModalOverlay');
}

function editSnippet(id) { openSnippetModal(id); }

async function saveSnippet() {
  const id = $('snippetEditId').value;
  const title = $('snippetTitle').value.trim();
  const language = $('snippetLanguage').value;
  const code = $('snippetCode').value.trim();
  const description = $('snippetDescription').value.trim();
  const tags = $('snippetTags').value.split(',').map(t => t.trim()).filter(t => t);
  const projectVal = $('snippetProject').value;
  const projectId = projectVal === '' ? null : Number(projectVal);

  if (!title || !code) { toast('⚠️ 标题和代码不能为空'); return; }

  const data = { title, language, code, description, tags, projectId };
  try {
    if (id) {
      await updateSnippet(id, data);
    } else {
      await createSnippet(data);
    }
    closeModal('snippetModalOverlay');
    renderSnippets();
    renderProjects();
    toast(id ? '✅ 片段已更新' : '✅ 片段已添加');
  } catch (e) {
    toast('⚠️ 保存失败: ' + e.message);
  }
}

async function deleteSnippet() {
  const id = $('snippetEditId').value;
  if (!id) return;
  try {
    await deleteSnippetById(id);
    closeModal('snippetModalOverlay');
    renderSnippets();
    renderProjects();
    toast('🗑 片段已删除');
  } catch (e) {
    toast('⚠️ 删除失败: ' + e.message);
  }
}

async function removeSnippet(id) {
  try {
    await deleteSnippetById(id);
    renderSnippets();
    renderProjects();
    toast('🗑 片段已删除');
  } catch (e) {
    toast('⚠️ 删除失败: ' + e.message);
  }
}

// ========================================
//  Tools
// ========================================
const TOOL_CATEGORY_LABELS = {
  api: 'API',
  testing: '测试',
  devops: 'DevOps',
  design: '设计',
  utility: '实用',
  other: '其他',
};

function toolCategoryLabel(cat) {
  return TOOL_CATEGORY_LABELS[cat] || cat;
}

function filterTools(cat) {
  currentToolFilter = cat;
  document.querySelectorAll('[data-tool-cat]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.toolCat === cat);
  });
  renderTools();
}

function renderTools() {
  const tools = getTools()
    .filter(t => currentToolFilter === 'all' || t.category === currentToolFilter)
    .sort((a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name));
  const grid = $('toolsGrid');

  if (!tools.length) {
    grid.innerHTML = '<div class="empty-state">暂无工具链接，点击「+ 添加工具」开始收藏</div>';
    return;
  }

  grid.innerHTML = tools.map(tool => `
    <div class="tool-card" onclick="window.open('${escapeHTML(tool.url)}', '_blank')">
      <div class="tool-card-header">
        <span class="tool-card-icon">${tool.icon || '🛠️'}</span>
        <div class="tool-card-title-wrap">
          <div class="tool-card-name">${escapeHTML(tool.name)}</div>
          <div class="tool-card-url">${escapeHTML(tool.url)}</div>
          <span class="tool-card-cat">${toolCategoryLabel(tool.category)}</span>
        </div>
        <div class="tool-card-actions" onclick="event.stopPropagation()">
          <button class="btn-xs" onclick="editTool('${tool.id}')" title="编辑">✎</button>
          <button class="btn-xs danger" onclick="removeTool('${tool.id}')" title="删除">✕</button>
        </div>
      </div>
      ${tool.description ? `<div class="tool-card-desc">${escapeHTML(tool.description)}</div>` : ''}
    </div>
  `).join('');
}

function openToolModal(id) {
  if (id) {
    const tool = getTools().find(t => t.id === id);
    if (!tool) return;
    $('toolEditId').value = tool.id;
    $('toolName').value = tool.name;
    $('toolUrl').value = tool.url;
    $('toolIcon').value = tool.icon || '🛠️';
    $('toolCategory').value = tool.category || 'utility';
    $('toolDescription').value = tool.description || '';
    $('toolModalTitle').textContent = '编辑工具链接';
    $('toolDeleteBtn').style.display = '';
  } else {
    $('toolEditId').value = '';
    $('toolName').value = '';
    $('toolUrl').value = '';
    $('toolIcon').value = '🛠️';
    $('toolCategory').value = 'utility';
    $('toolDescription').value = '';
    $('toolModalTitle').textContent = '新建工具链接';
    $('toolDeleteBtn').style.display = 'none';
  }
  openModal('toolModalOverlay');
}

function editTool(id) { openToolModal(id); }

async function saveTool() {
  const id = $('toolEditId').value;
  const name = $('toolName').value.trim();
  const url = $('toolUrl').value.trim();
  const icon = $('toolIcon').value.trim() || '🛠️';
  const category = $('toolCategory').value;
  const description = $('toolDescription').value.trim();

  if (!name || !url) { toast('⚠️ 名称和 URL 不能为空'); return; }

  const data = { name, url, icon, category, description, sortOrder: getTools().length };
  try {
    if (id) {
      const existing = getTools().find(t => t.id === id);
      await updateTool(id, { ...data, sortOrder: existing ? existing.sortOrder : 0 });
    } else {
      await createTool(data);
    }
    closeModal('toolModalOverlay');
    renderTools();
    toast(id ? '✅ 工具已更新' : '✅ 工具已添加');
  } catch (e) {
    toast('⚠️ 保存失败: ' + e.message);
  }
}

async function deleteTool() {
  const id = $('toolEditId').value;
  if (!id) return;
  try {
    await deleteToolById(id);
    closeModal('toolModalOverlay');
    renderTools();
    toast('🗑 工具已删除');
  } catch (e) {
    toast('⚠️ 删除失败: ' + e.message);
  }
}

async function removeTool(id) {
  try {
    await deleteToolById(id);
    renderTools();
    toast('🗑 工具已删除');
  } catch (e) {
    toast('⚠️ 删除失败: ' + e.message);
  }
}

// ========================================
//  Global Search
// ========================================
let _searchResults = [];

function handleGlobalSearch() {
  const query = $('globalSearch').value.trim().toLowerCase();
  const dropdown = $('searchDropdown');

  if (!query) { dropdown.classList.remove('show'); return; }

  _searchResults = [];

  getMemos().forEach(m => {
    const pLabel = projectLabel(m.projectId).toLowerCase();
    if (m.title.toLowerCase().includes(query) || m.content.toLowerCase().includes(query) || pLabel.includes(query)) {
      _searchResults.push({ type: '备忘录', title: m.title, sub: projectLabel(m.projectId), target: m.id, kind: 'memo' });
    }
  });

  getOperations().forEach(o => {
    const pLabel = projectLabel(o.projectId).toLowerCase();
    if (o.title.toLowerCase().includes(query) || (o.description || '').toLowerCase().includes(query) ||
        o.steps.some(s => s.toLowerCase().includes(query)) || pLabel.includes(query)) {
      _searchResults.push({ type: '操作流程', title: o.title, sub: projectLabel(o.projectId), target: o.id, kind: 'ops' });
    }
  });

  getSnippets().forEach(s => {
    const pLabel = projectLabel(s.projectId).toLowerCase();
    if (s.title.toLowerCase().includes(query) || s.code.toLowerCase().includes(query) ||
        (s.description || '').toLowerCase().includes(query) || pLabel.includes(query)) {
      _searchResults.push({ type: '代码片段', title: s.title, sub: projectLabel(s.projectId), target: s.id, kind: 'snippet' });
    }
  });

  getTools().forEach(t => {
    const cat = toolCategoryLabel(t.category).toLowerCase();
    if (t.name.toLowerCase().includes(query) || t.url.toLowerCase().includes(query) ||
        (t.description || '').toLowerCase().includes(query) || cat.includes(query)) {
      _searchResults.push({ type: '工具', title: t.name, sub: t.description || t.url, target: t.id, kind: 'tool' });
    }
  });

  PROJECTS.forEach(p => {
    if (p.short_name.toLowerCase().includes(query) || p.domain.toLowerCase().includes(query)) {
      _searchResults.push({ type: '项目', title: p.short_name, sub: p.domain, target: p.id, kind: 'project' });
    }
  });

  if (!_searchResults.length) {
    dropdown.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-muted);">未找到结果</div>';
  } else {
    dropdown.innerHTML = _searchResults.slice(0, 15).map((r, i) => `
      <div class="search-result-item" data-search-index="${i}">
        <div class="search-result-type">${r.type}</div>
        <div class="search-result-title">${escapeHTML(r.title)}</div>
        <div class="search-result-sub">${escapeHTML(r.sub)}</div>
      </div>
    `).join('');
  }
  dropdown.classList.add('show');
}

function dispatchSearchResult(index) {
  $('searchDropdown').classList.remove('show');
  $('globalSearch').value = '';
  const r = _searchResults[index];
  if (!r) return;
  if (r.kind === 'memo') { switchTab('memos'); editMemo(r.target); }
  else if (r.kind === 'ops') { switchTab('operations'); setTimeout(() => toggleOperation(r.target), 100); }
  else if (r.kind === 'snippet') { switchTab('snippets'); }
  else if (r.kind === 'tool') { switchTab('tools'); editTool(r.target); }
  else if (r.kind === 'project') { switchTab('projects'); setProjectFilter(r.target); }
}

document.getElementById('searchDropdown').addEventListener('click', function (e) {
  const item = e.target.closest('.search-result-item');
  if (item && item.dataset.searchIndex !== undefined) {
    dispatchSearchResult(parseInt(item.dataset.searchIndex));
  }
});

document.addEventListener('click', function (e) {
  if (!e.target.closest('.search-wrapper')) {
    $('searchDropdown').classList.remove('show');
  }
});

// ========================================
//  Tabs
// ========================================
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.toggle('active', c.id === 'tab-' + tab));
  if (tab === 'projects' && !Object.keys(_healthCache).length) {
    refreshProjectHealth();
  }
}

function renderAllContent() {
  renderProjects();
  renderMemos();
  renderOperations();
  renderSnippets();
  renderTools();
}

// ========================================
//  Helpers
// ========================================
function escapeHTML(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeAttr(str) {
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

function timeAgo(ts) {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '刚刚';
  if (mins < 60) return mins + ' 分钟前';
  const hours = Math.floor(mins / 60);
  if (hours < 24) return hours + ' 小时前';
  const days = Math.floor(hours / 24);
  if (days < 30) return days + ' 天前';
  return new Date(ts).toLocaleDateString('zh-CN');
}

// ========================================
//  Init
// ========================================
async function init() {
  initTheme();
  updateDateTime();
  setInterval(updateDateTime, 60000);
  populateProjectSelects();

  try {
    await loadAllData();
  } catch (e) {
    toast('⚠️ 数据加载失败，请确认服务已启动');
    console.error(e);
  }

  initTheme();
  renderQuickLinks();
  renderChecklist();
  renderAllContent();
  updateProjectFilterUI();
  refreshProjectHealth();
  startHealthCheckInterval();
  initGithubTop10();
}

document.addEventListener('DOMContentLoaded', init);
