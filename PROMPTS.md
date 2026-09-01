# InGovern — All Prompts Reference

This file documents every prompt used in the InGovern pipeline: where it lives, what model it targets, and what it does.

---

## 1. Resolution Extraction Prompt

**File:** `prompts/resolution_prompt.py`  
**Variable:** `RESOLUTION_PROMPT`  
**Used by:** `resolution_extractor/extract_resolutions.py`  
**Model:** `anthropic/claude-haiku-3.5` (via OpenRouter)  
**Purpose:** Extracts a structured list of shareholder resolutions from raw PDF text.

### Description
A lightweight extraction prompt. Given the full text of a notice PDF, it instructs the model to identify every resolution, assign it a number, title, and type, and return clean JSON — no commentary, no analysis.

### Resolution Types Recognised
`Director Appointment`, `RPT`, `Borrowing`, `ESOP`, `Remuneration`, `Auditor`, `Merger`, `Capital Raise`, `CSR`, `Dividend`, `Other`

### Prompt Text

```
You are an InGovern Governance Analyst.

Extract every shareholder resolution.

Return:

Resolution Number
Resolution Title
Resolution Type

Possible Types:
Director Appointment / RPT / Borrowing / ESOP / Remuneration / Auditor /
Merger / Capital Raise / CSR / Dividend / Other

Return JSON only.
```

---

## 2. AI Analyzer — Governance Analysis Prompt

**File:** `recommendation_engine/ai_analyzer.py`  
**Variables:** `_SYSTEM_PROMPT`, `_USER_TEMPLATE`  
**Used by:** `api/ai_analyze.py` (individual resolution analysis endpoint)  
**Model:** `anthropic/claude-haiku-3-5` (via OpenRouter)  
**Purpose:** Lightweight per-resolution governance analysis — used as a pre-analysis / enrichment step before the main commentary generator runs.

### Description
A structured analysis prompt that takes a single resolution (plus RAG-retrieved precedents and policy) and returns a JSON object covering governance analysis, policy compliance, risk assessment, a recommendation (`FOR` / `FOR*` / `AGAINST`), and confidence level. It is faster and cheaper than the main commentary prompt — used to populate `governance_concerns` and `recommendation` fields early in the pipeline.

### System Prompt

```
You are a senior institutional governance analyst specializing in
Indian listed companies (SEBI, Companies Act 2013, LODR). You analyze AGM, EGM, and
Postal Ballot resolutions for proxy advisory firms.

You always return your analysis as a valid JSON object. Never include markdown fences or
extra prose — only raw JSON.
```

### User Template

Injected fields:
- `{resolution_json}` — the resolution object (title, text, type, explanation)
- `{precedents_json}` — similar past resolutions retrieved from Supabase RAG
- `{policy_json}` — applicable governance policies

```
Analyze the following governance resolution and return a JSON object
with EXACTLY these keys:

{
  "governance_analysis":    "<2-3 sentence analysis of the governance quality>",
  "policy_analysis":        "<which policies / SEBI regulations apply and whether they are satisfied>",
  "historical_comparison":  "<comparison with similar historical cases if any, else 'No comparable cases'>",
  "risk_assessment":        "<identified risks: related-party, dilution, conflict-of-interest, etc.>",
  "governance_concerns":    ["<concern 1>", "<concern 2>"],
  "recommendation":         "FOR" | "FOR*" | "AGAINST",
  "confidence":             "High" | "Medium" | "Low",
  "reasoning":              ["<point 1>", "<point 2>", "<point 3>"]
}

Resolution details:
{resolution_json}

Historical precedents:
{precedents_json}

Policy in effect:
{policy_json}
```

### Output Schema

| Field | Type | Description |
|---|---|---|
| `governance_analysis` | string | 2–3 sentence qualitative assessment |
| `policy_analysis` | string | Applicable SEBI / CA 2013 regulations and compliance status |
| `historical_comparison` | string | Comparable past cases from RAG or "No comparable cases" |
| `risk_assessment` | string | RPT, dilution, conflict-of-interest risks |
| `governance_concerns` | string[] | Specific concerns, each as a plain string |
| `recommendation` | `FOR` / `FOR*` / `AGAINST` | Vote recommendation |
| `confidence` | `High` / `Medium` / `Low` | Model confidence |
| `reasoning` | string[] | Supporting reasoning points |

---

## 3. InGovern Commentary Generator — Main Prompt

**File:** `recommendation_engine/ingovern_commentary.py`  
**Variables:** `_SYSTEM_PROMPT`, `_USER_TEMPLATE`, `_NOTICE_TYPE_GUIDANCE`  
**Used by:** `api/commentary.py` → `GET /generate_commentary`  
**Model:** `google/gemini-2.5-flash` (via OpenRouter)  
**Temperature:** 0.1 | **Max tokens:** 6,000  
**Purpose:** The primary commentary generation step. Produces full institutional-grade InGovern-style vote recommendation reports for every resolution in the uploaded notice.

### Description
This is the most comprehensive prompt in the pipeline. It acts as a senior proxy advisory analyst and produces a five-section structured report per resolution:

1. **Introduction** — 2–3 sentences: what the company proposes and the legal basis.
2. **Summary** — minimum 5 paragraphs covering proposal terms, director/matter background, financials, regulatory compliance, and additional details.
3. **InGovern Commentary** — minimum 3 paragraphs covering governance quality, specific findings, and InGovern's analytical position.
4. **Governance Concerns** — numbered list, each citing a specific regulation or best-practice guideline with textual evidence.
5. **Closing Recommendation** — one sentence: `FOR`, `FOR*`, or `AGAINST`.

RAG context is injected before every call:
- **Style examples** — retrieved from Supabase (`resolution_type` + `notice_type` match), giving the model real InGovern writing samples to imitate.
- **Precedents** — similar past resolutions with their outcomes, for recommendation calibration.

### Analytical Framework (enforced by the system prompt)

| Section | What is checked |
|---|---|
| **Board Composition** | Chair independence, Audit Committee composition (Reg 18 SEBI LODR), NRC composition (Reg 19), tenures >10 years, directors on >7 boards (Reg 17A) |
| **Director Appointments** | DIN, age, qualifications, tenure, committee memberships, remuneration, retirement-by-rotation (Sec 152(6) CA 2013), family relationships |
| **Auditor / Financials** | Audit firm, registration, term, qualifications, emphasis of matter, CARO, subsidiary audits, secretarial audit |
| **Remuneration** | All components with amounts, comparison to last approved/paid, monetary cap, performance linkage |
| **RPT** | Party names, transaction type and value, Audit Committee approval, arm's-length status, Reg 23 SEBI LODR threshold |
| **Recommendation Logic** | FOR = routine + adequate disclosure; FOR* = vote FOR but raise concerns; AGAINST = material non-compliance or inadequate disclosure |

### Notice-Type Guidance (injected per notice type)

| Notice Type | Guidance injected |
|---|---|
| `AGM` | Ordinary vs special business treatment; brief for ordinary, detailed for special |
| `EGM` | Non-routine matters — M&A, RPT, capital structure; require deeper analysis |
| `Postal Ballot` | Voted remotely; self-contained notice; each resolution analysed independently |
| `NCM` | NCLT-convened; scheme terms, appointed date, swap ratio, fairness opinion, minority impact |

### System Prompt (condensed)

```
You are a senior proxy advisory analyst at InGovern Research Services,
India's leading independent corporate governance advisory firm.

CARDINAL RULE — NO HALLUCINATION, NO PLACEHOLDERS, NO INVENTION
• Use ONLY facts explicitly present in resolution_text, explanation, or board_context.
• NEVER write [Director's Name], [Auditor's Name], Rs. X crore, or ANY bracketed placeholder.
• If a fact is not in the provided text → OMIT it entirely.

[Analytical Framework: Board Composition / Director Appointments /
 Auditor / Remuneration / RPT / Recommendation Logic]

OUTPUT — five sections, all mandatory:
1. introduction       : 2–3 sentences, legal basis
2. summary_paragraphs : ≥5 paragraphs (terms, background, financials, compliance, extras)
3. ingovern_commentary: ≥3 paragraphs (governance quality, findings, position)
4. governance_concerns: numbered list citing regulation + text evidence
5. closing_recommendation: one sentence, FOR / FOR* / AGAINST

You ALWAYS return a valid JSON object ONLY — no markdown fences, no extra prose.
```

### User Template Injected Fields

| Placeholder | Source |
|---|---|
| `{notice_type}` | Session metadata |
| `{notice_type_guidance}` | `_NOTICE_TYPE_GUIDANCE[notice_type]` |
| `{company_name}` | Session / form input |
| `{financial_year}` | Session / form input |
| `{resolution_json}` | Resolution dict (text + explanatory statement combined, max 6,000 chars) |
| `{board_json}` | Full board of directors list from session |
| `{mgmt_rec}` | Management recommendation from notice |
| `{cover_rec_hint}` | Pre-printed InGovern recommendation if available |
| `{precedents_json}` | RAG: similar past resolutions from Supabase |
| `{style_examples}` | RAG: real InGovern writing style excerpts from Supabase |
| `{res_no}` | Resolution number |

### Output Schema

| Field | Type | Description |
|---|---|---|
| `resolution_number` | int | Resolution number from notice |
| `resolution_title` | string | Exact title from the notice |
| `resolution_type` | `Ordinary` / `Special` | Vote type |
| `management_recommendation` | `FOR` / `AGAINST` / `ABSTAIN` | As stated in the notice |
| `ingovern_recommendation` | `FOR` / `FOR*` / `AGAINST` | InGovern's recommendation |
| `ingovern_rationale` | string | 3–4 sentence rationale |
| `confidence` | `High` / `Medium` / `Low` | Model confidence |
| `introduction` | string | 2–3 sentence introduction paragraph |
| `summary_paragraphs` | string[] | ≥5 analytical paragraphs |
| `ingovern_commentary` | string[] | ≥3 governance commentary paragraphs |
| `governance_concerns` | string[] | Numbered concerns citing regulations |
| `closing_recommendation` | string | Final one-sentence recommendation |
| `risk_flags` | string[] | Additional risk flags from the text |
| `key_facts` | object | Extracted facts (name, DIN, age, tenure, remuneration, etc.) |
| `ai_powered` | bool | Always `true` on success |

---

