'use strict';
/* OPS // TRACK — frontend
 * Talks to the Flask backend over a JSON REST API. No data lives in localStorage
 * anymore except the API connection settings (base URL + optional bearer token).
 */

// ---------------------------------------------------------------- API config
const CFG_KEY = 'opstrack-api-config-v1';

function loadApiConfig() {
  try {
    const saved = JSON.parse(localStorage.getItem(CFG_KEY) || '{}');
    return {
      base: saved.base || window.location.origin,
      token: saved.token || '',
    };
  } catch (e) {
    return { base: window.location.origin, token: '' };
  }
}

let apiConfig = loadApiConfig();

function saveApiConfig() {
  const base = document.getElementById('apiBaseInput').value.trim().replace(/\/$/, '');
  const token = document.getElementById('apiTokenInput').value.trim();
  apiConfig = { base: base || window.location.origin, token };
  localStorage.setItem(CFG_KEY, JSON.stringify(apiConfig));
  showToast('Connection settings saved');
  initApp();
}

async function api(path, opts = {}) {
  const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
  if (apiConfig.token) headers['Authorization'] = 'Bearer ' + apiConfig.token;
  const res = await fetch(apiConfig.base + path, Object.assign({}, opts, { headers }));
  if (!res.ok) {
    let msg = 'Request failed (' + res.status + ')';
    try { const j = await res.json(); if (j.error) msg = j.error; } catch (e) {}
    throw new Error(msg);
  }
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res.text();
}

// -------------------------------------------------------------------- utils

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function todayStr() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

let toastTimer = null;
function showToast(msg, isError) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.toggle('error', !!isError);
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 3200);
}

function handleError(err) {
  console.error(err);
  showToast(err.message || 'Something went wrong', true);
}

// --------------------------------------------------------------- tab switch

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('hidden');
}

const QUICK_PRESETS = [
  { label: '+ Mark DSA done', type: 'dsa', title: 'DSA Practice' },
  { label: '+ Mark Bug Bounty / Security done', type: 'security', title: 'Bug Bounty / Security' },
  { label: '+ Mark Adverk session', type: 'adverk', title: 'Adverk Session' },
  { label: '+ Mark AI Project done', type: 'ai', title: 'AI Project' },
  { label: '+ Mark HWork done', type: 'other', title: 'HWork' },
];

function renderQuickPresets() {
  const wrap = document.getElementById('quickPresets');
  wrap.innerHTML = QUICK_PRESETS.map((p, i) => `
    <button type="button" class="preset-btn p-${p.type}" onclick="applyPreset(${i})">${escapeHtml(p.label)}</button>
  `).join('');
}

function applyPreset(i) {
  const p = QUICK_PRESETS[i];
  document.getElementById('eventTitle').value = p.title;
  document.getElementById('eventType').value = p.type;
  const startEl = document.getElementById('eventStart');
  const endEl = document.getElementById('eventEnd');
  if (!startEl.value) startEl.value = '18:00';
  if (!endEl.value) endEl.value = '19:00';
  document.getElementById('eventTitle').focus();
}

function switchTab(tab, el) {
  document.querySelectorAll('.tab-content').forEach(e => e.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(e => e.classList.remove('active'));
  document.querySelectorAll('.sidebar-item').forEach(e => e.classList.remove('active'));

  document.getElementById(tab).classList.add('active');
  document.querySelectorAll(`[data-tab="${tab}"]`).forEach(e => e.classList.add('active'));
}

// ------------------------------------------------------------------- health

async function checkConnection() {
  const badge = document.getElementById('connBadge');
  try {
    await api('/api/health');
    badge.textContent = 'connected';
    badge.className = 'conn-badge ok';
    return true;
  } catch (e) {
    badge.textContent = 'offline';
    badge.className = 'conn-badge bad';
    return false;
  }
}

// -------------------------------------------------------------- calendar/events

let viewMonth = new Date().getMonth();
let viewYear = new Date().getFullYear();
let selectedDate = todayStr();
let eventsCache = [];

async function loadEvents() {
  eventsCache = await api('/api/events');
  renderCalendar();
  renderDayEvents();
  renderUpcoming();
  updateStats();
}

function renderCalendar() {
  const cal = document.getElementById('calendar');
  const label = document.getElementById('calMonth');
  const first = new Date(viewYear, viewMonth, 1);
  const last = new Date(viewYear, viewMonth + 1, 0);
  const daysInMonth = last.getDate();
  const startDay = first.getDay();

  label.textContent = first.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  cal.innerHTML = '';

  ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].forEach(d => {
    const dow = document.createElement('div');
    dow.className = 'cal-dow';
    dow.textContent = d;
    cal.appendChild(dow);
  });

  for (let i = 0; i < startDay; i++) {
    const empty = document.createElement('div');
    empty.className = 'cal-cell empty';
    cal.appendChild(empty);
  }

  const byDate = {};
  eventsCache.forEach(e => { (byDate[e.date] = byDate[e.date] || []).push(e); });

  const colors = { adverk: '--amber', dsa: '--cyan', security: '--red', ai: '--purple', other: '--muted' };

  for (let day = 1; day <= daysInMonth; day++) {
    const cell = document.createElement('div');
    cell.className = 'cal-cell';
    const dateStr = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

    if (dateStr === todayStr()) cell.classList.add('today');
    if (dateStr === selectedDate) cell.classList.add('selected');
    cell.onclick = () => { selectedDate = dateStr; renderCalendar(); renderDayEvents(); };

    const dayNum = document.createElement('div');
    dayNum.className = 'cal-daynum';
    dayNum.textContent = day;
    cell.appendChild(dayNum);

    const dots = document.createElement('div');
    dots.className = 'cal-dots';
    (byDate[dateStr] || []).slice(0, 3).forEach(e => {
      const dot = document.createElement('div');
      dot.className = 'cal-dot';
      dot.style.background = `var(${colors[e.type] || '--muted'})`;
      dots.appendChild(dot);
    });
    cell.appendChild(dots);
    cal.appendChild(cell);
  }
}

function prevMonth() { viewMonth--; if (viewMonth < 0) { viewMonth = 11; viewYear--; } renderCalendar(); }
function nextMonth() { viewMonth++; if (viewMonth > 11) { viewMonth = 0; viewYear++; } renderCalendar(); }

async function addEvent() {
  const title = document.getElementById('eventTitle').value.trim();
  const start = document.getElementById('eventStart').value;
  const end = document.getElementById('eventEnd').value;
  const type = document.getElementById('eventType').value;
  const date = document.getElementById('eventDate').value || todayStr();

  if (!title || !start || !end) { showToast('Please fill in title, start and end time', true); return; }
  if (end <= start) { showToast('End time must be after start time', true); return; }

  try {
    await api('/api/events', { method: 'POST', body: JSON.stringify({ title, start, end, type, date }) });
    document.getElementById('eventTitle').value = '';
    document.getElementById('eventStart').value = '';
    document.getElementById('eventEnd').value = '';
    selectedDate = date;
    await loadEvents();
    showToast('Event added');
  } catch (e) { handleError(e); }
}

async function deleteEvent(id) {
  try {
    await api('/api/events/' + id, { method: 'DELETE' });
    await loadEvents();
  } catch (e) { handleError(e); }
}

function eventItemHtml(e, showDate) {
  return `
    <div class="event-item">
      <div style="display: flex; align-items: center; gap: 8px; flex: 1; min-width:0;">
        <span class="event-tag tag-${escapeHtml(e.type)}">${escapeHtml((e.type || '').toUpperCase())}</span>
        <div style="flex: 1; min-width:0;">
          <div style="font-weight: 500; font-size: 12px; overflow-wrap:anywhere;">${escapeHtml(e.title)}</div>
          <div class="event-time">${showDate ? escapeHtml(e.date) + ' • ' : ''}${escapeHtml(e.start)}–${escapeHtml(e.end)}</div>
        </div>
      </div>
      <button class="event-del" onclick="deleteEvent(${e.id})">×</button>
    </div>`;
}

function renderDayEvents() {
  const title = document.getElementById('dayListTitle');
  title.textContent = selectedDate === todayStr() ? "Today's Events" : `Events — ${selectedDate}`;
  const container = document.getElementById('dayEvents');
  const events = eventsCache.filter(e => e.date === selectedDate).sort((a, b) => a.start.localeCompare(b.start));
  if (!events.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><div class="empty-text">No events on this day</div></div>';
    return;
  }
  container.innerHTML = events.map(e => eventItemHtml(e, false)).join('');
}

function renderUpcoming() {
  const container = document.getElementById('upcomingEvents');
  const today = todayStr();
  const upcoming = eventsCache
    .filter(e => e.date >= today)
    .sort((a, b) => (a.date !== b.date ? a.date.localeCompare(b.date) : a.start.localeCompare(b.start)))
    .slice(0, 5);
  if (!upcoming.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">🎯</div><div class="empty-text">No upcoming events</div></div>';
    return;
  }
  container.innerHTML = upcoming.map(e => eventItemHtml(e, true)).join('');
}

// ------------------------------------------------------------------ tracker

async function logAdverkSession() {
  const input = document.getElementById('adverkHourInput');
  const hours = parseFloat(input.value);
  if (!hours || hours <= 0) { showToast('Enter a valid number of hours', true); return; }
  try {
    await api('/api/logs', { method: 'POST', body: JSON.stringify({ type: 'adverk', value: hours }) });
    input.value = '';
    await loadTracker();
    await loadStats();
    showToast('Session logged');
  } catch (e) { handleError(e); }
}

async function logDSAProblem() {
  const input = document.getElementById('dsaProblemInput');
  const count = parseInt(input.value, 10);
  if (!count || count <= 0) { showToast('Enter a valid number of problems', true); return; }
  try {
    await api('/api/logs', { method: 'POST', body: JSON.stringify({ type: 'dsa', value: count }) });
    input.value = '';
    await loadTracker();
    await loadStats();
    showToast('Logged');
  } catch (e) { handleError(e); }
}

async function loadTracker() {
  const [summary, logs] = await Promise.all([api('/api/tracker/summary'), api('/api/logs')]);
  document.getElementById('adverkHours').textContent = summary.adverk_hours + 'h';
  document.getElementById('adverkDays').textContent = summary.adverk_days + 'd';
  document.getElementById('dsaCount').textContent = summary.dsa_solved;
  document.getElementById('dsaDays').textContent = summary.dsa_days + 'd';

  const history = document.getElementById('sessionHistory');
  if (!logs.length) {
    history.innerHTML = '<div class="empty-state"><div class="empty-icon">📝</div><div class="empty-text">No sessions logged yet</div></div>';
    return;
  }
  history.innerHTML = logs.slice(0, 10).map(l => `
    <div class="event-item">
      <div style="flex: 1;">
        <div style="font-weight: 500; font-size: 12px;">${l.type === 'adverk' ? '🎓 Adverk' : '💻 DSA'}</div>
        <div class="event-time">${escapeHtml(l.date)}</div>
      </div>
      <div style="font-weight: 600; color: var(--cyan);">${escapeHtml(l.value)}${l.type === 'adverk' ? 'h' : ''}</div>
    </div>`).join('');
}

// ----------------------------------------------------------------- security

async function addSecurityProject() {
  const title = document.getElementById('securityTitle').value.trim();
  const desc = document.getElementById('securityDesc').value.trim();
  const tech = document.getElementById('securityTech').value.trim();
  if (!title) { showToast('Project name is required', true); return; }
  try {
    await api('/api/security', { method: 'POST', body: JSON.stringify({ title, desc, tech }) });
    document.getElementById('securityTitle').value = '';
    document.getElementById('securityDesc').value = '';
    document.getElementById('securityTech').value = '';
    await loadSecurity();
    showToast('Project added');
  } catch (e) { handleError(e); }
}

async function cycleSecurityStatus(id, current) {
  const order = ['In Progress', 'Completed', 'Paused'];
  const next = order[(order.indexOf(current) + 1) % order.length];
  try {
    await api('/api/security/' + id, { method: 'PATCH', body: JSON.stringify({ status: next }) });
    await loadSecurity();
  } catch (e) { handleError(e); }
}

async function deleteSecurity(id) {
  try {
    await api('/api/security/' + id, { method: 'DELETE' });
    await loadSecurity();
  } catch (e) { handleError(e); }
}

async function loadSecurity() {
  const items = await api('/api/security');
  const list = document.getElementById('securityList');
  if (!items.length) {
    list.innerHTML = '<div class="empty-state"><div class="empty-icon">🔐</div><div class="empty-text">Add your first security project</div></div>';
    return;
  }
  list.innerHTML = items.map(p => `
    <div style="background: var(--panel-2); border: 1px solid var(--line); border-radius: 4px; padding: 12px;">
      <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px; gap:8px;">
        <div style="font-weight: 600; font-size: 12px; overflow-wrap:anywhere;">${escapeHtml(p.title)}</div>
        <div class="card-actions">
          <span class="event-tag tag-security" style="cursor:pointer;" title="Click to change status" onclick="cycleSecurityStatus(${p.id}, '${escapeHtml(p.status)}')">${escapeHtml(p.status)}</span>
          <button class="event-del" onclick="deleteSecurity(${p.id})">×</button>
        </div>
      </div>
      <div style="font-size: 11px; color: var(--muted); margin-bottom: 6px; overflow-wrap:anywhere;">${escapeHtml(p.desc)}</div>
      <div style="font-family: var(--font-mono); font-size: 10px; color: var(--cyan); overflow-wrap:anywhere;">${escapeHtml(p.tech)}</div>
    </div>`).join('');
}

async function addLearningItem() {
  const input = document.getElementById('learningItem');
  const topic = input.value.trim();
  if (!topic) return;
  try {
    await api('/api/learning', { method: 'POST', body: JSON.stringify({ topic }) });
    input.value = '';
    await loadLearning();
  } catch (e) { handleError(e); }
}

async function toggleLearning(id) {
  try {
    await api(`/api/learning/${id}/toggle`, { method: 'POST' });
    await loadLearning();
    await loadStats();
  } catch (e) { handleError(e); }
}

async function deleteLearningItem(id) {
  try {
    await api('/api/learning/' + id, { method: 'DELETE' });
    await loadLearning();
  } catch (e) { handleError(e); }
}

async function loadLearning() {
  const items = await api('/api/learning');
  const container = document.getElementById('learningProgress');
  if (!items.length) {
    container.innerHTML = '<div class="empty-state"><div class="empty-icon">📚</div><div class="empty-text">No learning items yet</div></div>';
    return;
  }
  container.innerHTML = items.map(l => `
    <div class="checkbox-item ${l.done ? 'done' : ''}" style="justify-content:space-between;">
      <label style="display:flex; align-items:center; gap:8px; flex:1; min-width:0; cursor:pointer;">
        <input type="checkbox" ${l.done ? 'checked' : ''} onchange="toggleLearning(${l.id})">
        <span style="overflow-wrap:anywhere;">${escapeHtml(l.topic)}</span>
      </label>
      <button class="event-del" onclick="deleteLearningItem(${l.id})">×</button>
    </div>`).join('');
}

// --------------------------------------------------------------- restart plan

let restartPlanData = null;

async function loadRestartPlan() {
  const [plan, progress] = await Promise.all([api('/api/restart/plan'), api('/api/restart/progress')]);
  restartPlanData = plan;
  renderRestartPlan(plan, progress);
}

function renderRestartPlan(plan, progress) {
  const container = document.getElementById('restartPlan');
  let totalDays = 0, totalDone = 0;

  container.innerHTML = plan.map(phase => {
    let phaseDays = 0, phaseDone = 0;
    const weeksHtml = phase.weeks.map((week, wi) => {
      let weekDone = 0;
      const daysHtml = week.days.map((d, di) => {
        const key = `${phase.key}-w${wi}-d${di}`;
        const done = !!progress[key];
        if (done) weekDone++;
        return `
          <div class="day-row ${done ? 'done' : ''}">
            <input type="checkbox" id="rk-${key}" ${done ? 'checked' : ''} onchange="toggleRestartItem('${key}')">
            <label for="rk-${key}"><span class="day-tag">DAY ${di + 1}</span>${escapeHtml(d)}</label>
          </div>`;
      }).join('');
      phaseDays += week.days.length;
      phaseDone += weekDone;
      return `
        <div class="week-block" data-wk="${phase.key}-w${wi}">
          <div class="week-head" onclick="toggleWeek('${phase.key}-w${wi}')">
            <b>${escapeHtml(week.name)}</b><span>${weekDone}/${week.days.length}</span>
          </div>
          <div class="week-body">${daysHtml}</div>
        </div>`;
    }).join('');

    totalDays += phaseDays; totalDone += phaseDone;
    const pct = phaseDays ? Math.round((phaseDone / phaseDays) * 100) : 0;

    return `
      <div style="background: var(--panel-2); border: 1px solid var(--line); border-radius: 4px; overflow: hidden;">
        <div class="collapsible" onclick="this.classList.toggle('active')">
          <div style="flex:1;">
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--muted); margin-bottom: 4px;">${escapeHtml(phase.name)} · ${escapeHtml(phase.range)}</div>
            <div class="progress-bar" style="width: 160px;"><div class="progress-fill" style="width: ${pct}%"></div></div>
          </div>
          <span style="font-family: var(--font-mono); font-size: 12px; color: var(--cyan);">${phaseDone}/${phaseDays}</span>
        </div>
        <div class="collapsible-content">${weeksHtml}</div>
      </div>`;
  }).join('');

  document.getElementById('restartOverallNum').textContent = `${totalDone}/${totalDays}`;
  document.getElementById('restartOverallFill').style.width = (totalDays ? Math.round((totalDone / totalDays) * 100) : 0) + '%';
}

function toggleWeek(key) {
  const el = document.querySelector(`[data-wk="${key}"]`);
  if (el) el.classList.toggle('open');
}

async function toggleRestartItem(key) {
  try {
    const progress = await api('/api/restart/progress');
    progress[key] = !progress[key];
    await api('/api/restart/toggle', { method: 'POST', body: JSON.stringify({ key }) });
    const fresh = await api('/api/restart/progress');
    renderRestartPlan(restartPlanData, fresh);
    await loadStats();
  } catch (e) { handleError(e); }
}

// ----------------------------------------------------------------- portfolio

async function addProject() {
  const name = document.getElementById('projectName').value.trim();
  const desc = document.getElementById('projectDesc').value.trim();
  const link = document.getElementById('projectLink').value.trim();
  const tech = document.getElementById('projectTech').value.trim();
  if (!name) { showToast('Project name is required', true); return; }
  try {
    await api('/api/projects', { method: 'POST', body: JSON.stringify({ name, desc, link, tech }) });
    document.getElementById('projectName').value = '';
    document.getElementById('projectDesc').value = '';
    document.getElementById('projectLink').value = '';
    document.getElementById('projectTech').value = '';
    await loadProjects();
    showToast('Project added');
  } catch (e) { handleError(e); }
}

async function deleteProject(id) {
  try {
    await api('/api/projects/' + id, { method: 'DELETE' });
    await loadProjects();
  } catch (e) { handleError(e); }
}

async function loadProjects() {
  const items = await api('/api/projects');
  const grid = document.getElementById('portfolioGrid');
  if (!items.length) {
    grid.innerHTML = '<div class="empty-state" style="grid-column: 1/-1;"><div class="empty-icon">🎯</div><div class="empty-text">Add your projects</div></div>';
    return;
  }
  grid.innerHTML = items.map(p => `
    <div style="background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px; padding: 16px;">
      <div style="display:flex; justify-content:space-between; gap:8px;">
        <div style="font-weight: 600; font-size: 13px; margin-bottom: 8px; overflow-wrap:anywhere;">${escapeHtml(p.name)}</div>
        <button class="event-del" onclick="deleteProject(${p.id})">×</button>
      </div>
      <div style="font-size: 12px; color: var(--muted); margin-bottom: 8px; line-height: 1.5; overflow-wrap:anywhere;">${escapeHtml(p.desc)}</div>
      <div style="font-family: var(--font-mono); font-size: 11px; color: var(--cyan); margin-bottom: 8px; overflow-wrap:anywhere;">${escapeHtml(p.tech)}</div>
      ${p.link ? `<a href="${escapeHtml(p.link)}" target="_blank" rel="noopener noreferrer" style="color: var(--cyan); text-decoration: none; font-size: 11px;">→ View</a>` : ''}
    </div>`).join('');
}

async function loadAbout() {
  const about = await api('/api/about');
  document.getElementById('fullName').value = about.name || '';
  document.getElementById('email').value = about.email || '';
  document.getElementById('bio').value = about.bio || '';
}

async function updateAbout() {
  const name = document.getElementById('fullName').value.trim();
  const email = document.getElementById('email').value.trim();
  const bio = document.getElementById('bio').value.trim();
  try {
    await api('/api/about', { method: 'PUT', body: JSON.stringify({ name, email, bio }) });
    showToast('Profile saved');
  } catch (e) { handleError(e); }
}

// ------------------------------------------------------------ weekly timetable

let timetableData = null;
let timetableSaveTimer = null;

async function loadTimetable() {
  timetableData = await api('/api/timetable');
  renderTimetable();
}

function renderTimetable() {
  const table = document.getElementById('timetableEl');
  const t = timetableData;
  const head = `<tr><th>Day</th>${t.slots.map((s, i) => `<th>${escapeHtml(s)}</th>`).join('')}</tr>`;
  const rows = t.days.map((d, di) => `
    <tr>
      <td class="day-col">${escapeHtml(d.day)}</td>
      ${d.cells.map((c, ci) => `<td class="cell" contenteditable="true"
          onblur="onTimetableCellEdit(${di}, ${ci}, this.textContent)">${escapeHtml(c)}</td>`).join('')}
    </tr>`).join('');
  table.innerHTML = head + rows;
}

function onTimetableCellEdit(dayIndex, cellIndex, value) {
  timetableData.days[dayIndex].cells[cellIndex] = value.trim().slice(0, 200);
  scheduleTimetableSave();
}

function scheduleTimetableSave() {
  clearTimeout(timetableSaveTimer);
  timetableSaveTimer = setTimeout(saveTimetable, 600);
}

async function saveTimetable() {
  try {
    await api('/api/timetable', { method: 'PUT', body: JSON.stringify(timetableData) });
  } catch (e) { handleError(e); }
}

function addTimetableSlot() {
  if (timetableData.slots.length >= 12) { showToast('Max 12 time slots', true); return; }
  const label = prompt('New time slot label (e.g. 04:10-05:10)');
  if (!label) return;
  timetableData.slots.push(label.slice(0, 40));
  timetableData.days.forEach(d => d.cells.push(''));
  renderTimetable();
  saveTimetable();
}

function addTimetableDay() {
  if (timetableData.days.length >= 8) { showToast('Max 8 day rows', true); return; }
  const label = prompt('New day row label (e.g. Sun)');
  if (!label) return;
  timetableData.days.push({ day: label.slice(0, 20), cells: timetableData.slots.map(() => '') });
  renderTimetable();
  saveTimetable();
}

// --------------------------------------------------------------------- stats

async function loadStats() {
  try {
    const s = await api('/api/stats');
    document.getElementById('todayCount').textContent = s.today_count;
    document.getElementById('sessionHours').textContent = s.session_hours + 'h';
    document.getElementById('streakNum').textContent = s.streak;
  } catch (e) { /* non-fatal */ }
}

async function updateStats() { await loadStats(); }

// ------------------------------------------------------------ backup/restore

async function backupData() {
  try {
    const res = await fetch(apiConfig.base + '/api/backup', {
      headers: apiConfig.token ? { 'Authorization': 'Bearer ' + apiConfig.token } : {},
    });
    if (!res.ok) throw new Error('Backup failed (' + res.status + ')');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `opstrack-backup-${todayStr()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Backup downloaded');
  } catch (e) { handleError(e); }
}

function restoreData(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      const parsed = JSON.parse(e.target.result);
      await api('/api/restore', { method: 'POST', body: JSON.stringify(parsed) });
      showToast('Backup restored');
      await initApp();
    } catch (err) {
      handleError(new Error('Invalid backup file or restore failed'));
    }
  };
  reader.readAsText(file);
  event.target.value = '';
}

async function clearAllData() {
  if (!confirm('Clear ALL data on the server? This cannot be undone!')) return;
  try {
    await api('/api/clear', { method: 'POST' });
    showToast('All data cleared');
    await initApp();
  } catch (e) { handleError(e); }
}

// ------------------------------------------------------------------ startup

async function initApp() {
  document.getElementById('apiBaseInput').value = apiConfig.base;
  document.getElementById('apiTokenInput').value = apiConfig.token;
  document.getElementById('eventDate').value = todayStr();
  renderQuickPresets();

  const ok = await checkConnection();
  if (!ok) {
    showToast('Cannot reach the API — check the URL in Settings', true);
    return;
  }

  try {
    await Promise.all([
      loadEvents(),
      loadTracker(),
      loadSecurity(),
      loadLearning(),
      loadRestartPlan(),
      loadProjects(),
      loadAbout(),
      loadStats(),
      loadTimetable(),
    ]);
  } catch (e) { handleError(e); }
}

document.addEventListener('DOMContentLoaded', initApp);
setInterval(() => { checkConnection(); loadStats(); }, 60000); // gentle 60s refresh, matches the old auto-refresh

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  });
}
