"""
InGovern-style governance commentary generator.

The AI derives its OWN InGovern recommendation (FOR / FOR* / AGAINST) by
analysing the resolution text, governance factors, and policy framework.

The cover-page pre-printed recommendation (if present) is shown as a hint/
reference but the AI must independently validate or override it with reasoning.

Uses OpenRouter (no OpenAI SDK). Falls back gracefully.
"""

import json
import requests

from config.config import OPENROUTER_API_KEY, OPENROUTER_MODEL

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = """You are a senior proxy advisory analyst at InGovern Research Services,
a leading Indian corporate governance advisory firm.

You write professional, objective, institutional-quality governance commentary for
AGM, EGM, and Postal Ballot resolutions of Indian listed companies.

Your writing style:
- Formal, factual, precise — no marketing language
- Cite SEBI LODR, Companies Act 2013, Secretarial Standards where relevant
- Numbered governance concerns / observations (1, 2, 3...)
- Always end with a clear closing recommendation sentence
- FOR  = recommend shareholders vote FOR this resolution
- FOR* = vote FOR but raise the listed concerns at the meeting
- AGAINST = recommend shareholders vote AGAINST for the stated governance reasons

Your InGovern recommendation MUST be derived from your analysis of:
1. The resolution text and what the company is actually seeking
2. Governance norms under SEBI LODR / Companies Act 2013
3. The director's/auditor's independence, tenure, qualifications
4. Any red flags: excessive remuneration, dilution, RPT without proper disclosure, etc.
5. Management recommendation (FOR/AGAINST from the notice)

Do NOT simply copy the management recommendation. Do NOT default to FOR for everything.
Use AGAINST when: related party transactions lack proper disclosure, auditor tenure is
excessive, remuneration is disproportionate, or independence is compromised.
Use FOR* when: the resolution is acceptable but has specific concerns worth flagging.

You always return a valid JSON object only — no markdown fences, no extra prose."""

_USER_TEMPLATE = """Analyse the following governance resolution and write an InGovern-style commentary.

=== RESOLUTION DATA ===
{resolution_json}

=== MANAGEMENT RECOMMENDATION (from notice) ===
{mgmt_rec}

=== HISTORICAL PRECEDENTS (may be empty) ===
{precedents_json}

=== POLICY FRAMEWORK ===
{policy_json}

=== BOARD OF DIRECTORS CONTEXT ===
{board_json}

=== PRE-PRINTED INGOVERN RECOMMENDATION (reference only — you may agree or override) ===
{cover_rec_hint}

---
INSTRUCTIONS:
1. Read the resolution_text carefully. Extract all key facts (director name, DIN, tenure,
   auditor name, remuneration amount, shareholding %, related party details, etc.)
2. Assess governance quality against SEBI LODR / Companies Act 2013 standards.
3. Derive your OWN InGovern recommendation (FOR / FOR* / AGAINST) based on the analysis.
   - If the pre-printed hint says AGAINST or FOR*, you must explain why you agree or disagree.
   - Never default to FOR without analysis.
4. Write 2-4 factual summary paragraphs describing what the company is seeking.
5. List numbered governance concerns (1, 2, 3...) — only real concerns from the text.
6. Write a closing recommendation sentence.

Return a JSON object with EXACTLY these keys (no markdown, no extra text):
{{
  "resolution_number":           {res_no},
  "resolution_title":            "<exact title from resolution>",
  "resolution_type":             "<Ordinary|Special>",
  "management_recommendation":   "<FOR|AGAINST|ABSTAIN — from the notice>",
  "ingovern_recommendation":     "<FOR|FOR*|AGAINST — your derived recommendation>",
  "ingovern_rationale":          "<1-2 sentences explaining WHY you chose this recommendation>",
  "confidence":                  "<High|Medium|Low>",
  "summary_paragraphs":          ["<para1>", "<para2>", ...],
  "governance_concerns":         ["1. <specific concern>", "2. <specific concern>", ...],
  "closing_recommendation":      "<full closing sentence>",
  "risk_flags":                  ["<risk1>", "<risk2>"],
  "key_facts":                   {{
    "director_name": "", "din": "", "tenure": "", "auditor": "",
    "remuneration": "", "shareholding": "", "related_party": ""
  }},
  "ai_powered": true
}}"""


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
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens":  2500,
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

    # Strip markdown fences if present
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()

    return json.loads(content)


def generate_ingovern_commentary(
    resolution: dict,
    board_directors: list = None,
) -> dict:
    """
    Generate InGovern-style commentary for a single resolution.
    The AI independently derives its InGovern recommendation from the resolution text.
    """
    import re

    res_no   = resolution.get("resolution_number", 1)
    title    = resolution.get("title", resolution.get("resolution_type", ""))
    res_type = "Special" if resolution.get("special_resolution") else "Ordinary"
    mgmt_rec = resolution.get("management_recommendation", "FOR")
    cover_rec = resolution.get("cover_ingovern_rec", "")

    # Build a clean version of the resolution (truncate resolution_text to save tokens)
    safe_res = {k: v for k, v in resolution.items()
                if k not in ("policy", "precedents", "recommendation",
                             "governance_factors", "governance_evaluation")}
    if "resolution_text" in safe_res:
        t = safe_res["resolution_text"]
        safe_res["resolution_text"] = t[:5000] + ("…" if len(t) > 5000 else "")

    cover_hint = (
        f"Pre-printed recommendation: {cover_rec}" if cover_rec
        else "No pre-printed recommendation available — derive from analysis."
    )

    prompt = _USER_TEMPLATE.format(
        resolution_json = json.dumps(safe_res, indent=2, ensure_ascii=False),
        mgmt_rec        = mgmt_rec,
        precedents_json = json.dumps(resolution.get("precedents", [])[:3], indent=2, ensure_ascii=False),
        policy_json     = json.dumps(resolution.get("policy", {}), indent=2, ensure_ascii=False),
        board_json      = json.dumps((board_directors or [])[:5], indent=2, ensure_ascii=False),
        cover_rec_hint  = cover_hint,
        res_no          = res_no,
    )

    try:
        result = _call_openrouter(prompt)

        # Ensure all required keys exist
        result.setdefault("resolution_number",         res_no)
        result.setdefault("resolution_title",          title)
        result.setdefault("resolution_type",           res_type)
        result.setdefault("management_recommendation", mgmt_rec)
        result.setdefault("ingovern_recommendation",   "FOR")
        result.setdefault("ingovern_rationale",        "")
        result.setdefault("confidence",                "Medium")
        result.setdefault("summary_paragraphs",        [])
        result.setdefault("governance_concerns",       [])
        result.setdefault("closing_recommendation",    "")
        result.setdefault("risk_flags",                [])
        result.setdefault("key_facts",                 {})
        result["ai_powered"] = True
        result["error"]      = None

        # Normalise the recommendation value
        rec = str(result.get("ingovern_recommendation", "FOR")).strip().upper()
        if "AGAINST" in rec:
            result["ingovern_recommendation"] = "AGAINST"
        elif "*" in rec or "FOR*" in rec:
            result["ingovern_recommendation"] = "FOR*"
        else:
            result["ingovern_recommendation"] = "FOR"

        return result

    except Exception as exc:
        # Fallback: use cover rec if available, else FOR
        fallback_rec = cover_rec if cover_rec in ("FOR", "FOR*", "AGAINST") else "FOR"
        return {
            "resolution_number":         res_no,
            "resolution_title":          title,
            "resolution_type":           res_type,
            "management_recommendation": mgmt_rec,
            "ingovern_recommendation":   fallback_rec,
            "ingovern_rationale":        f"AI unavailable: {str(exc)[:100]}",
            "confidence":                "Low",
            "summary_paragraphs":        [],
            "governance_concerns":       [],
            "closing_recommendation":    f"We recommend shareholders vote {fallback_rec} this resolution.",
            "risk_flags":                [],
            "key_facts":                 {},
            "ai_powered":                False,
            "error":                     str(exc),
        }
