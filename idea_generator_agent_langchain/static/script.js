/* ============================================================
   Idea Generator Agent — UI Logic
   ============================================================ */

// ---- Theme Toggle ----
const themeToggle = document.getElementById('themeToggle');
const iconSun     = document.getElementById('iconSun');
const iconMoon    = document.getElementById('iconMoon');

function applyTheme(dark) {
  if (dark) {
    document.documentElement.setAttribute('data-theme', 'dark');
    iconSun.style.display  = 'none';
    iconMoon.style.display = '';
  } else {
    document.documentElement.removeAttribute('data-theme');
    iconSun.style.display  = '';
    iconMoon.style.display = 'none';
  }
  localStorage.setItem('theme', dark ? 'dark' : 'light');
}

const savedTheme = localStorage.getItem('theme');
applyTheme(savedTheme === 'dark');

themeToggle.addEventListener('click', () => {
  applyTheme(document.documentElement.getAttribute('data-theme') !== 'dark');
});

// ---- Platform filter ----
let allIdeas = [];

document.getElementById('platformFilter').addEventListener('click', (e) => {
  const pill = e.target.closest('.filter-pill');
  if (!pill) return;
  document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
  pill.classList.add('active');
  renderIdeas(pill.dataset.filter);
});

// ---- Loading step animator ----
const steps = ['step1','step2','step3','step4','step5'];
let stepIndex = 0;
let stepTimer = null;

function startStepAnimation() {
  stepIndex = 0;
  steps.forEach(s => {
    const el = document.getElementById(s);
    el.classList.remove('active','done');
  });
  document.getElementById(steps[0]).classList.add('active');

  const messages = [
    'Fetching website content...',
    'Extracting keywords...',
    'Fetching Google Trends...',
    'Generating ideas with AI...',
    'Saving to Google Sheets...'
  ];

  stepTimer = setInterval(() => {
    if (stepIndex < steps.length - 1) {
      document.getElementById(steps[stepIndex]).classList.remove('active');
      document.getElementById(steps[stepIndex]).classList.add('done');
      stepIndex++;
      document.getElementById(steps[stepIndex]).classList.add('active');
      document.getElementById('loadingStep').textContent = messages[stepIndex];
    }
  }, 3000);
}

function stopStepAnimation() {
  clearInterval(stepTimer);
  steps.forEach(s => {
    const el = document.getElementById(s);
    el.classList.remove('active');
    el.classList.add('done');
  });
}

// ---- Show / hide helpers ----
function show(id)  { document.getElementById(id).style.display = ''; }
function hide(id)  { document.getElementById(id).style.display = 'none'; }

// ---- Platform badge class ----
function platformClass(platform) {
  const p = (platform || '').toLowerCase();
  if (p.includes('instagram')) return 'badge-platform-instagram';
  if (p.includes('linkedin'))  return 'badge-platform-linkedin';
  if (p.includes('ads') || p.includes('ad')) return 'badge-platform-ads';
  return 'badge-platform-any';
}

// ---- Content type badge class ----
function contentClass(type) {
  const t = (type || '').toLowerCase();
  if (t.includes('reel'))     return 'badge-content-reel';
  if (t.includes('carousel')) return 'badge-content-carousel';
  if (t.includes('post'))     return 'badge-content-post';
  if (t.includes('ad'))       return 'badge-content-ad';
  return 'badge-content-post';
}

// ---- Render Stats ----
function renderStats(ideas, sheetStatus, sheetError) {
  const platforms = {};
  ideas.forEach(i => {
    const p = i.platform || 'Other';
    platforms[p] = (platforms[p] || 0) + 1;
  });

  const colors = ['#7C3AED','#0EA5E9','#10B981','#F59E0B'];
  const entries = Object.entries(platforms);

  const statsRow = document.getElementById('statsRow');
  statsRow.innerHTML = '';

  // Total card
  const totalCard = document.createElement('div');
  totalCard.className = 'stat-card';
  totalCard.innerHTML = `
    <div class="stat-accent" style="background:#7C3AED"></div>
    <div class="stat-label">Total Ideas</div>
    <div class="stat-value">${ideas.length}</div>
    <div class="stat-meta">Generated successfully</div>
  `;
  statsRow.appendChild(totalCard);

  // Per-platform cards
  entries.forEach(([platform, count], i) => {
    const card = document.createElement('div');
    card.className = 'stat-card';
    card.innerHTML = `
      <div class="stat-accent" style="background:${colors[i % colors.length]}"></div>
      <div class="stat-label">${platform}</div>
      <div class="stat-value">${count}</div>
      <div class="stat-meta">ideas</div>
    `;
    statsRow.appendChild(card);
  });

  // Sheet status card
  const sheetOk = sheetStatus === 'success';
  const sheetCard = document.createElement('div');
  sheetCard.className = 'stat-card';
  sheetCard.innerHTML = `
    <div class="stat-accent" style="background:${sheetOk ? '#10B981' : '#F59E0B'}"></div>
    <div class="stat-label">Google Sheet</div>
    <div class="stat-value" style="font-size:1.1rem;padding-top:0.2rem">${sheetOk ? 'Saved ✓' : 'Skipped'}</div>
    <div class="stat-meta">${sheetOk ? 'All ideas written to sheet' : 'Sheet auth not configured'}</div>
  `;
  statsRow.appendChild(sheetCard);
}

// ---- Render Ideas ----
function renderIdeas(filter) {
  const grid = document.getElementById('ideasGrid');
  grid.innerHTML = '';

  const filtered = filter === 'all'
    ? allIdeas
    : allIdeas.filter(i => (i.platform || '').toLowerCase().includes(filter.toLowerCase()));

  filtered.forEach((idea, idx) => {
    const card = document.createElement('div');
    card.className = 'idea-card';
    card.style.animationDelay = `${idx * 35}ms`;

    card.innerHTML = `
      <div class="idea-card-top">
        <div class="idea-card-badges">
          <span class="badge ${platformClass(idea.platform)}">${idea.platform || ''}</span>
          <span class="badge ${contentClass(idea.content_type)}">${idea.content_type || ''}</span>
        </div>
        <span class="idea-id">#${idea.idea_id || (idx + 1)}</span>
      </div>

      <div class="idea-title">${escHtml(idea.idea_title || '')}</div>
      <div class="idea-description">${escHtml(idea.description || '')}</div>

      <div class="idea-divider"></div>

      <div class="idea-meta">
        <div class="idea-meta-row">
          <span class="idea-meta-label">Hook</span>
          <span class="idea-meta-value">${escHtml(idea.hook || '')}</span>
        </div>
        <div class="idea-meta-row">
          <span class="idea-meta-label">Audience</span>
          <span class="idea-meta-value">${escHtml(idea.target_audience || '')}</span>
        </div>
        <div class="idea-meta-row">
          <span class="idea-meta-label">Goal</span>
          <span class="idea-meta-value">${escHtml(idea.goal || '')}</span>
        </div>
      </div>

      <div class="idea-card-footer">
        <span class="cta-pill">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
          ${escHtml(idea.cta || '')}
        </span>
        <span class="trend-chip">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>
          </svg>
          ${escHtml(idea.trend_used || '')}
        </span>
      </div>
    `;

    grid.appendChild(card);
  });

  if (filtered.length === 0) {
    grid.innerHTML = `<div style="color:var(--text-muted);font-size:0.85rem;padding:1rem 0;grid-column:1/-1">No ideas found for this filter.</div>`;
  }
}

// ---- Escape HTML ----
function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

// ---- Form Submit ----
document.getElementById('ideaForm').addEventListener('submit', async (e) => {
  e.preventDefault();

  const websiteUrl = document.getElementById('websiteUrl').value.trim();
  const domain     = document.getElementById('domain').value.trim();
  const topic      = document.getElementById('topic').value.trim();
  const leadMagnet = document.getElementById('leadMagnet').value.trim() || 'none';

  // Reset UI
  hide('errorState');
  hide('resultsSection');
  show('loadingState');
  document.getElementById('submitBtn').disabled = true;
  startStepAnimation();

  try {
    const response = await fetch('/generate-ideas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        website_url: websiteUrl,
        domain:      domain,
        topic:       topic,
        lead_magnet: leadMagnet
      })
    });

    const data = await response.json();

    stopStepAnimation();
    hide('loadingState');

    if (!response.ok) {
      document.getElementById('errorMessage').textContent = data.detail || 'An unexpected error occurred.';
      show('errorState');
      return;
    }

    allIdeas = data.ideas || [];

    // Reset filter
    document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
    document.querySelector('.filter-pill[data-filter="all"]').classList.add('active');

    renderStats(allIdeas, data.sheet_status, data.sheet_error);
    renderIdeas('all');
    show('resultsSection');

    // Scroll to results
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    stopStepAnimation();
    hide('loadingState');
    document.getElementById('errorMessage').textContent = err.message || 'Network error. Please check your connection.';
    show('errorState');
  } finally {
    document.getElementById('submitBtn').disabled = false;
  }
});

// ---- Retry button ----
document.getElementById('retryBtn').addEventListener('click', () => {
  hide('errorState');
});
