/* ═══════════════════════════════════════════════════════════════════════════
   InGovern Governance Agent — Frontend Application
   Single-page: History panel + New Report form + Scrollable pipeline results
═══════════════════════════════════════════════════════════════════════════ */

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  currentView: "home",
  reportData: null,
  company: "",
  fiscalYear: "",
};

// ── DOM helpers ───────────────────────────────────────────────────────────────
const el = (id) => document.getElementById(id);
const VIEWS = ["home", "form", "running", "report"];

function showView(name) {
  VIEWS.forEach((v) => {
    const node = el(`view-${v}`);
    if (node) node.classList.toggle("active", v === name);
  });
  state.currentView = name;
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, type = "info") {
  const tc = el("toastContainer");
  const t = document.createElement("div");
  t.className = `toast toast-${type}`;
  t.innerHTML = `<span>${msg}</span>`;
  tc.appendChild(t);
  setTimeout(() => t.classList.add("show"), 10);
  setTimeout(() => {
    t.classList.remove("show");
    setTimeout(() => t.remove(), 350);
  }, 3500);
}

// ── Theme ─────────────────────────────────────────────────────────────────────
(function initTheme() {
  const saved = localStorage.getItem("ingovern-theme") || "dark";
  document.documentElement.dataset.theme = saved;
})();

el("themeToggle").addEventListener("click", () => {
  const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = t;
  localStorage.setItem("ingovern-theme", t);
});

// ── History ───────────────────────────────────────────────────────────────────
function getHistory() {
  try {
    return JSON.parse(localStorage.getItem("ingovern-history") || "[]");
  } catch {
    return [];
  }
}

function saveHistory(items) {
  localStorage.setItem("ingovern-history", JSON.stringify(items));
}

function addHistoryItem(company, fiscalYear, noticeType, reportData) {
  const history = getHistory();
  const id = `${company}_${fiscalYear}_${Date.now()}`;
  const item = {
    id,
    company,
    fiscalYear,
    noticeType: noticeType || "AGM",
    date: new Date().toISOString(),
    reportData,
  };
  // Replace existing entry for same company+FY
  const idx = history.findIndex(
    (h) => h.company === company && h.fiscalYear === fiscalYear
  );
  if (idx >= 0) history.splice(idx, 1, item);
  else history.unshift(item);
  saveHistory(history);
  renderHistory();
  return item;
}

function renderHistory() {
  const list = el("historyList");
  const empty = el("historyEmpty");
  const history = getHistory();

  if (!history.length) {
    empty.style.display = "";
    list.querySelectorAll(".history-item").forEach((n) => n.remove());
    return;
  }
  empty.style.display = "none";

  // Remove old items
  list.querySelectorAll(".history-item").forEach((n) => n.remove());

  history.forEach((item) => {
    const btn = document.createElement("button");
    btn.className = "history-item";
    const dt = new Date(item.date);
    const dateStr = dt.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
    btn.innerHTML = `
      <div class="hi-company">${escapeHtml(item.company)}</div>
      <div class="hi-meta">
        <span class="badge badge-${(item.noticeType || "AGM").toLowerCase()}">${escapeHtml(item.noticeType || "AGM")}</span>
        <span class="hi-fy">${escapeHtml(item.fiscalYear || "")}</span>
      </div>
      <div class="hi-date">${dateStr}</div>
    `;
    btn.addEventListener("click", () => loadHistoryReport(item));
    list.appendChild(btn);
  });
}

function loadHistoryReport(item) {
  state.company = item.company;
  state.fiscalYear = item.fiscalYear;
  state.reportData = item.reportData;
  el("pageTitle").textContent = item.company;
  el("pageSubtitle").textContent = `${item.fiscalYear} · ${item.noticeType || "AGM"} · Historical Report`;
  const badge = el("sessionBadge");
  badge.textContent = item.noticeType || "AGM";
  badge.className = `badge badge-${(item.noticeType || "AGM").toLowerCase()}`;
  badge.style.display = "";
  renderFullReport(item.reportData);
  showView("report");
}

// ── File upload zone ──────────────────────────────────────────────────────────
(function setupUploadZone() {
  const zone = el("uploadZone");
  const input = el("pdfInput");
  const label = el("fileLabel");

  zone.addEventListener("click", () => input.click());
  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("drag-over");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    const f = e.dataTransfer.files[0];
    if (f && f.name.toLowerCase().endsWith(".pdf")) {
      const dt = new DataTransfer();
      dt.items.add(f);
      input.files = dt.files;
      setFileLabel(f.name);
    } else {
      toast("Please drop a PDF file.", "error");
    }
  });
  input.addEventListener("change", () => {
    if (input.files[0]) setFileLabel(input.files[0].name);
  });

  function setFileLabel(name) {
    label.textContent = `Selected: ${name}`;
    label.style.display = "";
    const iconDiv = zone.querySelector(".upload-icon");
    if (iconDiv) iconDiv.innerHTML = `
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>`;
  }
})();

// ── New Report button ─────────────────────────────────────────────────────────
el("newReportBtn").addEventListener("click", () => {
  resetForm();
  showView("form");
  el("pageTitle").textContent = "New Report";
  el("pageSubtitle").textContent = "Upload a governance notice to begin analysis";
  el("sessionBadge").style.display = "none";
});

function resetForm() {
  el("companyName").value = "";
  el("fiscalYear").value = "";
  el("pdfInput").value = "";
  el("fileLabel").style.display = "none";
  const iconDiv = document.querySelector(".upload-icon");
  if (iconDiv) iconDiv.innerHTML = `
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
    </svg>`;
}

// ── Upload & Pipeline ─────────────────────────────────────────────────────────
el("uploadBtn").addEventListener("click", startPipeline);

async function startPipeline() {
  const company = el("companyName").value.trim();
  const fy = el("fiscalYear").value.trim();
  const file = el("pdfInput").files[0];

  if (!file) {
    toast("Please select a PDF file.", "error");
    return;
  }

  state.company = company;
  state.fiscalYear = fy;

  el("runningCompanyTitle").textContent = company || "Analysing…";
  el("pageTitle").textContent = company || "Running Analysis";
  el("pageSubtitle").textContent = `${fy} · Processing pipeline…`;
  el("sessionBadge").style.display = "none";

  showView("running");
  resetPipelineUI();

  try {
    // ── Step 1: Upload ──────────────────────────────────────────────────────
    setStep("upload", "running");
    setProgress(1, "Uploading PDF notice…");

    const fd = new FormData();
    fd.append("file", file);
    if (company) fd.append("company_name", company);
    if (fy) fd.append("fiscal_year", fy);

    const uploadRes = await apiFetch("/upload_notice", { method: "POST", body: fd });
    if (!uploadRes || (uploadRes.status !== "success" && uploadRes.status !== "uploaded")) {
      throw new Error(uploadRes?.message || "Upload failed");
    }
    setStep("upload", "done");
    setProgress(2, "Extracting metadata…");

    // ── Step 2: Metadata ────────────────────────────────────────────────────
    setStep("metadata", "running");
    // metadata failure is non-fatal — continue with empty object
    let metaRes = await apiFetch("/notice/metadata");
    if (!metaRes || metaRes.status === "error") {
      metaRes = { status: "success" };
    }
    setStep("metadata", "done");
    setProgress(3, "Extracting board of directors…");

    // ── Step 3: Board ───────────────────────────────────────────────────────
    setStep("board", "running");
    // board failure is non-fatal — continue with empty list
    let boardRes = await apiFetch("/board/full");
    if (!boardRes || boardRes.status === "error") {
      boardRes = { status: "success", directors: [] };
    }
    setStep("board", "done");
    setProgress(4, "Extracting resolutions…");

    // ── Step 4: Resolutions ─────────────────────────────────────────────────
    setStep("resolutions", "running");
    const resRes = await apiFetch("/extract_resolutions");
    if (!resRes || resRes.status === "error") {
      throw new Error(resRes?.message || "Resolution extraction failed");
    }
    setStep("resolutions", "done");
    setProgress(5, "Generating AI commentary… (this may take several minutes)");

    // ── Step 5: Commentary ──────────────────────────────────────────────────
    setStep("commentary", "running");
    const commRes = await apiFetch("/generate_commentary");
    if (!commRes || commRes.status === "error") {
      throw new Error(commRes?.message || "Commentary generation failed");
    }
    setStep("commentary", "done");
    setProgress(6, "Building structured report…");

    // ── Step 6: Report ──────────────────────────────────────────────────────
    setStep("report", "running");
    const reportRes = await apiFetch("/full_report/generate");
    if (!reportRes || reportRes.status === "error") {
      throw new Error(reportRes?.message || "Report generation failed");
    }
    setStep("report", "done");
    setProgress(6, "Report complete!", 100);

    // ── Compile & render ────────────────────────────────────────────────────
    const resolvedMeta = metaRes.metadata || metaRes;
    const finalCompany =
      company || resolvedMeta.company_name || "Unknown Company";
    const noticeType = resolvedMeta.notice_type || "AGM";

    const fullData = {
      metadata: metaRes,
      board: boardRes,
      resolutions: resRes,
      commentary: commRes,
      report: reportRes,
      company: finalCompany,
      fiscalYear: fy,
    };

    state.reportData = fullData;
    state.company = finalCompany;

    addHistoryItem(finalCompany, fy, noticeType, fullData);

    el("pageTitle").textContent = finalCompany;
    el("pageSubtitle").textContent = `${fy} · ${noticeType} · Report Generated`;
    el("sessionBadge").textContent = noticeType;
    el("sessionBadge").className = `badge badge-${noticeType.toLowerCase()}`;
    el("sessionBadge").style.display = "";

    renderFullReport(fullData);
    showView("report");
    // Scroll to top of report
    el("appMain").scrollTo({ top: 0, behavior: "smooth" });
    toast("Report generated successfully!", "success");

  } catch (err) {
    toast(`Error: ${err.message}`, "error");
    showView("form");
  }
}

// ── Progress helpers ──────────────────────────────────────────────────────────
const STEP_ORDER = ["upload", "metadata", "board", "resolutions", "commentary", "report"];
const STEP_PCT   = [10, 25, 40, 55, 75, 100];

function resetPipelineUI() {
  STEP_ORDER.forEach((s, i) => {
    const node = el(`ps-${s}`);
    const badge = el(`psb-${s}`);
    if (!node) return;
    node.classList.remove("ps-running", "ps-done", "ps-error");
    node.classList.add("ps-pending");
    const icon = node.querySelector(".ps-icon");
    if (icon) icon.innerHTML = `<span class="ps-num">${i + 1}</span>`;
    if (badge) badge.textContent = "";
  });
  el("progressBar").style.width = "0%";
  el("progressLabel").textContent = "Starting…";
  el("progressPct").textContent = "0%";
}

function setStep(step, status) {
  const node = el(`ps-${step}`);
  const badge = el(`psb-${step}`);
  if (!node) return;

  node.classList.remove("ps-pending", "ps-running", "ps-done", "ps-error");
  node.classList.add(`ps-${status}`);

  const icon = node.querySelector(".ps-icon");
  if (status === "running") {
    if (icon) icon.innerHTML = `<div class="ps-spinner"></div>`;
    if (badge) badge.textContent = "Running…";
  } else if (status === "done") {
    if (icon) icon.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"/>
      </svg>`;
    if (badge) badge.textContent = "Done";
  } else if (status === "error") {
    if (icon) icon.innerHTML = `<span style="color:#ef4444;font-weight:900;">!</span>`;
    if (badge) badge.textContent = "Error";
  }
}

function setProgress(stepNum, label, forcePct) {
  const pct = forcePct !== undefined ? forcePct : STEP_PCT[stepNum - 1] || (stepNum / 6) * 100;
  el("progressBar").style.width = `${pct}%`;
  el("progressLabel").textContent = label;
  el("progressPct").textContent = `${Math.round(pct)}%`;
}

// ── API helper ────────────────────────────────────────────────────────────────
async function apiFetch(url, opts = {}, timeoutMs = 0) {
  // timeoutMs = 0 means no timeout — wait as long as the server needs
  const controller = new AbortController();
  const timer = timeoutMs > 0 ? setTimeout(() => controller.abort(), timeoutMs) : null;
  try {
    const res = await fetch(url, { signal: controller.signal, ...opts });
    if (timer) clearTimeout(timer);
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) return res.json();
    return { status: res.ok ? "success" : "error", message: `HTTP ${res.status}` };
  } catch (e) {
    if (timer) clearTimeout(timer);
    if (e.name === "AbortError") throw new Error("Request cancelled.");
    throw e;
  }
}

// ── Render full report ────────────────────────────────────────────────────────
function renderFullReport(data) {
  if (!data) return;

  const { metadata, board, resolutions, commentary } = data;

  // Normalise nested response shapes
  const meta     = (metadata && metadata.metadata) ? metadata.metadata : (metadata || {});
  const boardList = board?.board_of_directors || board?.directors || [];
  const resList   = resolutions?.resolutions || resolutions?.data || [];
  const commList  = commentary?.commentaries || [];

  // ① Metadata
  renderMetadata(meta);

  // ② Board of Directors
  renderBoard(boardList);

  // ③ Merge resolutions with their commentary
  const merged = mergeResolutionsWithCommentary(resList, commList);

  // ④ Proposals summary table
  renderResolutionSummary(merged);

  // ⑤ Resolution detail cards
  renderResolutionCards(merged);

  // ⑥ Header
  const company     = data.company || meta.company_name || "Company";
  const fy          = data.fiscalYear || "";
  const noticeType  = meta.notice_type || "AGM";
  const meetingDate = meta.meeting_date || "";

  el("reportCompanyTitle").textContent = company;
  el("reportMetaSub").textContent = [fy, noticeType, meetingDate].filter(Boolean).join(" · ");
  el("rpt-approve-card").style.display = "";
  el("approvalResult").style.display = "none";
}

function renderMetadata(meta) {
  const grid = el("rpt-metadata");
  grid.innerHTML = "";

  const fields = [
    { label: "Company Name",    key: "company_name" },
    { label: "ISIN",            key: "isin" },
    { label: "Notice Type",     key: "notice_type" },
    { label: "Meeting Date",    key: "meeting_date" },
    { label: "Meeting Time",    key: "meeting_time" },
    { label: "Venue",           key: "meeting_venue" },
    { label: "E-Voting Agency", key: "evoting_agency" },
    { label: "E-Voting Start",  key: "evoting_start" },
    { label: "E-Voting End",    key: "evoting_end" },
    { label: "Result Date",     key: "evoting_result_date" },
  ];

  let count = 0;
  fields.forEach(({ label, key }) => {
    const val = meta[key];
    if (!val) return;
    count++;
    const div = document.createElement("div");
    div.className = "meta-item";
    div.innerHTML = `<div class="meta-label">${escapeHtml(label)}</div><div class="meta-value">${escapeHtml(String(val))}</div>`;
    grid.appendChild(div);
  });

  if (!count) {
    grid.innerHTML = `<div class="text-muted text-sm" style="padding:0.5rem 0;">No metadata available.</div>`;
  }
}

function renderBoard(directors) {
  const tbody = el("rpt-board-body");
  el("rpt-board-sub").textContent = `${directors.length} director${directors.length !== 1 ? "s" : ""} found`;

  if (!directors.length) {
    tbody.innerHTML = `<tr><td colspan="15" style="text-align:center;color:var(--text-muted);padding:1.5rem;">No board data extracted from this notice.</td></tr>`;
    return;
  }

  const tick = (v) => {
    if (v === "Chairman") return `<span style="color:var(--brand-400);font-weight:700;">C</span>`;
    if (v === true || v === "true" || v === "True") return `<span style="color:#22c55e;font-weight:700;">✓</span>`;
    return `<span style="color:var(--text-muted);">—</span>`;
  };

  tbody.innerHTML = directors.map((d) => `<tr>
    <td>${escapeHtml(String(d.s_no ?? ""))}</td>
    <td style="font-weight:600;white-space:nowrap;">${escapeHtml(d.name || "")}</td>
    <td>${escapeHtml(String(d.years_as_director ?? d.years ?? ""))}</td>
    <td>${escapeHtml(String(d.date_of_appointment ?? d.appointed ?? ""))}</td>
    <td>${tick(d.chairman)}</td>
    <td>${tick(d.md_ceo ?? d.managing_director)}</td>
    <td>${tick(d.executive ?? d.executive_director)}</td>
    <td>${tick(d.non_executive)}</td>
    <td>${tick(d.independent)}</td>
    <td>${tick(d.audit ?? d.audit_committee)}</td>
    <td>${tick(d.nomination_remuneration ?? d.nrc)}</td>
    <td>${tick(d.stakeholder ?? d.stakeholder_committee)}</td>
    <td>${tick(d.risk ?? d.risk_committee)}</td>
    <td>${tick(d.csr ?? d.csr_committee)}</td>
    <td>${escapeHtml(String(d.other_companies ?? "0"))}</td>
  </tr>`).join("");
}

function mergeResolutionsWithCommentary(resList, commList) {
  return resList.map((res) => {
    const num = res.resolution_number;
    const commItem = commList.find((c) => {
      const cn = c.resolution_number ?? c.ingovern_commentary?.resolution_number;
      return cn === num;
    });
    const commentary = commItem?.ingovern_commentary || res.ingovern_commentary || null;
    return { ...res, ingovern_commentary: commentary };
  });
}

function renderResolutionSummary(resolutions) {
  const tbody = el("rpt-summary-body");
  el("rpt-summary-sub").textContent = `${resolutions.length} resolution${resolutions.length !== 1 ? "s" : ""}`;

  tbody.innerHTML = resolutions.map((res) => {
    const comm = res.ingovern_commentary || {};
    const rec  = comm.ingovern_recommendation || res.cover_ingovern_rec || "—";
    const mgmt = comm.management_recommendation || "FOR";
    const conf = comm.confidence || "—";
    const type = res.special_resolution ? "Special" : "Ordinary";
    return `<tr>
      <td style="font-weight:700;">${escapeHtml(String(res.resolution_number ?? ""))}</td>
      <td>${escapeHtml(res.title || res.resolution_type || "")}</td>
      <td><span class="badge badge-${type.toLowerCase()}">${type}</span></td>
      <td><span class="badge badge-for">${escapeHtml(mgmt)}</span></td>
      <td><span class="badge ${getRecClass(rec)}">${escapeHtml(rec)}</span></td>
      <td><span class="badge ${getConfClass(conf)}">${escapeHtml(conf)}</span></td>
    </tr>`;
  }).join("");
}

function renderResolutionCards(resolutions) {
  const container = el("rpt-resolutions");
  container.innerHTML = "";

  resolutions.forEach((res, idx) => {
    const comm = res.ingovern_commentary || {};
    const rec  = comm.ingovern_recommendation || res.cover_ingovern_rec || "—";
    const type = res.special_resolution ? "Special" : "Ordinary";

    const S = {
      h:  (t) => `<div style="font-size:0.72rem;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;color:#6366f1;margin:1.4rem 0 0.5rem;padding-bottom:0.3rem;border-bottom:1px solid #e5e7eb;">${t}</div>`,
      li: (t) => `<div style="display:flex;gap:0.5rem;margin:0 0 0.4rem;color:#374151;font-size:0.895rem;line-height:1.8;"><span style="color:#6366f1;flex-shrink:0;">•</span><span>${escapeHtml(t.replace(/^[•\-]\s*/,""))}</span></div>`,
      p:  (t) => `<p style="margin:0 0 0.85rem;color:#374151;font-size:0.895rem;line-height:1.85;">${escapeHtml(t)}</p>`,
    };

    // Render a paragraph: split on newlines, bullet lines get bullet treatment
    const renderPara = (text) => {
      const lines = text.split(/\n/);
      if (lines.length === 1) {
        return lines[0].trim().match(/^[•\-]/) ? S.li(lines[0]) : S.p(lines[0]);
      }
      let html = "";
      let prose = [];
      for (const line of lines) {
        const t = line.trim();
        if (!t) continue;
        if (t.match(/^[•\-]/)) {
          if (prose.length) { html += S.p(prose.join(" ")); prose = []; }
          html += S.li(t);
        } else {
          prose.push(t);
        }
      }
      if (prose.length) html += S.p(prose.join(" "));
      return html;
    };

    const renderParas = (arr) => (arr||[]).map(renderPara).join("");

    const intro      = comm.introduction    ? S.h("Introduction") + S.p(comm.introduction) : "";
    const summary    = (comm.summary_paragraphs||[]).length    ? S.h("Summary")             + renderParas(comm.summary_paragraphs)    : "";
    const commentary = (comm.ingovern_commentary||[]).length   ? S.h("InGovern Commentary") + renderParas(comm.ingovern_commentary)   : "";
    const concerns   = (comm.governance_concerns||[]).length   ? S.h("Governance Concerns") +
      (comm.governance_concerns).map((c,i) =>
        `<p style="margin:0 0 0.6rem;padding-left:1.1rem;color:#374151;font-size:0.895rem;line-height:1.8;position:relative;">
           <span style="position:absolute;left:0;font-weight:600;color:#6366f1;">${i+1}.</span>${escapeHtml(c.replace(/^\d+[.)]\s*/,""))}
         </p>`
      ).join("") : "";
    const conclusion = comm.closing_recommendation
      ? S.h("Conclusion") + `<p style="margin:0;color:#374151;font-size:0.895rem;line-height:1.8;font-style:italic;">${escapeHtml(comm.closing_recommendation)}</p>` : "";

    const card = document.createElement("div");
    card.className = "glass-card-static resolution-card mb-4";
    card.style.cssText = `animation-delay:${idx * 0.06}s;`;

    card.innerHTML = `
      <div class="res-card-header" style="border-bottom:1px solid #e5e7eb;padding-bottom:1rem;margin-bottom:0;">
        <div style="display:flex;align-items:flex-start;gap:0.875rem;flex-wrap:wrap;flex:1;">
          <span class="res-num">${escapeHtml(String(res.resolution_number ?? ""))}</span>
          <div style="flex:1;min-width:0;">
            <div class="res-title">${escapeHtml(res.title || res.resolution_type || "")}</div>
            <div style="display:flex;gap:0.4rem;margin-top:0.3rem;flex-wrap:wrap;">
              <span class="badge badge-${type.toLowerCase()}">${type}</span>
              ${res.resolution_type ? `<span class="badge badge-type">${escapeHtml(res.resolution_type)}</span>` : ""}
              ${res.director_name ? `<span class="badge badge-type">${escapeHtml(res.director_name)}</span>` : ""}
            </div>
          </div>
        </div>
        <div class="res-recs">
          <div class="rec-item">
            <div class="meta-label">MGMT</div>
            <span class="badge badge-for">${escapeHtml(comm.management_recommendation || "FOR")}</span>
          </div>
          <div class="rec-item">
            <div class="meta-label">INGOVERN</div>
            <span class="badge ${getRecClass(rec)}" style="font-size:0.82rem;padding:0.28rem 0.65rem;">${escapeHtml(rec)}</span>
          </div>
          ${comm.confidence ? `<div class="rec-item">
            <div class="meta-label">CONFIDENCE</div>
            <span class="badge ${getConfClass(comm.confidence)}">${escapeHtml(comm.confidence)}</span>
          </div>` : ""}
        </div>
      </div>
      <div class="res-card-body" style="padding-top:0.1rem;">
        ${intro}${summary}${commentary}${concerns}${conclusion}
      </div>
    `;
    container.appendChild(card);
  });
}

// ── Download PDF ──────────────────────────────────────────────────────────────
el("downloadReportBtn").addEventListener("click", downloadReport);

async function downloadReport() {
  const btn = el("downloadReportBtn");
  btn.disabled = true;
  const origHTML = btn.innerHTML;
  btn.innerHTML = `<span>Generating PDF…</span>`;

  try {
    const res = await fetch("/full_report/download");
    if (!res.ok) throw new Error(`Server returned ${res.status}`);

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    const cname = (state.company || "Report").replace(/\s+/g, "_");
    const fy    = (state.fiscalYear || "").replace(/\//g, "-");
    a.download = `${cname}_${fy}_InGovern_Report.pdf`.replace(/__+/g, "_");
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 1000);

    toast("Report downloaded!", "success");
  } catch (e) {
    toast(`Download failed: ${e.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = origHTML;
  }
}

// ── Approve ───────────────────────────────────────────────────────────────────
el("approveReportBtn").addEventListener("click", () => {
  const card = el("rpt-approve-card");
  if (card) card.scrollIntoView({ behavior: "smooth", block: "center" });
  setTimeout(() => { const inp = el("approvedBy"); if (inp) inp.focus(); }, 400);
});

el("submitApprovalBtn").addEventListener("click", async () => {
  const approvedBy = el("approvedBy").value.trim();
  const comments   = el("approvalComments").value.trim();

  if (!approvedBy) {
    toast("Please enter your name to approve.", "error");
    el("approvedBy").focus();
    return;
  }

  const btn = el("submitApprovalBtn");
  btn.disabled = true;
  try {
    const res = await apiFetch("/approve_report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved_by: approvedBy, comments }),
    });

    if (res.status === "success" || res.status === "approved") {
      const result = el("approvalResult");
      result.style.display = "";
      result.innerHTML = `<div style="display:inline-flex;align-items:center;gap:0.5rem;padding:0.5rem 1rem;background:rgba(34,197,94,0.12);border:1px solid rgba(34,197,94,0.25);border-radius:0.75rem;color:#22c55e;font-size:0.85rem;font-weight:600;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        Approved by ${escapeHtml(approvedBy)}
      </div>`;
      toast("Report approved!", "success");
    } else {
      throw new Error(res.message || "Approval failed");
    }
  } catch (e) {
    toast(`Approval error: ${e.message}`, "error");
  } finally {
    btn.disabled = false;
  }
});

// ── Start Over ────────────────────────────────────────────────────────────────
function startOver() {
  state.reportData = null;
  state.company    = "";
  state.fiscalYear = "";
  el("pageTitle").textContent    = "InGovern Governance Agent";
  el("pageSubtitle").textContent = "AI-powered proxy advisory for Indian listed companies";
  el("sessionBadge").style.display = "none";
  resetForm();
  showView("home");
}

el("startOverBtn").addEventListener("click", startOver);
el("startOverBtn2").addEventListener("click", startOver);

// ── Utilities ─────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getRecClass(rec) {
  const r = (rec || "").toUpperCase().replace(/\s/g, "");
  if (r === "AGAINST") return "badge-against";
  if (r === "FOR*")    return "badge-for-star";
  if (r === "FOR")     return "badge-for";
  return "badge-neutral";
}

function getConfClass(conf) {
  const c = (conf || "").toLowerCase();
  if (c === "high")   return "badge-high";
  if (c === "medium") return "badge-medium";
  if (c === "low")    return "badge-low";
  return "badge-neutral";
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
(function init() {
  renderHistory();
  showView("home");
})();
