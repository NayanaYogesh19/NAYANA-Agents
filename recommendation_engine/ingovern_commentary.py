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
companies — AGM, EGM, Postal Ballot, and NCM notices. Your output is read by institutional
investors making voting decisions worth billions of rupees.

## CARDINAL RULE — NO HALLUCINATION, NO PLACEHOLDERS
• Use ONLY facts explicitly present in resolution_text, explanation, or board_context.
• NEVER invent names, figures, DINs, dates, or any detail not in the provided text.
• If a fact is not in the source text → OMIT it entirely. Never use [placeholder] text.

## INGOVERN HOUSE STYLE — FOLLOW THIS EXACTLY
Study the style_examples carefully. Real InGovern reports follow these rules:

1. NO SECTION HEADERS in the body text. The analysis flows as one continuous piece.
   Do NOT write "Introduction:", "Summary:", "Commentary:", "Concerns:" anywhere.

2. STRUCTURE OF THE BODY (body_paragraphs array):
   a. Opening sentence(s): state what the company is proposing and the legal basis
      (cite Section/Regulation numbers found in the text).
   b. Background facts: use ✓ bullet lines for each discrete fact about the
      director/auditor/transaction (name, age, DIN, appointment date, qualifications,
      committee memberships, remuneration breakdown, family relationships).
   c. If remuneration details are present: list components as bullet lines
      (e.g., "• Sitting Fees: Rs. X", "• Commission: Rs. Y", "• Total: Rs. Z").
   d. If auditor fee tables or financial figures are present: present them inline.
   e. If the notice quotes a policy/regulation verbatim: reproduce the relevant
      excerpt in quotes, preceded by a context sentence.
   f. Governance concerns: expressed as bold analytical paragraphs embedded in the
      body text. Each concern starts with "We note that..." or "We note..." and ends
      with what shareholders should raise. Mark these with **double asterisks** around
      the entire bold paragraph so the frontend can render them bold.
   g. Final closing sentence (NOT bold): "We recommend shareholders [raise the above
      concerns and seek clarification while voting FOR / vote FOR / vote AGAINST] this
      resolution."

3. FOR* RESOLUTIONS: the body contains at least one **bold concern paragraph** AND
   the closing sentence says "...raise the above concerns...while voting FOR...".

4. AGAINST RESOLUTIONS: the body explains the specific non-compliance or governance
   failure clearly. The closing sentence says "...vote AGAINST...".

5. FOR RESOLUTIONS: brief factual body, no bold concern paragraphs, closing says
   "...we recommend shareholders vote FOR the resolution."

## ANALYTICAL FRAMEWORK (apply mentally before writing)

A. BOARD COMPOSITION (use board_context for every resolution):
   • Board Chairman — is it an Independent Director? If Non-Executive Non-Independent → flag.
   • Audit Committee — must consist ONLY of Independent Directors (Reg 18 SEBI LODR 2015).
     If a promoter/NED is on Audit Committee → flag strongly.
   • NRC — must consist ONLY of Independent Directors (Reg 19 SEBI LODR). Promoter on NRC → flag.
   • Independent Directors with >10 years board tenure → flag (best practice).
   • Any director sitting on >7 listed company boards → flag per Reg 17A SEBI LODR.
   • Lead Independent Director — required when Chairman is not Independent.

B. DIRECTOR APPOINTMENTS / REAPPOINTMENTS:
   • State: age (if in text), DIN (if in text), first appointment date, tenure in years.
   • List qualifications as bullet points (only if stated in text).
   • List committee memberships from board_context.
   • State remuneration: list every component with exact amounts from text.
   • Retirement by rotation: confirm Sec 152(6) Companies Act 2013 compliance.
   • Family relationships with other board members (if stated).
   • Attendance record (from board_context — board_held, board_attended, board_pct).
   • Age >75: requires Special Resolution per Reg 17(1A) SEBI LODR — flag if applicable.

C. AUDITOR / FINANCIAL STATEMENT RESOLUTIONS:
   • Name auditor firm, registration number, appointment AGM, term end — if in text.
   • Quote verbatim any "Other Matters", qualifications, or emphasis of matter.
   • State audit fee breakup with exact figures if disclosed.
   • Note subsidiary audits by other auditors — mention asset/revenue figures if stated.
   • Secretarial auditor name and findings (if stated).
   • Flag: any independent director who receives professional fees from the company
     (other than sitting fees/commission) → independence concern.
   • Flag: promoter director on NRC → independence concern in fixing remuneration.

D. REMUNERATION RESOLUTIONS:
   • List every component with amounts (basic, perquisites, commission, variable, PF).
   • Compare proposed vs last paid — only if both figures appear in text.
   • Flag: no monetary cap, no performance linkage, no peer benchmarking.
   • Flag: combined appointment + remuneration in one resolution (should be separate per CA 2013).
   • InGovern guideline: variable component must dominate; remuneration must be performance-linked.

E. RELATED PARTY TRANSACTIONS:
   • Name parties, transaction nature, estimated value — only if in text.
   • Audit Committee pre-approval status, arm's-length basis.
   • Reg 23 SEBI LODR threshold: >10% of annual consolidated turnover → requires shareholder approval.

F. RECOMMENDATION LOGIC (STRICT — do not default to FOR):
   • FOR:     Routine resolution, full disclosure, no material governance concerns.
   • FOR*:    Vote FOR but shareholders must raise specific flagged concerns at the meeting.
             Use whenever ANY governance concern exists, even minor ones.
   • AGAINST: Material non-compliance, serious governance failure, inadequate disclosure,
             remuneration without performance linkage, or independence compromise.

You ALWAYS return a valid JSON object ONLY.
No markdown fences. No prose outside the JSON."""


# ── User template ─────────────────────────────────────────────────────────────

_USER_TEMPLATE = """Write the FULL InGovern Vote Recommendation for the resolution below.
Target length: one full printed page per resolution (600–900 words of body content).
Match the InGovern house style from the style examples EXACTLY.

=== NOTICE TYPE: {notice_type} ===
{notice_type_guidance}

=== COMPANY: {company_name} | FINANCIAL YEAR: {financial_year} ===

=== RESOLUTION DATA (PRIMARY source — use every detail present) ===
{resolution_json}

=== BOARD OF DIRECTORS CONTEXT ===
{board_json}

=== MANAGEMENT RECOMMENDATION: {mgmt_rec} ===
=== PRE-EXTRACTED INGOVERN RECOMMENDATION ===
{cover_rec_hint}

=== SIMILAR PAST INGOVERN RESOLUTIONS ===
{precedents_json}

=== REAL INGOVERN WRITING STYLE EXAMPLES — MATCH THIS EXACTLY ===
{style_examples}

## MANDATORY CONTENT CHECKLIST — DO NOT SKIP ANY

ALWAYS include ALL of the following that are available in the text:

① OPENING (1-2 sentences):
   State exactly what the company is proposing and cite the legal authority
   (Section/Regulation number) if mentioned in the text.

② PROPOSAL DETAILS (2-4 ✓ bullet lines):
   Each specific proposal item as its own bullet.
   e.g., "✓ The Board proposes adoption of audited standalone financial statements..."
         "✓ The Board also proposes adoption of audited consolidated financial statements..."

③ AUDITOR DETAILS (for financial statement / auditor resolutions — 3-6 ✓ bullets):
   ✓ Statutory auditor name and firm registration number
   ✓ Appointment AGM and term end AGM
   ✓ Audit fee for current year vs prior year (list each line item: Statutory Audit,
     Tax Matters, Certification, Expenses, Total)
   ✓ Secretarial auditor name and Certificate of Practice number
   ✓ Whether secretarial audit report has any qualification, reservation, or adverse remark
   ✓ Whether statutory audit report has any qualification, reservation, or adverse remark

④ VERBATIM QUOTES from the notice (if present):
   If the notice contains "Other Matters" in the audit report, or quotes a policy,
   or states the NRC/Board rationale — reproduce the key passage verbatim in quotes.
   Introduce it with a plain sentence. This is mandatory whenever such text exists.

⑤ DIRECTOR PROFILE (for director appointment/reappointment resolutions — 5-8 ✓ bullets):
   ✓ Full name, age, designation, DIN (if stated)
   ✓ Date of first appointment to board
   ✓ Current tenure in years
   ✓ Qualifications (each qualification as a separate bullet)
   ✓ Professional background / career history (2-3 sentences)
   ✓ Current committee memberships (from board_context)
   ✓ Board attendance: meetings held vs attended vs percentage
   ✓ Family relationships with other board members (if stated)
   ✓ Other listed company directorships count

⑥ REMUNERATION DETAILS (for director/MD/remuneration resolutions):
   State the total remuneration and then bullet each component:
   "The breakup of remuneration for FY [year] is as follows:"
   ✓ Sitting Fees: Rs. X
   ✓ Commission: Rs. Y
   ✓ Perquisites/Retiral benefits: Rs. Z
   ✓ Total: Rs. [Total]
   Then state whether this is in line with company NED policy or not.

⑦ BOARD COMPOSITION ANALYSIS (always — 1-2 paragraphs, not bullets):
   Check from board_context and state findings:
   - Chairman independence status
   - Audit Committee composition — any non-independent member → flag
   - NRC composition — any non-independent/promoter member → flag
   - Any Independent Director with >10 years tenure
   - Any director on >7 listed boards
   Write these as plain analytical sentences (not bullets).

⑧ GOVERNANCE CONCERNS (bold paragraphs — one per concern):
   Each concern MUST:
   - Start with "**We note that..."
   - Name the specific director/person/fact from the text
   - Cite the specific Regulation/Section being violated
   - State the precise governance implication
   - End with what shareholders should ask
   Example: "**We note that [Name], a Non-Executive Non-Independent Director and Promoter,
   is a member of the Audit Committee. Regulation 18(1)(c) of SEBI LODR mandates that the
   Audit Committee shall comprise only of Independent Directors. We recommend shareholders
   raise this concern with the Board.**"

⑨ CLOSING SENTENCE (plain text, not bold — mandatory):
   FOR:    "Given [brief positive reason], we recommend shareholders vote FOR this resolution."
   FOR*:   "We recommend shareholders raise the above concerns and seek clarification from
            the board. However, since [brief reason], we recommend shareholders vote FOR
            this resolution."
   AGAINST:"We recommend shareholders vote AGAINST this resolution."

## BODY LENGTH REQUIREMENT
Your body_paragraphs array MUST contain at minimum:
- Financial statement resolutions: 12-18 items (opening + proposal bullets + auditor
  details + verbatim quote + board analysis + concerns + closing)
- Director appointment resolutions: 14-20 items (opening + director profile bullets +
  remuneration table + board analysis + concerns + closing)
- Remuneration/RPT resolutions: 12-16 items with full detail
- Simple/routine resolutions (cost auditor, dividend): 8-12 items minimum

If you produce fewer than 8 body_paragraphs items, you have not written enough.

Return ONLY this JSON (no markdown fences, no text outside the JSON object):
{{
  "resolution_number":         {res_no},
  "resolution_title":          "<exact title from the notice>",
  "resolution_type":           "<Ordinary|Special>",
  "management_recommendation": "<FOR|AGAINST|ABSTAIN>",
  "ingovern_recommendation":   "<FOR|FOR*|AGAINST>",
  "confidence":                "<High|Medium|Low>",
  "body_paragraphs": [
    "<item 1>",
    "<item 2 — add AS MANY items as needed to meet the length requirement>",
    "..."
  ],
  "governance_concerns": [
    "<Regulation/Section — one-line concern summary>"
  ],
  "closing_recommendation": "We recommend shareholders vote <FOR|FOR*|AGAINST> the resolution on <subject> of {company_name}.",
  "key_facts": {{
    "director_name":     "<from text or empty>",
    "din":               "<from text or empty>",
    "age":               "<from text or empty>",
    "tenure":            "<from text or empty>",
    "qualifications":    "<from text or empty>",
    "auditor":           "<from text or empty>",
    "remuneration":      "<total from text or empty>",
    "shareholding":      "<from text or empty>",
    "related_party":     "<from text or empty>",
    "board_seats":       "<count or empty>",
    "transaction_value": "<from text or empty>"
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
        "model": "anthropic/claude-haiku-4.5",
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens":  8000,
    }

    # Bounded timeout so a hung upstream call can't pin a thread/connection forever
    r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"OpenRouter {r.status_code}: {r.text[:300]}")

    content = (
        r.json()
        .get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    ).strip()

    # Strip accidental markdown fences, in case the model wraps JSON in ```json ... ```
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
    # Raised from 6,000: explanatory statements now flow through in full (see
    # resolution_extractor fix), and routine items with no explanation stay
    # short regardless — this cap only bites on genuinely long special items.
    combined_text = combined_text[:14000] + ("…" if len(combined_text) > 14000 else "")
    safe_res["resolution_text"] = combined_text

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
        result.setdefault("confidence",                "Medium")
        result.setdefault("body_paragraphs",           [])
        result.setdefault("governance_concerns",       [])
        result.setdefault("closing_recommendation",    "")
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
            "confidence":                "Low",
            "body_paragraphs":           [f"AI analysis unavailable: {str(exc)[:200]}"],
            "governance_concerns":       [],
            "closing_recommendation":    f"We recommend shareholders vote {fallback_rec} this resolution.",
            "key_facts":                 {},
            "ai_powered":                False,
            "error":                     str(exc),
        }
