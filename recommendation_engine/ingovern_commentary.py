"""
InGovern-style governance commentary generator.

RAG-powered: retrieves writing style examples and similar past resolutions from
Supabase (pgvector) before each generation so output progressively matches
InGovern's actual voice, notice-type structure, and analytical depth.

STRICT DATA POLICY: the AI must never invent, assume, or hallucinate any fact.
Every name, number, date, or detail in the output must be explicitly present in
the resolution_text or explanation provided. If a fact is unknown, omit it.

Uses OpenRouter (no OpenAI SDK). Falls back gracefully on any error.
"""

import re
import json
import requests

from config.config import OPENROUTER_API_KEY, OPENROUTER_MODEL
from database.rag_store import retrieve_style_examples, search_similar_resolutions

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── Notice-type structure notes injected into the prompt ─────────────────────

_NOTICE_TYPE_GUIDANCE = {
    "AGM": """AGM (Annual General Meeting) notices typically cover:
- Ordinary business: adoption of financial statements, dividend declaration,
  director rotations, auditor appointment/ratification
- Special business: remuneration approvals, related party transactions, ESOPs,
  charter amendments, capital raises
AGM reports follow a standard multi-resolution structure. Ordinary business
resolutions are treated briefly unless there are specific concerns; special
business resolutions receive detailed analysis.""",

    "EGM": """EGM (Extraordinary General Meeting) notices are called for specific
urgent matters not covered in the regular AGM cycle. Common EGM items:
- Approval of significant transactions (mergers, acquisitions, demergers)
- Related party transactions requiring shareholder approval
- Capital structure changes (rights issue, QIP, preferential allotment)
- Changes in key managerial positions
EGM resolutions typically require deeper analysis as they are non-routine.""",

    "Postal Ballot": """Postal Ballot notices are used for specific resolutions
that require shareholder consent between AGMs. Common Postal Ballot items:
- Director appointments/removals
- Related party transactions
- ESOP scheme approvals
- Material amendments to MOA/AOA
- Capital raises requiring special resolution
Since shareholders vote remotely without a meeting, the notice must be self-
contained with complete explanatory statements. Each resolution should be
analysed independently and thoroughly.""",

    "NCM": """NCM (National Company Law Tribunal-convened Meeting) or Court-convened
meetings are held for approvals related to:
- Mergers, amalgamations, demergers, restructurings under the Companies Act 2013
- Compromise or arrangement with creditors/members under Sections 230-232
NCM resolutions require analysis of the scheme terms, appointed date, swap
ratios, fairness opinion, and impact on minority shareholders.""",
}

# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a senior proxy advisory analyst at InGovern Research Services,
India's leading independent corporate governance advisory firm.

You write institutional-quality governance vote recommendation reports for Indian listed
companies — AGM, EGM, Postal Ballot, and NCM. Your analysis is read by institutional
investors who rely on it to make voting decisions worth billions of rupees.

══════════════════════════════════════════════════════════════════
CARDINAL RULE — NO HALLUCINATION, NO PLACEHOLDERS, NO INVENTION
══════════════════════════════════════════════════════════════════
• Use ONLY facts explicitly present in resolution_text, explanation, or board_context.
• NEVER write [Director's Name], [Auditor's Name], Rs. X crore, or ANY bracketed placeholder.
• If an auditor firm is named in the text → use that name. If not → do not name one.
• If financial figures appear in explanation → quote them exactly.
• If a fact is not in the provided text → OMIT it entirely.
══════════════════════════════════════════════════════════════════

ANALYTICAL FRAMEWORK (apply to every resolution):

A. BOARD COMPOSITION (always analyse using board_context):
   • Is the Board Chairman an Independent Director? If not → flag under Section 149/SEBI LODR.
   • Is there a Lead Independent Director given a non-independent Chair?
   • Audit Committee: does it consist ONLY of Independent Directors per Regulation 18 SEBI LODR?
   • NRC: does it consist ONLY of Independent Directors per Regulation 19 SEBI LODR?
   • Independent Directors with >10 years tenure on board → flag (best practice guideline).
   • Director sitting on >7 listed company boards → flag per Regulation 17A SEBI LODR.

B. DIRECTOR APPOINTMENTS / REAPPOINTMENTS:
   • DIN, age (if stated), qualifications (if stated), current board positions (if stated).
   • Tenure (first appointment date if stated → calculate years to today if calculable from text).
   • Committee memberships (from board_context).
   • Remuneration drawn (if stated in explanation) — list all components.
   • Retirement by rotation: confirm compliance with Section 152(6) Companies Act 2013.
   • Family relationships with other directors (if mentioned in text).

C. AUDITOR / FINANCIAL STATEMENT RESOLUTIONS:
   • Auditor name, firm registration number, appointment date, term — ONLY if in text.
   • Any qualifications, reservations, emphasis of matter, or "Other Matters" in audit report — quote verbatim.
   • CARO compliance issues.
   • Audit of subsidiaries by other auditors — mention if stated with figures.
   • Secretarial audit findings (if stated).

D. REMUNERATION RESOLUTIONS:
   • List every remuneration component with amounts if stated (basic, perquisites, commission,
     performance bonus, phantom options, PF/gratuity).
   • Compare proposed vs last approved vs last paid — ONLY if those figures appear in text.
   • Flag: no monetary cap, no peer benchmarking mentioned, no increment cap, combined
     appointment + remuneration resolution (should be two separate resolutions per CA 2013).
   • Apply InGovern voting guideline: variable component should dominate, must be performance-linked.

E. RELATED PARTY TRANSACTIONS:
   • Party names, transaction type, estimated value (ONLY if in text).
   • Whether Audit Committee approved, whether it is arm's length.
   • Regulation 23 SEBI LODR threshold checks.

F. RECOMMENDATION LOGIC:
   • FOR:     routine resolution, adequate disclosure, no material concerns.
   • FOR*:    vote FOR but shareholders should raise specific listed concerns at the meeting.
   • AGAINST: material governance concerns, inadequate disclosure, non-compliance with regulations,
              or remuneration structure that fails InGovern voting guidelines.
   • Do NOT default to FOR just because management recommends FOR.
   • If concerns exist → use FOR* or AGAINST as warranted.

OUTPUT — five sections, all mandatory:

1. introduction      : 2-3 sentences. What the company proposes and the legal basis (cite sections/regulations from the text).
2. summary_paragraphs: minimum 5 paragraphs.
   - Para 1: Precise proposal terms (dates, tenure, scope, vote type).
   - Para 2: Person/matter background using bullet points (•) for every specific fact.
   - Para 3: Financial / quantitative details (quote exact figures if present; state "not disclosed in the notice" if absent).
   - Para 4: Regulatory compliance assessment (cite specific regulation numbers).
   - Para 5+: Any additional material details from the explanatory statement.
3. ingovern_commentary: minimum 3 paragraphs.
   - Para 1: Governance quality of this specific resolution.
   - Para 2: Specific positive / negative findings, citing actual text content.
   - Para 3: InGovern's analytical position, agreement or divergence from management.
4. governance_concerns: numbered list. Each item MUST cite a regulation AND reference text content.
   Structure: "N. [Regulation X / Section Y / Best Practice] — <specific concern referencing the text>."
   Zero concerns is valid only for completely routine, fully disclosed resolutions.
5. closing_recommendation: one sentence — "We recommend shareholders vote FOR/FOR*/AGAINST
   the resolution on <subject> of <company_name>."

STYLE:
• Formal, precise, analytical — written for institutional investors, not retail audiences.
• Use exact section/regulation numbers: Sec 149/152/196/197 CA 2013; Reg 16/17/18/19/23/25 SEBI LODR; SS-2.
• Bullet points (•) for listing facts, never for analytical paragraphs.
• Never use vague praise ("robust governance", "commitment to transparency") without evidence.
• Every claim must have a textual basis.

You ALWAYS return a valid JSON object ONLY — no markdown code fences, no extra prose outside JSON."""


# ── User template ─────────────────────────────────────────────────────────────

_USER_TEMPLATE = """Write the full InGovern Vote Recommendation for the resolution below.

=== NOTICE TYPE: {notice_type} ===
{notice_type_guidance}

=== COMPANY: {company_name} | FINANCIAL YEAR: {financial_year} ===

=== RESOLUTION DATA (resolution_text + explanation — your PRIMARY source) ===
{resolution_json}

=== BOARD OF DIRECTORS CONTEXT (use for board composition analysis) ===
{board_json}

=== MANAGEMENT RECOMMENDATION: {mgmt_rec} ===

=== PRE-EXTRACTED INGOVERN RECOMMENDATION (agree or override with reasoning) ===
{cover_rec_hint}

=== SIMILAR PAST INGOVERN RESOLUTIONS (calibrate recommendation) ===
{precedents_json}

=== REAL INGOVERN WRITING STYLE EXAMPLES — MATCH THIS TONE AND DEPTH ===
These are verbatim excerpts from published InGovern {notice_type} reports.
Copy the analytical depth, numbered concern format, and bullet-point style.
Do NOT copy any names, figures, or content. Use your own analysis of the resolution above.
{style_examples}

---
STEP-BY-STEP INSTRUCTIONS:

STEP 1 — DATA EXTRACTION (do this mentally before writing):
Extract from resolution_text + explanation ONLY what is explicitly stated:
□ Director name, DIN, age, qualifications, first appointment date
□ Remuneration: every component with amounts if stated
□ Auditor: name, registration number, appointment AGM, term
□ Audit findings: qualifications, other matters, CARO issues
□ Transaction: parties, value, nature, Audit Committee approval
□ Effective date, tenure, vote type (Ordinary / Special)

STEP 2 — BOARD ANALYSIS (always do this):
From board_context, check:
□ Is Chairman an Independent Director?
□ Does Audit Committee have any non-independent members?
□ Does NRC have any non-independent members?
□ Any Independent Director with >10 years tenure?
□ Any director on >7 listed boards?

STEP 3 — WRITE the five sections with full analytical depth.
STEP 4 — DERIVE recommendation: FOR / FOR* / AGAINST — justify it.

Return ONLY this JSON (no markdown, no preamble):
{{
  "resolution_number":           {res_no},
  "resolution_title":            "<exact title from notice>",
  "resolution_type":             "<Ordinary|Special>",
  "management_recommendation":   "<FOR|AGAINST|ABSTAIN>",
  "ingovern_recommendation":     "<FOR|FOR*|AGAINST>",
  "ingovern_rationale":          "<3-4 sentences grounded in text>",
  "confidence":                  "<High|Medium|Low>",
  "introduction":                "<2-3 sentences: proposal + legal basis>",
  "summary_paragraphs": [
    "<Para 1: proposal terms>",
    "<Para 2: background with • bullets for each fact>",
    "<Para 3: financial/quantitative details — quote figures or state not disclosed>",
    "<Para 4: regulatory compliance assessment>",
    "<Para 5+: additional material details from explanatory statement>"
  ],
  "ingovern_commentary": [
    "<Para 1: governance quality of this resolution>",
    "<Para 2: specific findings with text references>",
    "<Para 3: InGovern analytical position vs management>"
  ],
  "governance_concerns": [
    "1. [Regulation / Section / Best Practice] — <specific concern referencing the text>",
    "2. ..."
  ],
  "closing_recommendation": "We recommend shareholders vote <FOR|FOR*|AGAINST> the resolution on <subject> of {company_name}.",
  "risk_flags":   ["<risk from text only>"],
  "key_facts": {{
    "director_name":    "<from text or empty string>",
    "din":              "<from text or empty string>",
    "age":              "<from text or empty string>",
    "tenure":           "<from text or empty string>",
    "qualifications":   "<from text or empty string>",
    "auditor":          "<from text or empty string>",
    "remuneration":     "<from text or empty string>",
    "shareholding":     "<from text or empty string>",
    "related_party":    "<from text or empty string>",
    "board_seats":      "<from text or empty string>",
    "transaction_value":"<from text or empty string>"
  }},
  "ai_powered": true
}}"""


# ── OpenRouter call ───────────────────────────────────────────────────────────

def _call_openrouter(prompt: str) -> dict:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://ingovern.ai",
        "X-Title":       "InGovern Governance Agent",
    }

    payload = {
        "model": "google/gemini-2.0-flash-001",
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens":  6000,
    }

    r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=None)
    if r.status_code != 200:
        raise RuntimeError(f"OpenRouter {r.status_code}: {r.text[:300]}")

    content = (
        r.json()
        .get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    ).strip()

    # Strip markdown fences (Gemini often wraps JSON in ```json ... ```)
    content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE).strip()
    content = re.sub(r"\s*```$", "", content).strip()

    # Find outermost JSON object in case of leading/trailing prose
    brace_start = content.find("{")
    brace_end   = content.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        content = content[brace_start:brace_end + 1]

    return json.loads(content)


# ── RAG context retrieval ─────────────────────────────────────────────────────

def _fetch_kb_context(
    resolution_type: str,
    title: str,
    res_text: str,
    ig_rec_hint: str,
    notice_type: str = "AGM",
) -> tuple[str, str]:
    """
    Fetch style examples + similar precedents from Supabase, filtered by
    resolution_type and notice_type for maximum relevance.
    """
    # Style examples: match resolution type + recommendation + notice type
    ingovern_rec_filter = ig_rec_hint if ig_rec_hint in ("FOR", "FOR*", "AGAINST") else None
    style_texts = retrieve_style_examples(
        resolution_type = resolution_type,
        ingovern_rec    = ingovern_rec_filter,
        limit           = 3,
    )
    if style_texts:
        style_str = "\n\n---\n".join(
            f"[Example {i+1}]\n{ex[:2000]}" for i, ex in enumerate(style_texts)
        )
    else:
        style_str = "No style examples available for this resolution type — use InGovern's standard formal tone."

    # Similar past resolutions: match resolution type + notice type
    query = f"{notice_type} {resolution_type} {title} {res_text[:400]}"
    precedents = search_similar_resolutions(
        query_text      = query,
        resolution_type = resolution_type,
        notice_type     = notice_type if notice_type != "AGM" else None,  # AGM is broadest, don't filter
        limit           = 3,
    )
    if precedents:
        prec_list = []
        for p in precedents:
            cj = p.get("commentary_json") or {}
            if isinstance(cj, str):
                try:
                    cj = json.loads(cj)
                except Exception:
                    cj = {}
            prec_list.append({
                "company":       p.get("company_name"),
                "year":          p.get("financial_year"),
                "notice_type":   p.get("notice_type"),
                "resolution":    p.get("resolution_title"),
                "ingovern_rec":  p.get("ingovern_rec"),
                "closing":       cj.get("closing_recommendation", ""),
                "concerns":      cj.get("governance_concerns", [])[:3],
                "body":          cj.get("body_text", "")[:600],
            })
        prec_str = json.dumps(prec_list, indent=2, ensure_ascii=False)
    else:
        prec_str = json.dumps([], indent=2)

    return style_str, prec_str


# ── Main commentary generator ─────────────────────────────────────────────────

def generate_ingovern_commentary(
    resolution: dict,
    board_directors: list = None,
    notice_type: str = "AGM",
    company_name: str = "",
    financial_year: str = "",
) -> dict:
    """
    Generate InGovern-style commentary for a single resolution.
    RAG-powered: fetches writing style examples (matched by resolution type +
    notice type) and similar precedents before calling the LLM.
    """
    res_no    = resolution.get("resolution_number", 1)
    title     = resolution.get("title", resolution.get("resolution_type", ""))
    res_type  = "Special" if resolution.get("special_resolution") else "Ordinary"
    mgmt_rec  = resolution.get("management_recommendation", "FOR")
    cover_rec = resolution.get("cover_ingovern_rec", "")
    res_text  = resolution.get("resolution_text", "") or ""
    expl_text = resolution.get("explanation", "") or ""

    # Classify for KB lookup
    from scripts.seed_knowledge_base import _classify_resolution_type
    resolution_type = _classify_resolution_type(title)

    # Fetch KB context filtered by notice type
    style_str, prec_str = _fetch_kb_context(
        resolution_type, title, res_text, cover_rec, notice_type
    )

    # Build clean resolution payload — exclude heavy/redundant keys
    safe_res = {k: v for k, v in resolution.items()
                if k not in ("policy", "precedents", "recommendation",
                             "governance_factors", "governance_evaluation",
                             "ingovern_commentary", "ai_analysis")}
    # Combine resolution_text + explanation for richer context
    combined_text = res_text
    if expl_text and expl_text not in res_text:
        combined_text = res_text + "\n\n--- EXPLANATORY STATEMENT ---\n" + expl_text
    safe_res["resolution_text"] = combined_text[:6000] + ("…" if len(combined_text) > 6000 else "")

    cover_hint = (
        f"Pre-printed InGovern recommendation: {cover_rec}" if cover_rec
        else "No pre-printed recommendation — derive from analysis."
    )

    notice_guidance = _NOTICE_TYPE_GUIDANCE.get(notice_type, _NOTICE_TYPE_GUIDANCE["AGM"])

    prompt = _USER_TEMPLATE.format(
        notice_type          = notice_type,
        notice_type_guidance = notice_guidance,
        company_name         = company_name or resolution.get("company_name", "the Company"),
        financial_year       = financial_year or "",
        resolution_json      = json.dumps(safe_res, indent=2, ensure_ascii=False),
        mgmt_rec             = mgmt_rec,
        precedents_json      = prec_str,
        policy_json          = json.dumps(resolution.get("policy", {}), indent=2, ensure_ascii=False),
        board_json           = json.dumps(board_directors or [], indent=2, ensure_ascii=False),
        cover_rec_hint       = cover_hint,
        style_examples       = style_str,
        res_no               = res_no,
    )

    try:
        result = _call_openrouter(prompt)

        result.setdefault("resolution_number",         res_no)
        result.setdefault("resolution_title",          title)
        result.setdefault("resolution_type",           res_type)
        result.setdefault("management_recommendation", mgmt_rec)
        result.setdefault("ingovern_recommendation",   "FOR")
        result.setdefault("ingovern_rationale",        "")
        result.setdefault("confidence",                "Medium")
        result.setdefault("introduction",              "")
        result.setdefault("summary_paragraphs",        [])
        result.setdefault("ingovern_commentary",       [])
        result.setdefault("governance_concerns",       [])
        result.setdefault("closing_recommendation",    "")
        result.setdefault("risk_flags",                [])
        result.setdefault("key_facts",                 {})
        result["ai_powered"] = True
        result["error"]      = None

        rec = str(result.get("ingovern_recommendation", "FOR")).strip().upper()
        if "AGAINST" in rec:
            result["ingovern_recommendation"] = "AGAINST"
        elif "*" in rec or "FOR*" in rec:
            result["ingovern_recommendation"] = "FOR*"
        else:
            result["ingovern_recommendation"] = "FOR"

        return result

    except Exception as exc:
        fallback_rec = cover_rec if cover_rec in ("FOR", "FOR*", "AGAINST") else "FOR"
        return {
            "resolution_number":         res_no,
            "resolution_title":          title,
            "resolution_type":           res_type,
            "management_recommendation": mgmt_rec,
            "ingovern_recommendation":   fallback_rec,
            "ingovern_rationale":        f"AI unavailable: {str(exc)[:100]}",
            "confidence":                "Low",
            "introduction":              "",
            "summary_paragraphs":        [],
            "ingovern_commentary":       [],
            "governance_concerns":       [],
            "closing_recommendation":    f"We recommend shareholders vote {fallback_rec} this resolution.",
            "risk_flags":                [],
            "key_facts":                 {},
            "ai_powered":                False,
            "error":                     str(exc),
        }
