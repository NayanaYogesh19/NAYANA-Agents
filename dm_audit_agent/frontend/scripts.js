// DM Audit Agent — frontend logic

const modeView = document.getElementById('modeView');
const formView = document.getElementById('formView');
const categoryReviewView = document.getElementById('categoryReviewView');
const finalizeView = document.getElementById('finalizeView');
const progressView = document.getElementById('progressView');
const resultsView = document.getElementById('resultsView');

const modeGrid = document.getElementById('modeGrid');
const continueFromModeBtn = document.getElementById('continueFromModeBtn');
const companyInfoForm = document.getElementById('companyInfoForm');
const startReviewBtn = document.getElementById('startReviewBtn');
const skipToFinalizeBtn = document.getElementById('skipToFinalizeBtn');
const backToModeBtn = document.getElementById('backToModeBtn');
const stepList = document.getElementById('stepList');
const errorBox = document.getElementById('errorBox');
const startOverBtn = document.getElementById('startOverBtn');
const downloadPdfBtn = document.getElementById('downloadPdfBtn');
const themeToggle = document.getElementById('themeToggle');

const sectionToggles = document.getElementById('sectionToggles');
const validationToast = document.getElementById('validationToast');
const validationToastText = document.getElementById('validationToastText');

// Category review view elements
const categoryReviewStepLabel = document.getElementById('categoryReviewStepLabel');
const categoryReviewHeading = document.getElementById('categoryReviewHeading');
const categoryReviewDesc = document.getElementById('categoryReviewDesc');
const categoryMetricsPhase = document.getElementById('categoryMetricsPhase');
const categoryMetricsGrid = document.getElementById('categoryMetricsGrid');
const ppcAdLibraryFields = document.getElementById('ppcAdLibraryFields');
const googleAdsUrlInput = document.getElementById('googleAdsUrlInput');
const metaAdsUrlInput = document.getElementById('metaAdsUrlInput');
const linkedinCompanyNameInput = document.getElementById('linkedinCompanyNameInput');
const smmProfileFields = document.getElementById('smmProfileFields');
const instagramUrlInput = document.getElementById('instagramUrlInput');
const facebookUrlInput = document.getElementById('facebookUrlInput');
const linkedinProfileUrlInput = document.getElementById('linkedinProfileUrlInput');
const youtubeUrlInput = document.getElementById('youtubeUrlInput');
const runCategoryAnalysisBtn = document.getElementById('runCategoryAnalysisBtn');
const runCategoryAnalysisBtnLabel = document.getElementById('runCategoryAnalysisBtnLabel');
const categoryGeneratingPhase = document.getElementById('categoryGeneratingPhase');
const categoryProgressDots = document.getElementById('categoryProgressDots');
const categoryNarrativePhase = document.getElementById('categoryNarrativePhase');
const categoryNarrativeBox = document.getElementById('categoryNarrativeBox');
const categoryNarrativeTextarea = document.getElementById('categoryNarrativeTextarea');
const editNarrativeBtn = document.getElementById('editNarrativeBtn');
const editNarrativeBtnLabel = document.getElementById('editNarrativeBtnLabel');
const proceedReviewBtn = document.getElementById('proceedReviewBtn');
const proceedReviewBtnLabel = document.getElementById('proceedReviewBtnLabel');
const startOverFromReviewBtn = document.getElementById('startOverFromReviewBtn');
const categoryReviewErrorBox = document.getElementById('categoryReviewErrorBox');

// Finalize view elements
const backToReviewBtn = document.getElementById('backToReviewBtn');
const generatePdfBtn = document.getElementById('generatePdfBtn');

// ---- Validation popup ----
let validationToastTimer = null;
// Accepts either a single {message, field} or a batch {messages: string[],
// fields: Element[]} so every invalid field can be shown/marked at once
// instead of only the first one found.
function showValidationError(arg1, arg2) {
  const messages = Array.isArray(arg1) ? arg1 : arg1.messages || [arg1.message ?? arg1];
  const fields = arg2 !== undefined ? [arg2].filter(Boolean) : (arg1.fields || [arg1.field].filter(Boolean));

  validationToastText.textContent = messages.join(' ');
  validationToast.classList.remove('hidden');
  validationToast.classList.add('shake');
  if (validationToastTimer) clearTimeout(validationToastTimer);
  validationToastTimer = setTimeout(() => {
    validationToast.classList.add('hidden');
    validationToast.classList.remove('shake');
  }, 5000);

  fields.forEach((focusEl, i) => {
    if (!focusEl) return;
    if (i === 0) focusEl.focus();
    focusEl.classList.add('field-invalid');
    focusEl.addEventListener('input', function clearInvalid() {
      focusEl.classList.remove('field-invalid');
      focusEl.removeEventListener('input', clearInvalid);
    }, { once: true });
  });
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

// A real domain/hostname: letters/digits/hyphens in each label, separated by
// dots, ending in a 2+ letter TLD. No spaces or other characters allowed —
// checked BEFORE handing the string to `new URL()`, because browsers'
// URL parsers are lenient (they silently percent-encode spaces in the
// hostname instead of rejecting them), which would otherwise let a bogus
// value like "MTR foods.in" (encoded to "mtr%20foods.in") pass as valid.
const _HOSTNAME_RE = /^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))*\.[a-z]{2,}$/i;

function isValidUrl(value) {
  const v = value.trim();
  if (!v) return false;
  if (/\s/.test(v)) return false;
  try {
    const withProtocol = /^https?:\/\//i.test(v) ? v : `https://${v}`;
    const parsed = new URL(withProtocol);
    return _HOSTNAME_RE.test(parsed.hostname);
  } catch (_) {
    return false;
  }
}

function isValidUrlList(value) {
  const parts = value.split(',').map((p) => p.trim()).filter(Boolean);
  return parts.length > 0 && parts.every(isValidUrl);
}

// Validates the company-info fields (name/domain/industry/competitors/email)
// on the Step-2 form. Returns null if everything is valid, or
// {messages: string[], fields: Element[]} listing EVERY invalid field at
// once (not just the first found) — so an error on an earlier field never
// hides a real error on a later one.
function validateCompanyInfoFields() {
  const messages = [];
  const fields = [];

  const requiredTextFields = [
    { name: 'Company Name', label: 'Company Name' },
    { name: 'Industry', label: 'Industry' },
  ];
  for (const { name, label } of requiredTextFields) {
    const el = companyInfoForm.querySelector(`[name="${CSS.escape(name)}"]`);
    if (el && !el.value.trim()) {
      messages.push(`${label} is required.`);
      fields.push(el);
    }
  }

  const domainEl = companyInfoForm.querySelector('[name="Domain/Website"]');
  if (!domainEl.value.trim()) {
    messages.push('Domain / Website is required.');
    fields.push(domainEl);
  } else if (!isValidUrl(domainEl.value)) {
    messages.push('Domain / Website must be a valid URL (e.g. example.com or https://example.com).');
    fields.push(domainEl);
  }

  const competitorsEl = document.getElementById('competitorUrlsInput');
  if (!competitorsEl.value.trim()) {
    messages.push('Competitor Company URLs is required.');
    fields.push(competitorsEl);
  } else if (!isValidUrlList(competitorsEl.value)) {
    messages.push('Competitor Company URLs must be valid URLs, separated by commas (e.g. competitor1.com, competitor2.com).');
    fields.push(competitorsEl);
  }

  const emailEl = companyInfoForm.querySelector('[name="Your Email"]');
  if (!emailEl.value.trim()) {
    messages.push('Your Email is required.');
    fields.push(emailEl);
  } else if (!isValidEmail(emailEl.value)) {
    messages.push('Please enter a valid email address (e.g. you@company.com).');
    fields.push(emailEl);
  }

  return messages.length ? { messages, fields } : null;
}

// Validates the numeric metric inputs — only ever used for SEO now (PPC's
// numeric fields were removed; its inputs are the 3 ad-library fields below).
function validateCategoryMetricInputs() {
  const inputs = categoryMetricsGrid.querySelectorAll('.metric-input');
  for (const input of inputs) {
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

// Validates the PPC ad-transparency-library fields (Google/Meta URLs +
// LinkedIn company name) shown alongside the numeric PPC metrics.
function validatePpcAdLibraryFields() {
  if (!googleAdsUrlInput.value.trim()) {
    return { message: 'Google Ads Transparency URL is required.', field: googleAdsUrlInput };
  }
  if (!isValidUrl(googleAdsUrlInput.value)) {
    return { message: 'Google Ads Transparency URL must be a valid URL.', field: googleAdsUrlInput };
  }
  if (!metaAdsUrlInput.value.trim()) {
    return { message: 'Meta Ads Library URL is required.', field: metaAdsUrlInput };
  }
  if (!isValidUrl(metaAdsUrlInput.value)) {
    return { message: 'Meta Ads Library URL must be a valid URL.', field: metaAdsUrlInput };
  }
  if (!linkedinCompanyNameInput.value.trim()) {
    return { message: 'LinkedIn Company Name is required.', field: linkedinCompanyNameInput };
  }
  return null;
}

// Validates the SMM direct social-profile URL fields (replaces automatic
// Tavily-based profile discovery — the user now supplies the real URLs).
function validateSmmProfileFields() {
  const fields = [
    { el: instagramUrlInput, label: 'Instagram Profile URL' },
    { el: facebookUrlInput, label: 'Facebook Page URL' },
    { el: linkedinProfileUrlInput, label: 'LinkedIn Company Page URL' },
    { el: youtubeUrlInput, label: 'YouTube Channel URL' },
  ];
  for (const { el, label } of fields) {
    if (!el.value.trim()) {
      return { message: `${label} is required.`, field: el };
    }
    if (!isValidUrl(el.value)) {
      return { message: `${label} must be a valid URL.`, field: el };
    }
  }
  return null;
}

const CATEGORY_DESCRIPTIONS = {
  seo: 'Current Digital State, Visibility Gap, Positioning, Technical Audit, SEO Benchmarks',
  ppc: 'Performance Marketing Audit, Conversion Funnel, PPC Benchmarks',
  smm: 'Social Media Audit, SMM Benchmarks',
};

const CATEGORY_LABELS_DISPLAY = { seo: 'SEO', ppc: 'Performance Marketing', smm: 'Social Media' };

// Only the finalize call (Strategy -> Content Generation -> PDF) happens
// after this point — research/seo/smm analysis already ran per-category
// during review, so the finalize spinner only lists what's left.
function buildFinalizeProgressSteps() {
  return [
    { key: 'strategy', label: 'Strategy Synthesis' },
    { key: 'content', label: 'Report Content Generation' },
    { key: 'pdf', label: 'PDF Rendering' },
  ];
}

let categoriesData = null;
let selectedCategories = [];
let lastResult = null;

// ---- Phased review flow state ----
let runId = null;
let pendingCategories = [];
let currentReviewCategory = null;
let lastCategoryResponse = null;

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
  [modeView, formView, categoryReviewView, finalizeView, progressView, resultsView].forEach((v) => v.classList.add('hidden'));
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

// ---- Build slide-inclusion toggles ----
function buildSectionToggles(toggleableSlides) {
  sectionToggles.innerHTML = '';
  toggleableSlides.forEach((slide) => {
    const label = document.createElement('label');
    label.className = 'toggle-chip';
    label.innerHTML = `
      <input type="checkbox" checked data-section-slug="${slide.slug}" />
      <span>${slide.title}</span>
    `;
    sectionToggles.appendChild(label);
  });
}

function collectMetrics(container) {
  const out = {};
  container.querySelectorAll('.metric-input').forEach((input) => {
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

// ---- Step progress simulation (finalize call only) ----
let stepTimer = null;
let elapsedTimer = null;
let dotsTimer = null;
let elapsedSeconds = 0;

function startStepAnimation() {
  stepList.innerHTML = '';
  buildFinalizeProgressSteps().forEach((step) => {
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
  stepTimer = setInterval(tick, 4000);

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

async function parseErrorDetail(resp) {
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
  return detail;
}

// ---- Phase 1: Start the run ----
companyInfoForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const validationError = validateCompanyInfoFields();
  if (validationError) {
    showValidationError(validationError);
    return;
  }

  const formData = new FormData(companyInfoForm);
  const payload = {};
  formData.forEach((value, key) => { payload[key] = value; });
  payload['Categories'] = selectedCategories;

  startReviewBtn.disabled = true;
  try {
    const resp = await fetch('/api/dm-audit/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await parseErrorDetail(resp));

    const data = await resp.json();
    runId = data.run_id;
    pendingCategories = selectedCategories.slice();
    currentReviewCategory = data.current_category;
    showCategoryReview(currentReviewCategory);
    showView(categoryReviewView);
  } catch (err) {
    showValidationError({ messages: ['Error: ' + err.message], fields: [] });
  } finally {
    startReviewBtn.disabled = false;
  }
});

// Testing-only shortcut: jump straight to the Finalize screen without
// starting a run or reviewing any category. Since there's no run_id yet in
// this path, the toggle list is fetched from the generic /api/categories
// endpoint (same "toggleable_slides" shape as finalize-options) instead of
// the run-scoped finalize-options endpoint. Clicking "Generate Audit
// Report" from here will still fail (no run_id, nothing reviewed) — this
// button only exists to preview the Finalize screen's layout/toggles.
skipToFinalizeBtn.addEventListener('click', async () => {
  skipToFinalizeBtn.disabled = true;
  try {
    const resp = await fetch('/api/categories');
    if (!resp.ok) throw new Error(await parseErrorDetail(resp));
    const data = await resp.json();
    buildSectionToggles(data.toggleable_slides);
    showView(finalizeView);
  } catch (err) {
    showValidationError({ messages: ['Error: ' + err.message], fields: [] });
  } finally {
    skipToFinalizeBtn.disabled = false;
  }
});

// ---- Phase 2: Per-category review ----
const CATEGORY_REVIEW_META = {
  seo: { heading: 'Review SEO Analysis', desc: 'Enter your SEO metrics, then run the analysis to review before proceeding.' },
  ppc: { heading: 'Review Performance Marketing', desc: 'Enter your ad transparency library URLs, then run the analysis to review before proceeding.' },
  smm: { heading: 'Review Social Media Analysis', desc: 'Enter your social media profile URLs, then run the analysis to review before proceeding.' },
};

function showCategoryReview(category) {
  currentReviewCategory = category;
  categoryReviewErrorBox.classList.add('hidden');
  categoryReviewErrorBox.textContent = '';

  const meta = CATEGORY_REVIEW_META[category] || { heading: 'Review Analysis', desc: '' };
  categoryReviewHeading.textContent = meta.heading;
  categoryReviewDesc.textContent = meta.desc;

  categoryMetricsPhase.classList.add('hidden');
  categoryGeneratingPhase.classList.add('hidden');
  categoryNarrativePhase.classList.add('hidden');
  categoryMetricsGrid.innerHTML = '';

  ppcAdLibraryFields.classList.add('hidden');
  googleAdsUrlInput.value = '';
  metaAdsUrlInput.value = '';
  linkedinCompanyNameInput.value = '';

  smmProfileFields.classList.add('hidden');
  instagramUrlInput.value = '';
  facebookUrlInput.value = '';
  linkedinProfileUrlInput.value = '';
  youtubeUrlInput.value = '';

  runCategoryAnalysisBtnLabel.textContent = 'Run Analysis';

  if (category === 'seo') {
    buildMetricFieldGroup(categoryMetricsGrid, categoriesData.seo_fields, 'seo');
    categoryMetricsPhase.classList.remove('hidden');
  } else if (category === 'ppc') {
    ppcAdLibraryFields.classList.remove('hidden');
    runCategoryAnalysisBtnLabel.textContent = 'Submit and Analyze';
    categoryMetricsPhase.classList.remove('hidden');
  } else if (category === 'smm') {
    smmProfileFields.classList.remove('hidden');
    runCategoryAnalysisBtnLabel.textContent = 'Submit and Analyze';
    categoryMetricsPhase.classList.remove('hidden');
  }
}

runCategoryAnalysisBtn.addEventListener('click', () => runCategoryAnalysis());

async function runCategoryAnalysis() {
  if (currentReviewCategory === 'seo') {
    const metricError = validateCategoryMetricInputs();
    if (metricError) {
      showValidationError(metricError.message, metricError.field);
      return;
    }
  } else if (currentReviewCategory === 'ppc') {
    const adFieldError = validatePpcAdLibraryFields();
    if (adFieldError) {
      showValidationError(adFieldError.message, adFieldError.field);
      return;
    }
  } else if (currentReviewCategory === 'smm') {
    const profileFieldError = validateSmmProfileFields();
    if (profileFieldError) {
      showValidationError(profileFieldError.message, profileFieldError.field);
      return;
    }
  }

  categoryMetricsPhase.classList.add('hidden');
  categoryNarrativePhase.classList.add('hidden');
  categoryGeneratingPhase.classList.remove('hidden');

  let dotCount = 1;
  const dotsTimer = setInterval(() => {
    dotCount = (dotCount % 3) + 1;
    categoryProgressDots.textContent = '.'.repeat(dotCount);
  }, 500);

  const body = {};
  if (currentReviewCategory === 'seo') {
    body['SEO Metrics'] = collectMetrics(categoryMetricsGrid);
  } else if (currentReviewCategory === 'ppc') {
    body['Google Ads URL'] = googleAdsUrlInput.value.trim();
    body['Meta Ads URL'] = metaAdsUrlInput.value.trim();
    body['LinkedIn Company Name'] = linkedinCompanyNameInput.value.trim();
  } else if (currentReviewCategory === 'smm') {
    body['Instagram URL'] = instagramUrlInput.value.trim();
    body['Facebook URL'] = facebookUrlInput.value.trim();
    body['LinkedIn URL'] = linkedinProfileUrlInput.value.trim();
    body['YouTube URL'] = youtubeUrlInput.value.trim();
  }

  try {
    const resp = await fetch(`/api/dm-audit/${runId}/category/${currentReviewCategory}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(await parseErrorDetail(resp));

    const data = await resp.json();
    lastCategoryResponse = data;
    renderCategoryNarrative(data);
  } catch (err) {
    categoryGeneratingPhase.classList.add('hidden');
    categoryReviewErrorBox.textContent = 'Error: ' + err.message;
    categoryReviewErrorBox.classList.remove('hidden');
    // Every category now has its own input fields — re-show them (with
    // whatever the user already typed still filled in) so they can Retry.
    categoryMetricsPhase.classList.remove('hidden');
  } finally {
    clearInterval(dotsTimer);
  }
}

function formatAdSamples(label, totalAds, samples, capped) {
  if (totalAds === null || totalAds === undefined) {
    return `${label}: not fetched (no error, but no ads found or input missing).`;
  }
  let block = `${label}: ${totalAds} ad(s) found` + (capped ? ` (showing first ${totalAds} — this advertiser may have more)` : '');
  if (samples && samples.length) {
    block += '\n' + samples
      .map((ad, i) => {
        const lines = [`  ${i + 1}. ${ad.headline || ad.primary_text || '(no text)'} — ${ad.advertiser_name || ''}`.trimEnd()];
        const details = [];
        if (ad.ad_library_id) details.push(`Library ID: ${ad.ad_library_id}`);
        if (ad.platforms && ad.platforms.length) details.push(`Platforms: ${ad.platforms.join(', ')}`);
        if (ad.content_type) details.push(`Type: ${ad.content_type}`);
        if (ad.ad_status) details.push(`Status: ${ad.ad_status}`);
        if (ad.date_started) details.push(`Started: ${ad.date_started}`);
        if (ad.date_ended) details.push(`Ended: ${ad.date_ended}`);
        if (details.length) lines.push(`     ${details.join(' | ')}`);
        return lines.join('\n');
      })
      .join('\n');
  }
  return block;
}

// Whether the currently-shown narrative is directly editable text that
// should be saved server-side on Proceed (true for SEO/SMM narratives,
// false for PPC's metrics/ad-data confirmation, which isn't free-text).
let narrativeIsEditable = false;

function exitEditMode() {
  categoryNarrativeTextarea.classList.add('hidden');
  categoryNarrativeBox.classList.remove('hidden');
  editNarrativeBtnLabel.textContent = 'Edit';
}

function renderCategoryNarrative(data) {
  categoryGeneratingPhase.classList.add('hidden');
  categoryNarrativePhase.classList.remove('hidden');
  exitEditMode();

  let text;
  if (data.narrative) {
    text = data.narrative;
  } else if (data.ad_data) {
    const adData = data.ad_data;
    const monthNote = (platformKey) => {
      const n = adData[`${platformKey}_ads_started_this_month`];
      return n === null || n === undefined ? '' : ` (${n} started this month)`;
    };
    text = 'Fetched Ad Library Data:\n\n';
    text += formatAdSamples('Google Ads', adData.google_total_ads, adData.google_sample_ads, adData.google_capped) + monthNote('google') + '\n\n';
    text += formatAdSamples('Meta Ads', adData.meta_total_ads, adData.meta_sample_ads, adData.meta_capped) + monthNote('meta') + '\n\n';
    text += formatAdSamples('LinkedIn Ads', adData.linkedin_total_ads, adData.linkedin_sample_ads, adData.linkedin_capped) + monthNote('linkedin');
  } else {
    text = 'No analysis text was returned for this category.';
  }

  // Every category's review text is editable (SEO/SMM narratives, and now
  // PPC's formatted ad-data summary too) — edits are saved via the same
  // /narrative endpoint and override what flows into the final report.
  narrativeIsEditable = Boolean(data.narrative || data.ad_data);
  editNarrativeBtn.classList.toggle('hidden', !narrativeIsEditable);
  categoryNarrativeBox.textContent = text;
  categoryNarrativeTextarea.value = text;
  if (!data.narrative) data.narrative = text; // so Proceed's save-check picks it up uniformly

  proceedReviewBtnLabel.textContent = data.is_last ? 'Proceed to Finalize' : 'Proceed';
}

editNarrativeBtn.addEventListener('click', () => {
  const isEditing = !categoryNarrativeTextarea.classList.contains('hidden');
  if (isEditing) {
    // Save: reflect the edited text back into the read-only view and
    // into lastCategoryResponse so Proceed sends the right value.
    const edited = categoryNarrativeTextarea.value;
    categoryNarrativeBox.textContent = edited;
    if (lastCategoryResponse) lastCategoryResponse.narrative = edited;
    exitEditMode();
  } else {
    categoryNarrativeBox.classList.add('hidden');
    categoryNarrativeTextarea.classList.remove('hidden');
    editNarrativeBtnLabel.textContent = 'Save';
    categoryNarrativeTextarea.focus();
  }
});

proceedReviewBtn.addEventListener('click', async () => {
  const data = lastCategoryResponse;
  if (!data) return;

  // If currently mid-edit, save it first so the latest text is used.
  if (!categoryNarrativeTextarea.classList.contains('hidden')) {
    editNarrativeBtn.click();
  }

  if (narrativeIsEditable && data.narrative) {
    try {
      await fetch(`/api/dm-audit/${runId}/category/${currentReviewCategory}/narrative`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 'Narrative': data.narrative }),
      });
    } catch (err) {
      showValidationError({ messages: ['Error saving edited analysis: ' + err.message], fields: [] });
      return;
    }
  }

  if (data.is_last) {
    await enterFinalizeStep();
  } else {
    showCategoryReview(data.next_category);
  }
});

startOverFromReviewBtn.addEventListener('click', resetToStart);

// ---- Phase 3: Finalize ----
async function enterFinalizeStep() {
  try {
    const resp = await fetch(`/api/dm-audit/${runId}/finalize-options`);
    if (!resp.ok) throw new Error(await parseErrorDetail(resp));
    const data = await resp.json();
    buildSectionToggles(data.toggleable_slides);
    showView(finalizeView);
  } catch (err) {
    categoryReviewErrorBox.textContent = 'Error: ' + err.message;
    categoryReviewErrorBox.classList.remove('hidden');
  }
}

backToReviewBtn.addEventListener('click', () => {
  // Client-side only — the last-reviewed category's narrative is still
  // cached in lastCategoryResponse/the narrative box, no network call needed.
  showView(categoryReviewView);
});

generatePdfBtn.addEventListener('click', async () => {
  errorBox.classList.add('hidden');
  errorBox.textContent = '';

  const payload = { 'Excluded Sections': collectExcludedSections() };

  generatePdfBtn.disabled = true;
  showView(progressView);
  startStepAnimation();

  try {
    const resp = await fetch(`/api/dm-audit/${runId}/finalize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await parseErrorDetail(resp));

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
    generatePdfBtn.disabled = false;
  }
});

// ---- Results rendering ----
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

function resetToStart() {
  companyInfoForm.reset();
  lastResult = null;
  selectedCategories = [];
  runId = null;
  pendingCategories = [];
  currentReviewCategory = null;
  lastCategoryResponse = null;
  modeGrid.querySelectorAll('.mode-card').forEach((c) => c.classList.remove('selected'));
  showView(modeView);
}

startOverBtn.addEventListener('click', resetToStart);

loadCategories();
