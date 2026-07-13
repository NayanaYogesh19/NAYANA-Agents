// DM Audit Agent — frontend logic

const modeView = document.getElementById('modeView');
const formView = document.getElementById('formView');
const progressView = document.getElementById('progressView');
const resultsView = document.getElementById('resultsView');

const modeGrid = document.getElementById('modeGrid');
const continueFromModeBtn = document.getElementById('continueFromModeBtn');
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
const seoSection = document.getElementById('seoSection');
const ppcSection = document.getElementById('ppcSection');
const smmSection = document.getElementById('smmSection');
const sectionToggles = document.getElementById('sectionToggles');
const validationToast = document.getElementById('validationToast');
const validationToastText = document.getElementById('validationToastText');

// ---- Validation popup ----
let validationToastTimer = null;
function showValidationError(message, focusEl) {
  validationToastText.textContent = message;
  validationToast.classList.remove('hidden');
  validationToast.classList.add('shake');
  if (validationToastTimer) clearTimeout(validationToastTimer);
  validationToastTimer = setTimeout(() => {
    validationToast.classList.add('hidden');
    validationToast.classList.remove('shake');
  }, 4000);
  if (focusEl) {
    focusEl.focus();
    focusEl.classList.add('field-invalid');
    focusEl.addEventListener('input', function clearInvalid() {
      focusEl.classList.remove('field-invalid');
      focusEl.removeEventListener('input', clearInvalid);
    }, { once: true });
  }
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

function isValidUrl(value) {
  const v = value.trim();
  if (!v) return false;
  try {
    const withProtocol = /^https?:\/\//i.test(v) ? v : `https://${v}`;
    const parsed = new URL(withProtocol);
    return parsed.hostname.includes('.');
  } catch (_) {
    return false;
  }
}

function isValidUrlList(value) {
  const parts = value.split(',').map((p) => p.trim()).filter(Boolean);
  return parts.length > 0 && parts.every(isValidUrl);
}

// Returns null if the whole form is valid, or {message, field} on the first
// problem found (so we can stop at the first error like a real validation flow).
function validateAuditForm() {
  const requiredTextFields = [
    { name: 'Company Name', label: 'Company Name' },
    { name: 'Industry', label: 'Industry' },
  ];
  for (const { name, label } of requiredTextFields) {
    const el = auditForm.querySelector(`[name="${CSS.escape(name)}"]`);
    if (el && !el.value.trim()) {
      return { message: `${label} is required.`, field: el };
    }
  }

  const domainEl = auditForm.querySelector('[name="Domain/Website"]');
  if (!domainEl.value.trim()) {
    return { message: 'Domain / Website is required.', field: domainEl };
  }
  if (!isValidUrl(domainEl.value)) {
    return { message: 'Domain / Website must be a valid URL (e.g. https://example.com).', field: domainEl };
  }

  const competitorsEl = document.getElementById('competitorUrlsInput');
  if (!competitorsEl.value.trim()) {
    return { message: 'Competitor Company URLs is required.', field: competitorsEl };
  }
  if (!isValidUrlList(competitorsEl.value)) {
    return { message: 'Competitor Company URLs must be valid URLs, separated by commas (e.g. https://competitor1.com, https://competitor2.com).', field: competitorsEl };
  }

  const emailEl = auditForm.querySelector('[name="Your Email"]');
  if (!emailEl.value.trim()) {
    return { message: 'Your Email is required.', field: emailEl };
  }
  if (!isValidEmail(emailEl.value)) {
    return { message: 'Please enter a valid email address (e.g. you@company.com).', field: emailEl };
  }

  const metricInputs = auditForm.querySelectorAll('.metric-input');
  for (const input of metricInputs) {
    if (input.value.trim() === '') {
      const label = input.closest('.field')?.querySelector('label')?.textContent || 'This metric';
      return { message: `${label} is required.`, field: input };
    }
    if (Number.isNaN(Number(input.value))) {
      const label = input.closest('.field')?.querySelector('label')?.textContent || 'This metric';
      return { message: `${label} must be a valid number.`, field: input };
    }
  }

  return null;
}

const CATEGORY_DESCRIPTIONS = {
  seo: 'Current Digital State, Visibility Gap, Positioning, Technical Audit, SEO Benchmarks',
  ppc: 'Performance Marketing Audit, Conversion Funnel, PPC Benchmarks',
  smm: 'Social Media Audit, SMM Benchmarks',
};

// Mirrors the actual backend pipeline in app.py: research always runs
// first; SEO Audit only runs if "seo" is selected; Social Profile Discovery
// + SMM Gap Analysis only run if "smm" is selected; strategy/content/PDF
// always run last. Never shows a step for a category the user didn't pick.
function buildProgressSteps(categories) {
  const steps = [{ key: 'research', label: 'Market & Competitor Research' }];
  if (categories.includes('seo')) {
    steps.push({ key: 'seo', label: 'SEO Audit Analysis' });
  }
  if (categories.includes('smm')) {
    steps.push({ key: 'smmfetch', label: 'Social Profile Discovery & Metrics Fetch' });
    steps.push({ key: 'smm', label: 'Social Media Gap Analysis' });
  }
  steps.push({ key: 'strategy', label: 'Strategy Synthesis' });
  steps.push({ key: 'content', label: 'Report Content Generation' });
  steps.push({ key: 'pdf', label: 'PDF Rendering' });
  return steps;
}

let categoriesData = null;
let selectedCategories = [];
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

// ---- Load categories + field metadata ----
async function loadCategories() {
  const resp = await fetch('/api/categories');
  categoriesData = await resp.json();
  renderCategoryCards();
}

const CATEGORY_ICON_SVG = {
  seo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
  ppc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
  smm: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="22" height="22"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.6" y1="10.5" x2="15.4" y2="6.5"/><line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/></svg>',
};

function renderCategoryCards() {
  modeGrid.innerHTML = '';
  categoriesData.categories.forEach((cat) => {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'mode-card';
    card.dataset.category = cat.slug;
    card.innerHTML = `
      <div class="mode-card-check">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" width="13" height="13">
          <path d="M20 6L9 17l-5-5"/>
        </svg>
      </div>
      <div class="mode-card-icon icon-${cat.slug}">${CATEGORY_ICON_SVG[cat.slug] || ''}</div>
      <div class="mode-card-title">${cat.label}</div>
      <div class="mode-card-desc">${CATEGORY_DESCRIPTIONS[cat.slug] || ''}</div>
    `;
    card.addEventListener('click', () => toggleCategory(cat.slug));
    modeGrid.appendChild(card);
  });
}

function toggleCategory(slug) {
  const idx = selectedCategories.indexOf(slug);
  if (idx >= 0) selectedCategories.splice(idx, 1);
  else selectedCategories.push(slug);

  modeGrid.querySelectorAll('.mode-card').forEach((c) => {
    c.classList.toggle('selected', selectedCategories.includes(c.dataset.category));
  });
}

continueFromModeBtn.addEventListener('click', () => {
  if (selectedCategories.length === 0) {
    alert('Select at least one of SEO, Performance Marketing, or Social Media to continue.');
    return;
  }
  buildMetricsFields();
  buildSectionToggles();
  showView(formView);
});

backToModeBtn.addEventListener('click', () => showView(modeView));

// ---- Build metric input fields dynamically from /api/categories field metadata ----
function buildMetricFieldGroup(container, fieldLabels, namePrefix) {
  container.innerHTML = '';
  Object.entries(fieldLabels).forEach(([key, label]) => {
    const div = document.createElement('div');
    div.className = 'field';
    div.innerHTML = `
      <label>${label}</label>
      <input type="number" step="any" class="glass-input metric-input" data-metric-key="${key}" data-metric-group="${namePrefix}" placeholder="Enter value" required />
    `;
    container.appendChild(div);
  });
}

function buildMetricsFields() {
  if (selectedCategories.includes('seo')) {
    buildMetricFieldGroup(seoMetricsGrid, categoriesData.seo_fields, 'seo');
    seoSection.classList.remove('hidden');
  } else {
    seoMetricsGrid.innerHTML = '';
    seoSection.classList.add('hidden');
  }

  if (selectedCategories.includes('ppc')) {
    buildMetricFieldGroup(ppcMetricsGrid, categoriesData.ppc_fields, 'ppc');
    ppcSection.classList.remove('hidden');
  } else {
    ppcMetricsGrid.innerHTML = '';
    ppcSection.classList.add('hidden');
  }

  if (selectedCategories.includes('smm')) {
    smmSection.classList.remove('hidden');
  } else {
    smmSection.classList.add('hidden');
  }
}

// ---- Build slide-inclusion toggles ----
function buildSectionToggles() {
  sectionToggles.innerHTML = '';
  categoriesData.toggleable_slides.forEach((slide) => {
    const label = document.createElement('label');
    label.className = 'toggle-chip';
    label.innerHTML = `
      <input type="checkbox" checked data-section-slug="${slide.slug}" />
      <span>${slide.title}</span>
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
let elapsedTimer = null;
let dotsTimer = null;
let elapsedSeconds = 0;

function startStepAnimation() {
  // Rebuild the step list every run so it only shows steps relevant to the
  // categories actually selected for THIS run (not a stale list from a
  // previous selection).
  stepList.innerHTML = '';
  buildProgressSteps(selectedCategories).forEach((step) => {
    const li = document.createElement('li');
    li.dataset.step = step.key;
    li.innerHTML = `<span class="dot"></span> ${step.label}`;
    stepList.appendChild(li);
  });

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

  elapsedSeconds = 0;
  const elapsedEl = document.getElementById('elapsedTime');
  elapsedEl.textContent = '(0:00 elapsed)';
  elapsedTimer = setInterval(() => {
    elapsedSeconds += 1;
    const m = Math.floor(elapsedSeconds / 60);
    const s = String(elapsedSeconds % 60).padStart(2, '0');
    elapsedEl.textContent = `(${m}:${s} elapsed)`;
  }, 1000);

  const dotsEl = document.getElementById('progressDots');
  let dotCount = 1;
  dotsTimer = setInterval(() => {
    dotCount = (dotCount % 3) + 1;
    dotsEl.textContent = '.'.repeat(dotCount);
  }, 500);
}

function finishStepAnimation() {
  if (stepTimer) clearInterval(stepTimer);
  if (elapsedTimer) clearInterval(elapsedTimer);
  if (dotsTimer) clearInterval(dotsTimer);
  stepList.querySelectorAll('li').forEach((li) => { li.classList.remove('active'); li.classList.add('done'); });
}

// ---- Form submit ----
auditForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorBox.classList.add('hidden');
  errorBox.textContent = '';

  const validationError = validateAuditForm();
  if (validationError) {
    showValidationError(validationError.message, validationError.field);
    return;
  }

  const formData = new FormData(auditForm);
  const payload = {};
  formData.forEach((value, key) => { payload[key] = value; });

  payload['Categories'] = selectedCategories;
  payload['Excluded Sections'] = collectExcludedSections();
  payload['SEO Metrics'] = selectedCategories.includes('seo') ? collectMetrics('seo') : {};
  payload['PPC Metrics'] = selectedCategories.includes('ppc') ? collectMetrics('ppc') : {};
  // No "SMM Metrics" — always auto-fetched server-side when smm is selected.

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
        if (Array.isArray(errJson.detail)) {
          // FastAPI/Pydantic validation error shape: [{msg, loc, ...}, ...]
          detail = errJson.detail.map((d) => d.msg || JSON.stringify(d)).join(' ');
        } else if (typeof errJson.detail === 'string') {
          detail = errJson.detail;
        }
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
const CATEGORY_LABELS_DISPLAY = { seo: 'SEO', ppc: 'Performance Marketing', smm: 'Social Media' };

function renderResults(data) {
  document.getElementById('resultsTitle').textContent = `Audit Report Ready — ${data.company_name}`;
  const catLabel = data.categories.map((c) => CATEGORY_LABELS_DISPLAY[c] || c).join(' + ');
  document.getElementById('resultsSubtitle').textContent = `${catLabel} · ${data.slide_count} slides`;
  document.getElementById('resultsFilename').textContent = data.pdf_filename;
  document.getElementById('resultsIncluded').textContent = `Included: ${data.included_slides.join(', ')}`;
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
  selectedCategories = [];
  modeGrid.querySelectorAll('.mode-card').forEach((c) => c.classList.remove('selected'));
  showView(modeView);
});

loadCategories();
