// DM Audit Agent — frontend logic

const modeView = document.getElementById('modeView');
const formView = document.getElementById('formView');
const progressView = document.getElementById('progressView');
const resultsView = document.getElementById('resultsView');

const modeGrid = document.getElementById('modeGrid');
const auditForm = document.getElementById('auditForm');
const submitBtn = document.getElementById('submitBtn');
const backToModeBtn = document.getElementById('backToModeBtn');
const stepList = document.getElementById('stepList');
const errorBox = document.getElementById('errorBox');
const startOverBtn = document.getElementById('startOverBtn');
const downloadPdfBtn = document.getElementById('downloadPdfBtn');
const themeToggle = document.getElementById('themeToggle');

const seoMetricsGrid = document.getElementById('seoMetricsGrid');
const ppcMetricsGrid = document.getElementById('ppcMetricsGrid');
const smmMetricsGrid = document.getElementById('smmMetricsGrid');
const ppcSection = document.getElementById('ppcSection');
const smmSection = document.getElementById('smmSection');
const sectionToggles = document.getElementById('sectionToggles');

let modesData = null;
let selectedMode = null;
let lastResult = null;

// ---- Theme ----
function applyStoredTheme() {
  const stored = localStorage.getItem('dm-audit-theme');
  if (stored) document.documentElement.setAttribute('data-theme', stored);
}
themeToggle.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('dm-audit-theme', next);
});
applyStoredTheme();

// ---- Views ----
function showView(view) {
  [modeView, formView, progressView, resultsView].forEach((v) => v.classList.add('hidden'));
  view.classList.remove('hidden');
}

// ---- Load modes + field metadata ----
async function loadModes() {
  const resp = await fetch('/api/modes');
  modesData = await resp.json();
  renderModeCards();
}

function renderModeCards() {
  modeGrid.innerHTML = '';
  Object.entries(modesData.modes).forEach(([key, meta]) => {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'mode-card';
    card.dataset.mode = key;
    card.innerHTML = `
      <div class="mode-card-title">${meta.label}</div>
      <div class="mode-card-count">${meta.slide_count} slides</div>
    `;
    card.addEventListener('click', () => selectMode(key));
    modeGrid.appendChild(card);
  });
}

function selectMode(key) {
  selectedMode = key;
  modeGrid.querySelectorAll('.mode-card').forEach((c) => c.classList.toggle('selected', c.dataset.mode === key));
  buildMetricsFields();
  buildSectionToggles();
  setTimeout(() => showView(formView), 150);
}

backToModeBtn.addEventListener('click', () => showView(modeView));

// ---- Build metric input fields dynamically from /api/modes field metadata ----
function buildMetricFieldGroup(container, fieldLabels, namePrefix) {
  container.innerHTML = '';
  Object.entries(fieldLabels).forEach(([key, label]) => {
    const div = document.createElement('div');
    div.className = 'field';
    div.innerHTML = `
      <label>${label}</label>
      <input type="number" step="any" class="glass-input metric-input" data-metric-key="${key}" data-metric-group="${namePrefix}" placeholder="Enter value" />
    `;
    container.appendChild(div);
  });
}

function buildMetricsFields() {
  buildMetricFieldGroup(seoMetricsGrid, modesData.seo_fields, 'seo');
  if (selectedMode === 'full') {
    buildMetricFieldGroup(ppcMetricsGrid, modesData.ppc_fields, 'ppc');
    buildMetricFieldGroup(smmMetricsGrid, modesData.smm_fields, 'smm');
    ppcSection.classList.remove('hidden');
    smmSection.classList.remove('hidden');
  } else {
    ppcSection.classList.add('hidden');
    smmSection.classList.add('hidden');
  }
}

// ---- Build section-inclusion toggles ----
function buildSectionToggles() {
  sectionToggles.innerHTML = '';
  const meta = modesData.modes[selectedMode];
  meta.toggleable_sections.forEach((section) => {
    const label = document.createElement('label');
    label.className = 'toggle-chip';
    label.innerHTML = `
      <input type="checkbox" checked data-section-slug="${section.slug}" />
      <span>${section.title}</span>
    `;
    sectionToggles.appendChild(label);
  });
}

function collectMetrics(group) {
  const out = {};
  document.querySelectorAll(`.metric-input[data-metric-group="${group}"]`).forEach((input) => {
    const key = input.dataset.metricKey;
    out[key] = input.value === '' ? null : parseFloat(input.value);
  });
  return out;
}

function collectExcludedSections() {
  const excluded = [];
  sectionToggles.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    if (!cb.checked) excluded.push(cb.dataset.sectionSlug);
  });
  return excluded;
}

// ---- Step progress simulation ----
let stepTimer = null;
function startStepAnimation() {
  let idx = 0;
  const items = stepList.querySelectorAll('li');
  items.forEach((li) => li.classList.remove('active', 'done'));

  function tick() {
    items.forEach((li, i) => {
      if (i < idx) { li.classList.add('done'); li.classList.remove('active'); }
      else if (i === idx) { li.classList.add('active'); li.classList.remove('done'); }
      else { li.classList.remove('active', 'done'); }
    });
    idx = Math.min(idx + 1, items.length - 1);
  }
  tick();
  stepTimer = setInterval(tick, 6000);
}

function finishStepAnimation() {
  if (stepTimer) clearInterval(stepTimer);
  stepList.querySelectorAll('li').forEach((li) => { li.classList.remove('active'); li.classList.add('done'); });
}

// ---- Form submit ----
auditForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorBox.classList.add('hidden');
  errorBox.textContent = '';

  const formData = new FormData(auditForm);
  const payload = {};
  formData.forEach((value, key) => { payload[key] = value; });

  payload['Audit Mode'] = selectedMode;
  payload['Excluded Sections'] = collectExcludedSections();
  payload['SEO Metrics'] = collectMetrics('seo');
  payload['PPC Metrics'] = selectedMode === 'full' ? collectMetrics('ppc') : {};
  payload['SMM Metrics'] = selectedMode === 'full' ? collectMetrics('smm') : {};

  submitBtn.disabled = true;
  showView(progressView);
  startStepAnimation();

  try {
    const resp = await fetch('/api/dm-audit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      let detail = `Request failed with status ${resp.status}`;
      try {
        const errJson = await resp.json();
        detail = errJson.detail || detail;
      } catch (_) { /* ignore parse error */ }
      throw new Error(detail);
    }

    const data = await resp.json();
    finishStepAnimation();
    lastResult = data;

    setTimeout(() => {
      renderResults(data);
      showView(resultsView);
    }, 400);
  } catch (err) {
    finishStepAnimation();
    errorBox.textContent = 'Error: ' + err.message;
    errorBox.classList.remove('hidden');
    showView(progressView);
  } finally {
    submitBtn.disabled = false;
  }
});

// ---- Results rendering ----
function renderResults(data) {
  document.getElementById('resultsTitle').textContent = `Audit Report Ready — ${data.company_name}`;
  document.getElementById('resultsSubtitle').textContent = `${data.audit_mode === 'full' ? 'SEO + Performance Marketing + Social Media' : 'SEO Only'} · ${data.included_sections.length} sections`;
  document.getElementById('resultsFilename').textContent = data.pdf_filename;
  document.getElementById('resultsIncluded').textContent = `Included: ${data.included_sections.join(', ')}`;
}

downloadPdfBtn.addEventListener('click', () => {
  if (!lastResult) return;
  const a = document.createElement('a');
  a.href = lastResult.download_url;
  a.download = lastResult.pdf_filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
});

startOverBtn.addEventListener('click', () => {
  auditForm.reset();
  lastResult = null;
  selectedMode = null;
  modeGrid.querySelectorAll('.mode-card').forEach((c) => c.classList.remove('selected'));
  showView(modeView);
});

loadModes();
