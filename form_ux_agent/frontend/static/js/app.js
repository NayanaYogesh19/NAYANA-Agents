/**
 * app.js — Form & UX Optimisation Agent Frontend
 * Trilliant Digital
 */

// ── State ─────────────────────────────────────────────────
let channel = 'website';
let mode = null;          // null until user explicitly clicks a mode card
let selectedPlatform = 'meta';
let accounts = [];
let selectedAccount = null;
let lastResult = null;
let selectedFormUrl = null;  // URL of the form the user picked from discovery

// ── Init ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadAccounts();
});

// ── Load Accounts from API ─────────────────────────────────
async function loadAccounts() {
  try {
    const res = await fetch('/api/accounts');
    const data = await res.json();
    accounts = data.accounts || [];
    const sel = document.getElementById('account-select');
    sel.innerHTML = '<option value="">— Select an account —</option>';
    accounts.forEach(acc => {
      const opt = document.createElement('option');
      opt.value = acc.account_name;
      opt.textContent = `${acc.account_name} (${acc.account_id})`;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error('Failed to load accounts:', e);
  }
}

function onAccountChange() {
  const sel = document.getElementById('account-select');
  const name = sel.value;
  selectedAccount = accounts.find(a => a.account_name === name) || null;

  const infoBox = document.getElementById('account-info');
  if (selectedAccount) {
    document.getElementById('info-id').textContent = selectedAccount.account_id;
    document.getElementById('info-ga4').textContent = selectedAccount.ga4_property_id || '—';
    document.getElementById('info-url').textContent = selectedAccount.website_url;
    document.getElementById('ga4-id').value = selectedAccount.ga4_property_id || '';
    infoBox.style.display = 'block';
  } else {
    infoBox.style.display = 'none';
  }

  resetDiscovery();
  hideResults();
}

// ── Channel Toggle ─────────────────────────────────────────
function setChannel(ch) {
  channel = ch;
  document.getElementById('btn-website').classList.toggle('active', ch === 'website');
  document.getElementById('btn-ads').classList.toggle('active', ch === 'ads');
  document.getElementById('path-website').style.display = ch === 'website' ? 'block' : 'none';
  document.getElementById('path-ads').style.display = ch === 'ads' ? 'block' : 'none';
  hideResults();
}

// ── Mode Toggle (Create / Optimise) ───────────────────────
function setMode(m) {
  mode = m;
  document.getElementById('mc-optimise').classList.toggle('active', m === 'optimise');
  document.getElementById('mc-create').classList.toggle('active', m === 'create');

  const inputsSection = document.getElementById('step-inputs');
  inputsSection.style.display = 'block';

  document.getElementById('form-discovery-panel').style.display = m === 'optimise' ? 'block' : 'none';
  document.getElementById('create-url-panel').style.display = m === 'create' ? 'block' : 'none';

  resetDiscovery();

  // Create mode: show Run button immediately; Optimise: only after form is selected
  const runBtn = document.getElementById('run-website');
  if (m === 'create') {
    runBtn.style.display = 'block';
    runBtn.innerHTML = '<i class="ti ti-wand"></i> Generate Form Blueprint';
    runBtn.onclick = runCreateForm;
  } else {
    runBtn.style.display = 'none';
    runBtn.innerHTML = '<i class="ti ti-player-play"></i> Run Form Analysis';
    runBtn.onclick = runWebsiteAnalysis;
  }

  if (m === 'optimise' && selectedAccount) {
    document.getElementById('scan-url').value = selectedAccount.website_url || '';
  }
  if (m === 'create' && selectedAccount) {
    document.getElementById('create-url').value = selectedAccount.website_url || '';
  }

  const note = document.getElementById('audience-note');
  note.style.display = 'flex';
  onAudienceChange();

  hideResults();
}

function resetDiscovery() {
  selectedFormUrl = null;
  const formUrlEl = document.getElementById('form-url');
  if (formUrlEl) formUrlEl.value = '';
  const discovered = document.getElementById('discovered-forms-section');
  if (discovered) discovered.style.display = 'none';
  const list = document.getElementById('discovered-forms-list');
  if (list) list.innerHTML = '';
  if (mode !== 'create') {
    document.getElementById('run-website').style.display = 'none';
  }
}

// ── Platform Toggle ────────────────────────────────────────
function setPlatform(p) {
  selectedPlatform = p;
  document.querySelectorAll('.platform-card:not(.disabled)').forEach(el => el.classList.remove('active'));
  const el = document.getElementById('p-' + p);
  if (el && !el.classList.contains('disabled')) el.classList.add('active');
}

// ── Audience Note ──────────────────────────────────────────
function onAudienceChange() {
  const val = document.getElementById('audience').value;
  const note = document.getElementById('audience-note');
  note.className = 'audience-note ' + (val === 'b2b' ? 'b2b-note' : 'b2c-note');
  note.innerHTML = val === 'b2b'
    ? '<i class="ti ti-info-circle"></i><span><strong>B2B mode:</strong> Max 5 fields · Higher-intent CTA rules · GDPR consent required</span>'
    : '<i class="ti ti-info-circle"></i><span><strong>B2C mode:</strong> Max 3 fields · Volume-optimised CTA rules · Pre-fill recommended</span>';
}

// ── Form Discovery (Optimise mode) ────────────────────────
async function discoverForms() {
  const scanUrl = document.getElementById('scan-url').value.trim();
  if (!scanUrl) return showError('Please enter a website URL to scan.');
  if (!selectedAccount) return showError('Please select an account first.');

  const btn = document.querySelector('.scan-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader"></i> Scanning…';

  try {
    const res = await fetch('/api/discover/forms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: scanUrl, account_name: selectedAccount.account_name }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Could not scan URL.');
    renderDiscoveredForms(data.forms || [], scanUrl);
  } catch (e) {
    showError(e.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-search"></i> Scan for Forms';
  }
}

function renderDiscoveredForms(forms, baseUrl) {
  const section = document.getElementById('discovered-forms-section');
  const list = document.getElementById('discovered-forms-list');
  list.innerHTML = '';

  if (!forms.length) {
    list.innerHTML = '<p style="color:#888;font-size:13px">No forms detected on this page. Try a different URL (e.g. /contact, /get-a-quote).</p>';
    section.style.display = 'block';
    return;
  }

  forms.forEach((form, i) => {
    const card = document.createElement('div');
    card.className = 'form-discovery-card';
    card.innerHTML = `
      <div class="fd-title">Form ${i + 1}${form.form_name ? ' — ' + form.form_name : ''}</div>
      <div class="fd-meta">${form.field_count} field${form.field_count !== 1 ? 's' : ''} · CTA: "${form.cta_text || 'N/A'}"</div>
      <div class="fd-fields">${(form.field_labels || []).slice(0, 5).join(' · ') || 'Fields detected'}</div>
      <div class="fd-url">${form.page_url || baseUrl}</div>
    `;
    card.onclick = () => selectDiscoveredForm(card, form.page_url || baseUrl, form);
    list.appendChild(card);
  });

  section.style.display = 'block';
}

function selectDiscoveredForm(card, url, form) {
  document.querySelectorAll('.form-discovery-card').forEach(c => c.classList.remove('selected'));
  card.classList.add('selected');
  selectedFormUrl = url;
  document.getElementById('form-url').value = url;
  const runBtn = document.getElementById('run-website');
  runBtn.style.display = 'block';
  runBtn.innerHTML = '<i class="ti ti-player-play"></i> Run Form Analysis';
  runBtn.onclick = runWebsiteAnalysis;
  runBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Run Website Analysis (optimise mode) ──────────────────
async function runWebsiteAnalysis() {
  const accountName = document.getElementById('account-select').value;
  const bizGoal = document.getElementById('biz-goal').value;
  const audience = document.getElementById('audience').value;
  const device = document.getElementById('device').value;
  const ga4Id = document.getElementById('ga4-id').value.trim();
  const description = document.getElementById('website-description').value.trim();

  if (!accountName) return showError('Please select an account.');
  if (!bizGoal) return showError('Please select a Business Goal.');
  if (!audience) return showError('Please select an Audience Type.');
  if (!device) return showError('Please select a Device Priority.');

  const formUrl = document.getElementById('form-url').value.trim();
  if (!formUrl) return showError('Please scan for forms and select one first.');

  showLoading('Running form analysis…', [
    '🔍 Validating account and URL…',
    '🕷️ Scraping website and detecting forms…',
    '✅ Running 8 UX rule checks…',
    '📊 Fetching analytics data…',
    '🤖 Running AI diagnosis…',
    '📄 Generating PDF report and UX table…',
  ]);

  try {
    const res = await fetch('/api/analyse/website', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account_name: accountName,
        form_url: formUrl,
        mode: 'optimise',
        business_goal: bizGoal,
        audience: audience,
        device_priority: device,
        ga4_property_id: ga4Id,
        user_description: description,
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Analysis failed.');

    lastResult = data;
    hideLoading();
    renderWebsiteResults(data);
  } catch (e) {
    hideLoading();
    showError(e.message);
  }
}

// ── Run Create Form (create mode) ─────────────────────────
async function runCreateForm() {
  const accountName = document.getElementById('account-select').value;
  const bizGoal = document.getElementById('biz-goal').value;
  const audience = document.getElementById('audience').value;
  const device = document.getElementById('device').value;
  const ga4Id = document.getElementById('ga4-id').value.trim();
  const websiteUrl = document.getElementById('create-url').value.trim();
  const description = document.getElementById('website-description').value.trim();

  if (!accountName) return showError('Please select an account.');
  if (!bizGoal) return showError('Please select a Business Goal.');
  if (!audience) return showError('Please select an Audience Type.');
  if (!device) return showError('Please select a Device Priority.');
  if (!websiteUrl) return showError('Please enter a website URL.');

  showLoading('Building your form blueprint…', [
    '🌐 Scraping website content…',
    '🧠 Analysing your business and audience…',
    '✏️ AI designing optimal form structure…',
    '📋 Writing field recommendations…',
    '🎯 Generating A/B test plan and UX projections…',
    '📄 Creating downloadable PDF blueprint…',
  ]);

  try {
    const res = await fetch('/api/create/form', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account_name: accountName,
        website_url: websiteUrl,
        business_goal: bizGoal,
        audience: audience,
        device_priority: device,
        ga4_property_id: ga4Id,
        user_description: description,
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Blueprint generation failed.');

    lastResult = data;
    hideLoading();
    renderCreateResults(data);
  } catch (e) {
    hideLoading();
    showError(e.message);
  }
}

// ── Render Create Form Results ─────────────────────────────
function renderCreateResults(data) {
  const bp = data.blueprint || {};

  // Hide score banner — not applicable for create mode
  document.getElementById('score-banner').style.display = 'none';

  // Show blueprint tab
  document.getElementById('tab-blueprint-btn').style.display = '';
  document.getElementById('tab-meta-btn').style.display = 'none';
  document.getElementById('tab-diagnosis-btn').style.display = 'none';
  document.getElementById('tab-checks-btn').style.display = 'none';
  document.getElementById('tab-analytics-btn').style.display = 'none';

  const panel = document.getElementById('blueprint-panel');
  panel.innerHTML = '';

  // Projected scores banner
  if (bp.projected_ux_score || bp.projected_conversion_rate) {
    const banner = document.createElement('div');
    banner.className = 'blueprint-scores';
    banner.innerHTML = `
      <div class="bp-score-item">
        <div class="bp-score-num">${bp.projected_ux_score || '—'}<span style="font-size:14px">/100</span></div>
        <div class="bp-score-lbl">Projected UX Score</div>
      </div>
      <div class="bp-score-item">
        <div class="bp-score-num">${bp.projected_conversion_rate || '—'}</div>
        <div class="bp-score-lbl">Projected Conversion Rate</div>
      </div>
      <div class="bp-score-item">
        <div class="bp-score-num">${(bp.recommended_fields || []).length || '—'}</div>
        <div class="bp-score-lbl">Recommended Fields</div>
      </div>
    `;
    panel.appendChild(banner);
  }

  // Form title + description
  if (bp.form_title) {
    const titleBlock = document.createElement('div');
    titleBlock.className = 'bp-title-block';
    titleBlock.innerHTML = `
      <h2 class="bp-form-title">"${bp.form_title}"</h2>
      <p class="bp-form-desc">${bp.form_description || ''}</p>
      ${bp.cta_button_text ? `<div class="bp-cta-preview"><span class="bp-cta-btn">${bp.cta_button_text}</span> <span class="bp-cta-label">Recommended CTA</span></div>` : ''}
    `;
    panel.appendChild(titleBlock);
  }

  // Recommended fields
  if ((bp.recommended_fields || []).length) {
    const fieldsBlock = document.createElement('div');
    fieldsBlock.className = 'bp-section';
    fieldsBlock.innerHTML = '<div class="step-label">Recommended Form Fields</div>';
    const table = document.createElement('div');
    table.className = 'bp-fields-table';
    bp.recommended_fields.forEach((f, i) => {
      const row = document.createElement('div');
      row.className = 'bp-field-row';
      row.innerHTML = `
        <div class="bp-field-num">${i + 1}</div>
        <div class="bp-field-info">
          <div class="bp-field-label">${f.label || 'Field'} ${f.required ? '<span class="badge orange">Required</span>' : '<span class="badge">Optional</span>'}</div>
          <div class="bp-field-meta">Type: <strong>${f.type || 'text'}</strong>${f.placeholder ? ` · Placeholder: "${f.placeholder}"` : ''}${f.options && f.options.length ? ` · Options: ${f.options.join(', ')}` : ''}</div>
          <div class="bp-field-why">${f.why_include || ''}</div>
        </div>
      `;
      table.appendChild(row);
    });
    fieldsBlock.appendChild(table);
    panel.appendChild(fieldsBlock);
  }

  // Why this works
  if (bp.why_this_works) {
    panel.appendChild(_bpTextSection('Why This Form Works', 'ti-bulb', bp.why_this_works));
  }

  // What happens next
  if (bp.what_happens_next) {
    panel.appendChild(_bpTextSection('What Happens After Submission', 'ti-arrow-right-circle', bp.what_happens_next));
  }

  // Optimization strategies
  if ((bp.optimization_strategies || []).length) {
    panel.appendChild(_bpListSection('Optimisation Strategies', 'ti-target', bp.optimization_strategies));
  }

  // Field optimization tips
  if ((bp.field_optimization_tips || []).length) {
    panel.appendChild(_bpListSection('Field Optimisation Tips', 'ti-adjustments', bp.field_optimization_tips));
  }

  // Trust signals
  if ((bp.trust_signals_to_add || []).length) {
    panel.appendChild(_bpListSection('Trust Signals to Add', 'ti-shield-check', bp.trust_signals_to_add));
  }

  // GDPR consent
  if (bp.gdpr_consent_text) {
    panel.appendChild(_bpTextSection('GDPR Consent Text', 'ti-lock', bp.gdpr_consent_text));
  }

  // Implementation plan
  if ((bp.implementation_plan || []).length) {
    const impBlock = document.createElement('div');
    impBlock.className = 'bp-section';
    impBlock.innerHTML = '<div class="step-label"><i class="ti ti-list-numbers"></i> Implementation Plan</div>';
    const ol = document.createElement('ol');
    ol.className = 'result-list bp-ol';
    bp.implementation_plan.forEach(step => {
      const li = document.createElement('li');
      li.textContent = step;
      ol.appendChild(li);
    });
    impBlock.appendChild(ol);
    panel.appendChild(impBlock);
  }

  // A/B test plan
  if (bp.ab_test_plan) {
    const abBlock = document.createElement('div');
    abBlock.className = 'bp-section bp-ab-block';
    abBlock.innerHTML = `
      <div class="step-label"><i class="ti ti-test-pipe"></i> A/B Test Plan</div>
      <div class="bp-ab-text">${typeof bp.ab_test_plan === 'string' ? bp.ab_test_plan : JSON.stringify(bp.ab_test_plan, null, 2)}</div>
    `;
    panel.appendChild(abBlock);
  }

  // Form position recommendation
  if (bp.form_position_recommendation) {
    panel.appendChild(_bpTextSection('Placement Recommendation', 'ti-layout', bp.form_position_recommendation));
  }

  // Downloads
  renderDownloads(data.downloads || {});

  showResults();
  showTab('tab-blueprint');
}

function _bpTextSection(title, icon, text) {
  const block = document.createElement('div');
  block.className = 'bp-section';
  block.innerHTML = `<div class="step-label"><i class="ti ${icon}"></i> ${title}</div><p class="bp-body-text">${text}</p>`;
  return block;
}

function _bpListSection(title, icon, items) {
  const block = document.createElement('div');
  block.className = 'bp-section';
  block.innerHTML = `<div class="step-label"><i class="ti ${icon}"></i> ${title}</div>`;
  const ul = document.createElement('ul');
  ul.className = 'result-list';
  items.forEach(item => {
    const li = document.createElement('li');
    li.textContent = item;
    ul.appendChild(li);
  });
  block.appendChild(ul);
  return block;
}

// ── Custom Questions (Meta) ────────────────────────────────
function addCustomQuestion() {
  const list = document.getElementById('custom-questions-list');
  const idx = list.children.length + 1;
  const row = document.createElement('div');
  row.className = 'custom-q-row';
  row.innerHTML = `
    <input type="text" class="custom-q-input" placeholder="e.g. What is your monthly budget?" />
    <select class="custom-q-type">
      <option value="short_answer">Short answer</option>
      <option value="multiple_choice">Multiple choice</option>
      <option value="conditional">Conditional logic</option>
    </select>
    <button type="button" class="custom-q-remove" onclick="this.parentElement.remove()">
      <i class="ti ti-trash"></i>
    </button>
  `;
  list.appendChild(row);
}

function getCustomQuestions() {
  return Array.from(document.querySelectorAll('.custom-q-row')).map(row => {
    const text = row.querySelector('.custom-q-input').value.trim();
    const type = row.querySelector('.custom-q-type').value;
    return text ? `${text} (${type})` : null;
  }).filter(Boolean);
}

// ── Meta UI Helpers ───────────────────────────────────────
function onFormTypeChange(radio) {
  document.querySelectorAll('.meta-radio-card').forEach(c => c.classList.remove('active'));
  radio.closest('.meta-radio-card').classList.add('active');
}

function onMetaAudienceChange() {
  const val = document.getElementById('meta-audience').value;
  const recommendedType = val === 'b2b' ? 'Higher intent' : 'More volume';
  document.querySelectorAll('input[name="form_type"]').forEach(r => {
    if (r.value === recommendedType) { r.checked = true; onFormTypeChange(r); }
  });
}

function countChars(input, countId, max) {
  const len = input.value.length;
  const el = document.getElementById(countId);
  if (el) {
    el.textContent = len + '/' + max;
    el.style.color = len >= max * 0.9 ? '#e53e3e' : '#999';
  }
}

// ── Run Meta Analysis ──────────────────────────────────────
async function runMetaAnalysis() {
  const accountName  = document.getElementById('account-select').value;
  const goal         = document.getElementById('meta-goal').value;
  const audience     = document.getElementById('meta-audience').value;
  const privacy      = document.getElementById('meta-privacy').value.trim();
  const formType     = document.querySelector('input[name="form_type"]:checked')?.value || 'More volume';
  const flexDelivery = document.getElementById('flexible-delivery').checked;
  const metaDescription = document.getElementById('meta-description').value.trim();

  if (!accountName) return showError('Please select an account.');
  if (!goal) return showError('Please select a Business Goal.');
  if (!audience) return showError('Please select an Audience Type.');
  const checked = Array.from(document.querySelectorAll('#field-checkboxes input:checked')).map(cb => cb.value);
  if (checked.length < 1) return showError('Please select at least 1 contact field.');
  const customQuestions = getCustomQuestions();

  showLoading('Generating Meta form spec with 5 options each…', [
    'Validating account…',
    'AI crafting 5 headline options…',
    'AI writing 5 description options…',
    'AI designing 5 thank-you screen variations…',
    'Compiling your complete Meta Instant Form spec…',
  ]);

  try {
    const res = await fetch('/api/analyse/meta', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account_name:       accountName,
        business_goal:      goal,
        audience:           audience,
        form_type:          formType,
        flexible_delivery:  flexDelivery,
        intro_headline:     '',
        intro_description:  '',
        questions_description: '',
        contact_fields:     checked,
        custom_questions:   customQuestions,
        user_description:   metaDescription,
        privacy_policy_url: privacy,
        privacy_link_text:  '',
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Meta form generation failed.');
    lastResult = data;
    hideLoading();
    renderMetaResults(data);
  } catch (e) {
    hideLoading();
    showError(e.message);
  }
}

// ── Render Website Results ─────────────────────────────────
function renderWebsiteResults(data) {
  const ux = data.ux_results || {};
  const diag = data.diagnosis || {};
  const conv = data.conversion_loss || {};
  const analytics = data.analytics || {};

  // Score banner
  document.getElementById('score-num').textContent = ux.ux_score ?? '—';
  document.getElementById('score-grade').textContent = ux.ux_grade ?? '—';
  document.getElementById('score-lift').textContent = conv.estimated_lift ?? '—';
  document.getElementById('score-rate').textContent = conv.current_estimated_rate ?? '—';
  document.getElementById('score-banner').style.display = 'grid';

  // Show/hide relevant tabs
  document.getElementById('tab-diagnosis-btn').style.display = '';
  document.getElementById('tab-checks-btn').style.display = '';
  document.getElementById('tab-analytics-btn').style.display = '';
  document.getElementById('tab-blueprint-btn').style.display = 'none';
  document.getElementById('tab-meta-btn').style.display = 'none';

  // Diagnosis tab
  renderList('diagnosis-summary-list', diag.key_issues || []);
  renderList('root-causes', diag.root_causes || []);
  renderList('quick-wins', diag.quick_wins || []);
  renderList('cta-variants', diag.cta_variants || []);
  renderList('strategic-fixes', diag.strategic_fixes || []);
  renderList('ux-optimisation-plan', diag.ux_optimisation_plan || []);
  renderList('form-redesign-recommendations', diag.form_redesign_recommendations || []);

  // UX Checks tab
  renderChecks(ux.checks || {});

  // Analytics tab
  renderAnalytics(analytics, data.ux_results);

  // Downloads tab
  renderDownloads(data.downloads || {});

  showResults();
  showTab('tab-diagnosis');
}

// ── Render Meta Results ────────────────────────────────────
function renderMetaResults(data) {
  const spec = data.meta_form_spec || {};
  document.getElementById('score-banner').style.display = 'none';
  document.getElementById('tab-diagnosis-btn').style.display = 'none';
  document.getElementById('tab-checks-btn').style.display = 'none';
  document.getElementById('tab-analytics-btn').style.display = 'none';
  document.getElementById('tab-blueprint-btn').style.display = 'none';
  document.getElementById('tab-meta-btn').style.display = '';

  const panel = document.getElementById('meta-spec-panel');
  panel.innerHTML = '';

  // Helper: render one section with a list of option cards
  function makeOptionsBlock(title, icon, optionsArray, noteText) {
    if (!optionsArray || !optionsArray.length) return null;
    const block = document.createElement('div');
    block.className = 'meta-result-block';
    block.innerHTML = `<div class="meta-result-header"><i class="ti ${icon}"></i> ${title}</div>` +
      (noteText ? `<p class="meta-options-note">${noteText}</p>` : '');
    const grid = document.createElement('div');
    grid.className = 'meta-options-grid';
    optionsArray.forEach((opt, i) => {
      const card = document.createElement('div');
      card.className = 'meta-option-card';
      card.innerHTML = `
        <div class="meta-opt-num">Option ${i + 1}</div>
        <div class="meta-opt-text">${opt}</div>
        <button class="meta-opt-copy" title="Copy to clipboard" onclick="copyMetaOption(this, '${opt.replace(/'/g, "\\'")}')">
          <i class="ti ti-copy"></i> Copy
        </button>
      `;
      grid.appendChild(card);
    });
    block.appendChild(grid);
    return block;
  }

  function makeSpecBlock(title, icon, rows) {
    const block = document.createElement('div');
    block.className = 'meta-result-block';
    block.innerHTML = `<div class="meta-result-header"><i class="ti ${icon}"></i> ${title}</div>`;
    const grid = document.createElement('div');
    grid.className = 'meta-spec-grid';
    rows.forEach(r => {
      if (r.val === undefined || r.val === null || r.val === '') return;
      const card = document.createElement('div');
      card.className = 'spec-card';
      card.innerHTML = `<div class="spec-lbl">${r.lbl}</div><div class="spec-val">${r.val}</div>` +
        (r.sub ? `<div class="spec-sub">${r.sub}</div>` : '');
      grid.appendChild(card);
    });
    block.appendChild(grid);
    return block;
  }

  // Form type block
  const typeBlock = makeSpecBlock('Form Configuration', 'ti-forms', [
    { lbl: 'Form Name',         val: spec.form_name  || '—' },
    { lbl: 'Form Type',         val: spec.form_type  || '—' },
    { lbl: 'Flexible Delivery', val: spec.flexible_delivery ? 'Enabled — Optimised by Meta AI' : 'Manual' },
  ]);
  panel.appendChild(typeBlock);

  // Intro — 5 headline options
  const introHeadlines = spec.intro_card?.headline_options || (spec.intro_card?.headline ? [spec.intro_card.headline] : []);
  const introDescs = spec.intro_card?.description_options || (spec.intro_card?.description ? [spec.intro_card.description] : []);
  const introBg = spec.intro_card?.image_recommendation;

  if (introHeadlines.length) {
    const b = makeOptionsBlock('Intro Card — Headline Options (Pick 1)', 'ti-id-badge-2', introHeadlines, 'AI-generated options tailored to your business goal and audience. Test each for best CTR.');
    if (b) panel.appendChild(b);
  }
  if (introDescs.length) {
    const b = makeOptionsBlock('Intro Card — Description Options (Pick 1)', 'ti-align-left', introDescs);
    if (b) panel.appendChild(b);
  }
  if (introBg) {
    const b = makeSpecBlock('Intro Card — Visual', 'ti-photo', [{ lbl: 'Image Recommendation', val: introBg }]);
    panel.appendChild(b);
  }

  // Questions section
  const qs = spec.questions_section || {};
  const qDescs = qs.description_options || (qs.description ? [qs.description] : []);
  if (qDescs.length) {
    const b = makeOptionsBlock('Questions Screen — Description Options (Pick 1)', 'ti-list-check', qDescs, 'Short description shown above your contact fields.');
    if (b) panel.appendChild(b);
  }
  const preFill = (qs.pre_fill_fields || []).join(', ');
  const customQList = qs.custom_questions || [];
  if (preFill || customQList.length) {
    panel.appendChild(makeSpecBlock('Questions — Contact Fields', 'ti-address-book', [
      { lbl: 'Pre-fill Fields (from Meta profile)', val: preFill || '—' },
      { lbl: 'Custom Questions', val: customQList.length ? customQList.join(' · ') : 'None added' },
    ]));
  }

  // Privacy
  panel.appendChild(makeSpecBlock('Privacy Policy', 'ti-lock', [
    { lbl: 'Link Text', val: spec.privacy_policy?.link_text || '—' },
    { lbl: 'URL',       val: spec.privacy_policy?.url       || '—' },
  ]));

  // Review screen
  if (spec.review_screen?.enabled) {
    panel.appendChild(makeSpecBlock('Review Screen', 'ti-eye', [
      { lbl: 'Enabled', val: 'Yes — leads confirm their info before submitting', sub: spec.review_screen.note || '' },
    ]));
  }

  // Thank-you screen — 5 options each
  const ty = spec.thank_you_screen || {};
  const tyHeadlines = ty.headline_options || (ty.headline ? [ty.headline] : []);
  const tyDescs = ty.description_options || (ty.description ? [ty.description] : []);
  const tyCtas = ty.cta_options || (ty.cta_button_text ? [ty.cta_button_text] : []);
  if (tyHeadlines.length) {
    const b = makeOptionsBlock('Thank You Screen — Headline Options (Pick 1)', 'ti-circle-check', tyHeadlines, 'Reinforce why they made a great choice. Test urgency vs. reassurance.');
    if (b) panel.appendChild(b);
  }
  if (tyDescs.length) {
    const b = makeOptionsBlock('Thank You Screen — Description Options (Pick 1)', 'ti-message-2', tyDescs);
    if (b) panel.appendChild(b);
  }
  if (tyCtas.length) {
    const b = makeOptionsBlock('Thank You Screen — CTA Button Options (Pick 1)', 'ti-hand-click', tyCtas, 'Drive next action: website visit, booking, or download.');
    if (b) panel.appendChild(b);
  }
  if (ty.cta_url) {
    panel.appendChild(makeSpecBlock('Thank You Screen — CTA URL', 'ti-link', [{ lbl: 'URL', val: ty.cta_url }]));
  }

  // How this helps
  const helpItems = spec.how_this_helps || [];
  if (helpItems.length) {
    const block = document.createElement('div');
    block.className = 'meta-result-block';
    block.innerHTML = `<div class="meta-result-header"><i class="ti ti-chart-bar"></i> How This Form Helps Your Business</div>`;
    const ul = document.createElement('ul');
    ul.className = 'result-list';
    helpItems.forEach(h => { const li = document.createElement('li'); li.textContent = h; ul.appendChild(li); });
    block.appendChild(ul);
    panel.appendChild(block);
  }

  // CRM + email validation
  panel.appendChild(makeSpecBlock('Email Validation & CRM', 'ti-mail-check', [
    { lbl: 'Validation Tool', val: spec.email_validation?.tool_recommended || '—', sub: spec.email_validation?.setup_note || '' },
    { lbl: 'CRM Sync',        val: spec.crm_sync_note || '—' },
  ]));

  // Optimisation tips
  if ((spec.optimisation_tips || []).length) {
    const block = document.createElement('div');
    block.className = 'meta-result-block';
    block.innerHTML = `<div class="meta-result-header"><i class="ti ti-bulb"></i> Optimisation Tips</div>`;
    const ul = document.createElement('ul');
    ul.className = 'result-list';
    spec.optimisation_tips.forEach(tip => { const li = document.createElement('li'); li.textContent = tip; ul.appendChild(li); });
    block.appendChild(ul);
    panel.appendChild(block);
  }

  // Implementation steps
  const stepsList = document.getElementById('meta-steps');
  stepsList.innerHTML = '';
  (data.implementation_steps || []).forEach(step => {
    const li = document.createElement('li'); li.textContent = step; stepsList.appendChild(li);
  });

  // Downloads (meta PDF)
  renderDownloads(data.downloads || {});

  showResults();
  showTab('tab-meta');
}

// ── Render Helpers ─────────────────────────────────────────
function renderList(id, items) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = '';
  if (!items || !items.length) {
    el.innerHTML = '<li style="color:#aaa;font-style:italic">No data available.</li>';
    return;
  }
  items.forEach(item => {
    const li = document.createElement('li');
    li.textContent = item;
    el.appendChild(li);
  });
}

function renderChecks(checks) {
  const grid = document.getElementById('checks-grid');
  grid.innerHTML = '';
  Object.entries(checks).forEach(([key, chk]) => {
    const passed = chk.passed;
    const card = document.createElement('div');
    card.className = `check-card ${passed ? 'pass' : 'fail'}`;
    card.innerHTML = `
      <div class="check-head">
        <span class="check-name">${chk.name || key}</span>
        <span class="check-score ${passed ? 'pass' : 'fail'}">${chk.score}/${chk.max_score}</span>
      </div>
      <div class="check-finding">${chk.finding || ''}</div>
      ${!passed ? `<div class="check-fix">💡 ${chk.fix || ''}</div>` : ''}
    `;
    grid.appendChild(card);
  });
}

function renderAnalytics(analytics, uxResults) {
  const panel = document.getElementById('analytics-panel');
  panel.innerHTML = '';

  const stats = [
    { num: analytics.form_starts ?? '—', lbl: 'Form Starts' },
    { num: analytics.form_submits ?? '—', lbl: 'Form Submits' },
    { num: analytics.completion_rate ?? '—', lbl: 'Completion Rate' },
    { num: analytics.abandonment_rate ?? '—', lbl: 'Abandonment Rate' },
    { num: analytics.device_split?.mobile ?? '—', lbl: 'Mobile Sessions' },
    { num: (analytics.date_range ?? '30 days').replace(' (illustrative)', ''), lbl: 'Date Range' },
  ];

  const grid = document.createElement('div');
  grid.className = 'analytics-grid';
  grid.style.gridTemplateColumns = 'repeat(3, 1fr)';
  stats.forEach(s => {
    const card = document.createElement('div');
    card.className = 'analytics-stat';
    card.innerHTML = `<div class="analytics-num">${s.num}</div><div class="analytics-lbl">${s.lbl}</div>`;
    grid.appendChild(card);
  });
  panel.appendChild(grid);

  if (analytics.field_drop_off && analytics.field_drop_off.length) {
    const title = document.createElement('div');
    title.className = 'sub-h';
    title.style.marginTop = '16px';
    title.textContent = 'Field-level Drop-off';
    panel.appendChild(title);

    const ul = document.createElement('ul');
    ul.className = 'result-list';
    analytics.field_drop_off.forEach(row => {
      const li = document.createElement('li');
      li.innerHTML = `<strong>${row.field}</strong> — Drop-off: ${row.drop_off_pct}`;
      ul.appendChild(li);
    });
    panel.appendChild(ul);
  }
}

function renderDownloads(downloads) {
  const grid = document.getElementById('download-grid');
  grid.innerHTML = '';

  const files = [
    { url: downloads.pdf_brief,      icon: 'ti-file-text',   title: 'Form Redesign Brief',        sub: 'PDF — full audit report for designer & developer' },
    { url: downloads.ux_table_csv,   icon: 'ti-table',       title: 'UX Improvement Table',        sub: 'CSV — prioritised sprint backlog' },
    { url: downloads.pdf_blueprint,  icon: 'ti-file-pencil', title: 'New Form Blueprint',          sub: 'PDF — complete AI-designed form spec' },
    { url: downloads.meta_spec_pdf,  icon: 'ti-brand-meta',  title: 'Meta Instant Form Spec',     sub: 'PDF — 5 options per element, ready for Ads Manager' },
  ];

  files.forEach(f => {
    if (!f.url) return;
    const a = document.createElement('a');
    a.className = 'download-card';
    a.href = f.url;
    a.target = '_blank';
    a.innerHTML = `
      <i class="ti ${f.icon} download-icon"></i>
      <div>
        <div class="download-title">${f.title}</div>
        <div class="download-sub">${f.sub}</div>
      </div>
    `;
    grid.appendChild(a);
  });

  if (!grid.children.length) {
    grid.innerHTML = '<p style="color:#999;font-size:13px">No files generated yet.</p>';
  }
}

// ── Copy Meta Option ───────────────────────────────────────
function copyMetaOption(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.innerHTML;
    btn.innerHTML = '<i class="ti ti-check"></i> Copied!';
    btn.classList.add('copied');
    setTimeout(() => { btn.innerHTML = orig; btn.classList.remove('copied'); }, 1800);
  }).catch(() => {
    // Fallback for older browsers
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    btn.innerHTML = '<i class="ti ti-check"></i> Copied!';
    setTimeout(() => { btn.innerHTML = '<i class="ti ti-copy"></i> Copy'; }, 1800);
  });
}

// ── Tab Switching ──────────────────────────────────────────
function showTab(id) {
  document.querySelectorAll('.tab-panel').forEach(p => p.style.display = 'none');
  document.querySelectorAll('.rt').forEach(b => b.classList.remove('active'));
  const panel = document.getElementById(id);
  if (panel) panel.style.display = 'block';
  // Activate the corresponding button
  const btnId = id + '-btn';
  const btn = document.getElementById(btnId);
  if (btn) {
    btn.classList.add('active');
  } else {
    // Fallback: match by onclick content for Downloads tab (no btn id)
    document.querySelectorAll('.rt').forEach(b => {
      if (b.getAttribute('onclick') && b.getAttribute('onclick').includes(id)) {
        b.classList.add('active');
      }
    });
  }
}

// ── Start Over ─────────────────────────────────────────────
function startOver() {
  // Reset all state
  mode = null;
  selectedFormUrl = null;
  lastResult = null;

  // Reset account selector
  document.getElementById('account-select').value = '';
  document.getElementById('account-info').style.display = 'none';

  // Reset mode cards
  document.getElementById('mc-optimise').classList.remove('active');
  document.getElementById('mc-create').classList.remove('active');

  // Hide mode-specific panels
  document.getElementById('step-inputs').style.display = 'none';
  document.getElementById('form-discovery-panel').style.display = 'none';
  document.getElementById('create-url-panel').style.display = 'none';
  document.getElementById('run-website').style.display = 'none';
  document.getElementById('audience-note').style.display = 'none';

  // Clear all form inputs
  ['scan-url', 'create-url', 'form-url', 'ga4-id', 'website-description', 'meta-description'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });

  // Reset dropdowns to blank
  ['biz-goal', 'audience', 'device', 'meta-goal', 'meta-audience'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });

  // Clear custom questions
  const cqList = document.getElementById('custom-questions-list');
  if (cqList) cqList.innerHTML = '';

  // Clear discovered forms
  const discovered = document.getElementById('discovered-forms-section');
  if (discovered) discovered.style.display = 'none';
  const list = document.getElementById('discovered-forms-list');
  if (list) list.innerHTML = '';

  // Reset tab visibility for next run
  document.getElementById('tab-diagnosis-btn').style.display = '';
  document.getElementById('tab-checks-btn').style.display = '';
  document.getElementById('tab-analytics-btn').style.display = '';
  document.getElementById('tab-blueprint-btn').style.display = 'none';
  document.getElementById('tab-meta-btn').style.display = 'none';

  // Hide results
  hideResults();
  hideLoading();

  // Scroll back to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── UI Helpers ─────────────────────────────────────────────
function showLoading(title, steps) {
  document.getElementById('loading').style.display = 'block';
  document.getElementById('loading-title').textContent = title;
  const stepsEl = document.getElementById('loading-steps');
  let i = 0;
  stepsEl.textContent = steps[0] || '';
  const interval = setInterval(() => {
    i++;
    if (i < steps.length) stepsEl.textContent = steps[i];
    else clearInterval(interval);
  }, 1800);
  window._loadingInterval = interval;
  hideResults();
}

function hideLoading() {
  document.getElementById('loading').style.display = 'none';
  if (window._loadingInterval) clearInterval(window._loadingInterval);
}

function showResults() {
  document.getElementById('results').style.display = 'block';
  document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}

function hideResults() {
  document.getElementById('results').style.display = 'none';
}

function showError(msg) {
  alert('Error: ' + msg);
}
