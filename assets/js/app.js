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

function matchesProjectFilter(item) {
  if (currentProjectFilter === null) return true;
  return item.projectId === currentProjectFilter || item.projectId === null || item.projectId === undefined;
}

function getProjectStats(projectId) {
  const memos = getMemos().filter(m => m.projectId === projectId).length;
  const ops = getOperations().filter(o => o.projectId === projectId).length;
  const snippets = getSnippets().filter(s => s.projectId === projectId).length;
  return { memos, ops, snippets, total: memos + ops + snippets };
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
  const select = $('sidebarProjectFilter');
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

  const sidebarSelect = $('sidebarProjectFilter');
  if (sidebarSelect) {
    sidebarSelect.innerHTML = '<option value="all">全部项目</option>' + options;
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
  if (!confirm('确定删除此链接？')) return;
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
  if (!confirm('重置所有任务？将取消所有勾选。')) return;
  try {
    await resetChecklistAll();
    renderChecklist();
    toast('🔄 清单已重置');
  } catch (e) {
    toast('⚠️ 重置失败: ' + e.message);
  }
}

// ========================================
//  Projects Tab
// ========================================
function renderProjects() {
  const container = $('projectsContainer');
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
}

function renderProjectCard(p) {
  const stats = getProjectStats(p.id);
  const url = getProjectUrl(p);
  const selected = currentProjectFilter === p.id ? 'selected' : '';

  return `
    <div class="project-card ${selected}" data-project-id="${p.id}" onclick="selectProjectFromCard(${p.id})">
      <span class="project-env-badge ${p.env}">${p.env}</span>
      <div class="project-card-top">
        <div class="project-card-icon">${p.icon}</div>
        <div>
          <div class="project-card-name">${escapeHTML(p.short_name)}</div>
          <div class="project-card-id">ID: ${p.id}</div>
        </div>
      </div>
      <div class="project-card-domain">
        <a href="${url}" target="_blank" onclick="event.stopPropagation()">${escapeHTML(p.domain)}</a>
      </div>
      <div class="project-card-stats">
        <span class="project-stat ${stats.memos ? 'has-items' : ''}">📝 ${stats.memos}</span>
        <span class="project-stat ${stats.ops ? 'has-items' : ''}">⚙️ ${stats.ops}</span>
        <span class="project-stat ${stats.snippets ? 'has-items' : ''}">💻 ${stats.snippets}</span>
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

// ========================================
//  Memos
// ========================================
function renderFilterBanner(containerId, type) {
  if (currentProjectFilter === null) return '';
  const p = getProjectById(currentProjectFilter);
  if (!p) return '';
  return `
    <div class="filter-banner">
      <span>筛选中: ${p.icon} <strong>${escapeHTML(p.short_name)}</strong> 的${type}</span>
      <button onclick="clearProjectFilter()">清除筛选 ✕</button>
    </div>`;
}

function renderMemos() {
  const banner = renderFilterBanner('memoGrid', '备忘录');
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
    grid.innerHTML = banner + `
      <div class="empty-state" style="grid-column:1/-1;">
        <div class="empty-state-icon">📝</div>
        <div class="empty-state-text">${currentProjectFilter !== null ? '该项目暂无备忘录' : '暂无备忘录，点击右上角 📝 创建'}</div>
      </div>`;
    return;
  }

  grid.innerHTML = banner + memos.map(memo => `
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
  if (!id || !confirm('确定永久删除此备忘录？')) return;
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
  if (!confirm('确定删除此备忘录？')) return;
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
  const banner = renderFilterBanner('opsList', '操作流程');
  const ops = getOperations().filter(matchesProjectFilter);
  const container = $('opsList');

  if (!ops.length) {
    container.innerHTML = banner + `
      <div class="empty-state">
        <div class="empty-state-icon">⚙️</div>
        <div class="empty-state-text">${currentProjectFilter !== null ? '该项目暂无操作流程' : '暂无操作流程，点击右上角 ⚙️ 添加'}</div>
      </div>`;
    return;
  }

  container.innerHTML = banner + ops.map(op => `
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
  if (!id || !confirm('确定永久删除此流程？')) return;
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
  if (!confirm('确定删除此流程？')) return;
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
  const banner = renderFilterBanner('snippetList', '代码片段');
  const snippets = getSnippets().filter(matchesProjectFilter);
  const container = $('snippetList');

  if (!snippets.length) {
    container.innerHTML = banner + `
      <div class="empty-state">
        <div class="empty-state-icon">💻</div>
        <div class="empty-state-text">${currentProjectFilter !== null ? '该项目暂无代码片段' : '暂无代码片段，点击右上角 💻 添加'}</div>
      </div>`;
    return;
  }

  container.innerHTML = banner + snippets.map(s => `
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
  if (!id || !confirm('确定永久删除此片段？')) return;
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
  if (!confirm('确定删除此片段？')) return;
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
}

function renderAllContent() {
  renderProjects();
  renderMemos();
  renderOperations();
  renderSnippets();
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
    initTheme();
    renderQuickLinks();
    renderChecklist();
    renderAllContent();
    updateProjectFilterUI();
  } catch (e) {
    toast('⚠️ 数据加载失败，请确认服务已启动');
    console.error(e);
  }
}

document.addEventListener('DOMContentLoaded', init);
