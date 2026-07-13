"""
content_agent.py — dynamic, per-company narrative content generator.

Produces the text (and benchmark/KPI table data) used to render the final
PDF, matching the reference "Digital Marketing Audit Report" template:

  - Per-category slides (Current Digital State, Visibility Gap) get their
    own independent content for each selected category (SEO/PPC/SMM) — the
    model is asked once per category so content never bleeds between them.
  - Combined slides (Industry Best Practices, Benchmark Analysis, Strategic
    Takeaways, Growth Recommendations, Summary & Next Steps) get ONE set of
    content that adapts to draw from whichever categories were selected.

Absolute rules enforced via prompt:
  - Never invent a number — only reuse manually-entered metrics or numbers
    surfaced by upstream research/audit agents; otherwise "Data not available".
  - Never write generic, interchangeable content — every section must be
    grounded in this specific company/industry/competitors.
  - Never mention investment/pricing/retainer/contract terms.
  - Emits parseable JSON with explicit structured sub-keys (never a single
    blob of prose) so slide_renderers.py can place each bullet directly
    without any text-parsing heuristics.
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_llm

SYSTEM_MESSAGE = """<role>
You are a senior digital marketing strategist writing the narrative content
for a client-facing audit report PDF. You do not control the visual layout —
you only produce the text and table data for a fixed set of report sections
that a rendering engine will place into pre-built slide templates.
</role>

<absolute_rules>
1. NEVER invent a number. Use only numbers given to you in the input
   (manually entered metrics, PageSpeed data, or research findings). If a
   number is not given, write "Data not available" rather than estimating.
2. NEVER write generic, interchangeable content. Every section must read as
   if written specifically for THIS company, in THIS industry, referencing
   THIS company's actual competitors and actual numbers. Two different
   companies' reports must never share similar-sounding sentences.
3. NEVER mention: investment amounts, monthly retainer pricing, contract
   terms, or terms & conditions — these are permanently excluded from every
   report regardless of what is asked.
4. Only produce the sections listed in REQUESTED_SECTIONS, for exactly the
   categories listed in SELECTED_CATEGORIES. Do not add sections/categories
   that were not requested, and do not skip any that were.
5. Output must be valid JSON only — no markdown fences, no commentary before
   or after the JSON object.
6. Every sub-key must be a JSON array of substantive bullet strings — never
   a single wall-of-text string, never omitted (use "Data not available" as
   a bullet only as an absolute last resort). Exact required counts per
   sub-key are given in SECTION GUIDANCE below; follow them precisely.
7. Every bullet MUST follow this exact style, matching the reference report:
   "<Bold Label> [<the actual number/value>]: <1-2 sentence explanation
   citing what this specifically means for this company, in this industry,
   vs its named competitors>." For example:
   "Health Score [63/100]: Current technical health is moderate but lags
   behind industry leaders, limiting ranking potential for high-value
   keywords." The label is a short 2-4 word metric name; the bracketed part
   is the real number/value for THIS company (never a placeholder like
   "XX"); the explanation must be substantive enough to fill the available
   space (aim for 20-35 words per bullet, not a short fragment).
</absolute_rules>

<output_schema>
Return a single JSON object with this shape:

{
  "per_category": {
    "<category>": {
      "current_state": {"performance_overview": [...3 bullets...], "technical_gaps": [...3 bullets...], "content_gaps": [...3 bullets...], "visibility_challenges": [...3 bullets...]},
      "visibility_gap": {"client_vs_industry": [...EXACTLY 5 bullets...], "strategic_opportunities": [...EXACTLY 3 bullets...]}
    },
    ...
  },
  "best_practices": {"<category>": [...EXACTLY 5 bullets...], ...one key per SELECTED_CATEGORIES...},
  "benchmarks": {
    "client_table": {"headers": [...], "rows": [[...]]},
    "industry_table": {"headers": [...], "rows": [[...]]},
    "takeaways": [...]
  },
  "growth_recommendations": {
    "<category>": [{"title": "...", "detail": "...", "benefit": "..."}, ...EXACTLY 4 items...],
    ...one key per SELECTED_CATEGORIES...
  },
  "summary_next_steps": {
    "foundation_strategy": [{"title": "...", "detail": "...", "impact": "..."}, ...EXACTLY 6 items...],
    "growth_execution": [{"title": "...", "detail": "...", "impact": "..."}, ...EXACTLY 6 items...],
    "action_plan": [{"title": "...", "detail": "...", "impact": "..."}, ...EXACTLY 6 items...]
  },
  "positioning_line": "<one short tagline for the title slide, specific to this company>"
}

"per_category" must contain one key per category in SELECTED_CATEGORIES
(exactly "seo", "ppc", and/or "smm"), each with "current_state" and
"visibility_gap" sub-objects using the exact sub-keys shown above — content
for each category must be written independently, in that category's own
terms (SEO = organic/technical, PPC = paid/funnel, SMM = social presence),
never mixing categories together in one category's content.

MANDATORY BULLET COUNTS (never fewer — pad with additional real, specific
findings rather than stopping short; never generic filler just to hit count):
- current_state.performance_overview: exactly 3 bullets
- current_state.technical_gaps: exactly 3 bullets
- current_state.content_gaps: exactly 3 bullets
- current_state.visibility_challenges: exactly 3 bullets
- visibility_gap.client_vs_industry: exactly 5 bullets (this is the largest
  section on its slide — cover follower/traffic/ranking gaps, engagement
  gaps, content-format gaps, posting-cadence gaps, and authority gaps as
  applicable to the category, each with a real number where available)
- visibility_gap.strategic_opportunities: exactly 3 bullets
- best_practices.<each selected category>: exactly 5 bullets

"benchmarks" is produced exactly once, as a SINGLE slide with exactly 2
tables (never a separate table/slide per category). BOTH tables' rows MUST
include metrics for EVERY category in SELECTED_CATEGORIES, and MUST NEVER
include rows for a category that is NOT in SELECTED_CATEGORIES. This is
strict: if SELECTED_CATEGORIES = ["ppc"] only, the tables must contain ONLY
PPC rows (Ad Spend, Impressions, Clicks, CTR, CPC, Conversions, Conversion
Rate, ROAS) — do NOT include any SEO rows (Health Score, Organic Traffic,
Organic Keywords, Errors, Warnings) or SMM rows (LinkedIn/Instagram/
Facebook/YouTube followers) in that case, since no SEO or SMM data exists
for this run and those rows would be meaningless. Concretely:
- If (and only if) "seo" is in SELECTED_CATEGORIES: include SEO rows (Health
  Score, Organic Traffic, Organic Keywords, Errors, Warnings) using the
  EXACT values from MANUALLY_ENTERED_SEO_METRICS given below.
- If (and only if) "ppc" is in SELECTED_CATEGORIES: include PPC rows (Ad
  Spend, Impressions, Clicks, CTR, CPC, Conversions, Conversion Rate, ROAS)
  using the EXACT values from MANUALLY_ENTERED_PPC_METRICS given below.
- If (and only if) "smm" is in SELECTED_CATEGORIES: include SMM rows
  (LinkedIn/Instagram/Facebook/YouTube Followers, Brand Tone) using the
  EXACT values from AUTO_FETCHED_SMM_METRICS given below.
Every metric that has a real value in the corresponding METRICS input below
MUST appear in "client_table" with that exact value — never write "Data not
available" for a metric you were actually given a number for. Only use
"Data not available" for a metric that is genuinely missing/null in the
input, or for a competitor's cell in "industry_table" when research
genuinely found nothing (never for the client's own column).
"client_table" = this company's own current values for all selected
categories' metrics (headers e.g. ["Metric","Current Status","Trend"]).
"industry_table" = the same metrics compared against the REAL named
competitors from NAMED_COMPETITORS (headers = ["Metric", company name,
<first named competitor>] at minimum — add more competitor columns if
multiple were named). Never invent competitor numbers you have no basis
for — use "Data not available" for a competitor's cell only if research
found nothing, but always include the row for the metric itself.

"summary_next_steps" is produced exactly once (this slide is NOT
per-category — it has a fixed 3-section structure regardless of how many
categories are selected), and must draw on and mention ALL of
SELECTED_CATEGORIES together (e.g. if seo+ppc+smm are all selected, each of
its 3 sections should include actions spanning SEO, PPC, and SMM, not just
SEO). It has exactly 3 sections, each with EXACTLY 6 items (never fewer,
never generic filler — each item must be a real, specific action grounded
in this company's actual findings above):
- "foundation_strategy": 6 items — core foundational fixes/strategy shifts
  (e.g. technical remediation, positioning, research-backed groundwork).
- "growth_execution": 6 items — active growth/execution moves (e.g.
  campaign launches, content programs, channel expansion).
- "action_plan": 6 items — concrete near-term next steps with a clear
  sequence (what to do first, second, etc.), each still a
  {"title","detail","impact"} object like the other two sections.
Each item's "impact" field is a short 1-sentence business-impact statement
(this replaces the old "Business Impact:" labeled line — the rendering
engine adds any label formatting itself).

"best_practices" and "growth_recommendations" are BOTH per-category, each
rendering as ONE slide regardless of how many categories are selected, but
with content broken out per category — produce one key per category in
SELECTED_CATEGORIES:

- "best_practices" = {"seo": [...5 bullets...], "ppc": [...5 bullets...],
  "smm": [...5 bullets...]} (only for selected categories) — each bullet
  naming a REAL named competitor and a REAL specific tactic they use for
  that category (SEO = e.g. content/backlink/technical tactics; PPC = e.g.
  targeting/creative/bidding tactics; SMM = e.g. posting cadence/content-
  format/community tactics) — never generic, interchangeable advice, and
  never invented if the research brief doesn't support it (use "Data not
  available via search" as a last resort, never more than once per category).

- "growth_recommendations" = {"seo": [...EXACTLY 4 items...], "ppc":
  [...EXACTLY 4 items...], "smm": [...EXACTLY 4 items...]} (only for
  selected categories) — each item is a {"title","detail","benefit"} object,
  where "seo" recommendations map to a "Search & Technical Optimization"
  block, "ppc" recommendations map to an "Ads Enhancement" block, and "smm"
  recommendations map to a "Brand Authority & Engagement" block (the
  rendering engine handles the block titles — you only provide the 4 items
  per selected category). Each item must be a real, specific, unique
  recommendation grounded in this company's actual findings above — never
  a generic tip that could apply to any company.
</output_schema>
"""

CATEGORY_CONTEXT_HINTS = {
    "seo": "organic search visibility, technical SEO health, and content depth",
    "ppc": "paid search/social advertising performance, funnel conversion, and ad spend efficiency",
    "smm": "social media presence, follower growth, posting cadence, and engagement",
}


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def _as_bullet_list(value) -> list[str]:
    """Coerce a sub-key's value into a clean list[str], never raising."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, dict):
        return [str(v).strip() for v in value.values() if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    lines = [l.strip(" -•\t:") for l in text.splitlines() if l.strip()]
    lines = [l for l in lines if len(l) > 3]
    return lines or [text]


def _as_card_list(value) -> list[dict]:
    """Coerce a growth/summary sub-key's value into a list of
    {"title","detail"/"benefit"/"impact"} dicts, tolerating the model
    returning plain strings instead of structured cards."""
    if not value:
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                out.append({
                    "title": str(item.get("title", "")).strip(),
                    "detail": str(item.get("detail", "")).strip(),
                    "benefit": str(item.get("benefit", item.get("impact", ""))).strip(),
                })
            else:
                out.append({"title": str(item).strip(), "detail": "", "benefit": ""})
        return [c for c in out if c["title"] or c["detail"]]
    return []


def _normalize_current_state(value: dict) -> dict:
    keys = ["performance_overview", "technical_gaps", "content_gaps", "visibility_challenges"]
    value = value if isinstance(value, dict) else {}
    return {k: _as_bullet_list(value.get(k)) for k in keys}


def _normalize_visibility_gap(value: dict) -> dict:
    keys = ["client_vs_industry", "strategic_opportunities"]
    value = value if isinstance(value, dict) else {}
    return {k: _as_bullet_list(value.get(k)) for k in keys}


def _normalize_best_practices(value, categories: list[str]) -> dict[str, list[str]]:
    """best_practices is keyed per category (one 5-bullet list per selected
    category), rendered on a single combined slide. Tolerates the model
    returning the old flat {"bullets": [...]} shape by assigning it to the
    first selected category rather than discarding the content."""
    value = value if isinstance(value, dict) else {}
    if "bullets" in value and not any(cat in value for cat in categories):
        # Old flat shape — keep the content, attribute it to the first category.
        fallback_bullets = _as_bullet_list(value.get("bullets"))
        return {categories[0]: fallback_bullets} if categories else {}
    return {cat: _as_bullet_list(value.get(cat)) for cat in categories}


def _normalize_growth_recommendations(value, categories: list[str]) -> dict[str, list[dict]]:
    """growth_recommendations is keyed per category (one 4-item card list per
    selected category — SEO -> "Search & Technical Optimization", PPC ->
    "Ads Enhancement", SMM -> "Brand Authority & Engagement" — the block
    titles are applied by the renderer). Tolerates the model returning the
    old fixed-key shape ("search_technical_optimization" /
    "brand_authority_engagement") by remapping those onto seo/smm."""
    value = value if isinstance(value, dict) else {}
    legacy_map = {"search_technical_optimization": "seo", "brand_authority_engagement": "smm"}
    if any(k in value for k in legacy_map) and not any(cat in value for cat in categories):
        remapped = {legacy_map[k]: v for k, v in value.items() if k in legacy_map}
        return {cat: _as_card_list(remapped.get(cat)) for cat in categories}
    return {cat: _as_card_list(value.get(cat)) for cat in categories}


def _normalize_content(data: dict, categories: list[str]) -> dict:
    per_category_raw = data.get("per_category") or {}
    per_category: dict[str, dict] = {}
    for cat in categories:
        cat_data = per_category_raw.get(cat) or {}
        per_category[cat] = {
            "current_state": _normalize_current_state(cat_data.get("current_state")),
            "visibility_gap": _normalize_visibility_gap(cat_data.get("visibility_gap")),
        }

    best_practices = _normalize_best_practices(data.get("best_practices"), categories)

    benchmarks_raw = data.get("benchmarks") or {}
    benchmarks = {
        "client_table": benchmarks_raw.get("client_table") or {"headers": [], "rows": []},
        "industry_table": benchmarks_raw.get("industry_table") or {"headers": [], "rows": []},
        "takeaways": _as_bullet_list(benchmarks_raw.get("takeaways")),
    }

    growth_recommendations = _normalize_growth_recommendations(data.get("growth_recommendations"), categories)

    summary_raw = data.get("summary_next_steps") or {}
    summary_next_steps = {
        "foundation_strategy": _as_card_list(summary_raw.get("foundation_strategy")),
        "growth_execution": _as_card_list(summary_raw.get("growth_execution")),
        "action_plan": _as_card_list(summary_raw.get("action_plan")),
    }

    return {
        "per_category": per_category,
        "best_practices": best_practices,
        "benchmarks": benchmarks,
        "growth_recommendations": growth_recommendations,
        "summary_next_steps": summary_next_steps,
        "positioning_line": str(data.get("positioning_line") or "").strip(),
    }


def _empty_content(categories: list[str], positioning_fallback: str) -> dict:
    per_category = {
        cat: {
            "current_state": _normalize_current_state({}),
            "visibility_gap": _normalize_visibility_gap({}),
        }
        for cat in categories
    }
    return {
        "per_category": per_category,
        "best_practices": {cat: [] for cat in categories},
        "benchmarks": {"client_table": {"headers": [], "rows": []}, "industry_table": {"headers": [], "rows": []}, "takeaways": []},
        "growth_recommendations": {cat: [] for cat in categories},
        "summary_next_steps": {"foundation_strategy": [], "growth_execution": [], "action_plan": []},
        "positioning_line": positioning_fallback,
    }


def run_content_generation(
    *,
    company_name: str,
    industry: str,
    categories: list[str],
    research_brief: str,
    seo_audit_text: str,
    smm_audit_text: str,
    strategy_text: str,
    seo_metrics: dict,
    ppc_metrics: dict,
    smm_metrics: dict,
    competitor_names: str,
) -> dict:
    category_hints = "\n".join(
        f'- "{cat}": covers {CATEGORY_CONTEXT_HINTS[cat]}.' for cat in categories
    )

    user_text = f"""COMPANY: {company_name}
INDUSTRY: {industry}
NAMED_COMPETITORS: {competitor_names}
SELECTED_CATEGORIES: {categories}

CATEGORY GUIDANCE:
{category_hints}

RESEARCH_BRIEF:
{research_brief}

SEO_AUDIT_FINDINGS (present only if "seo" is selected):
{seo_audit_text or "Not applicable — SEO not selected."}

SMM_AUDIT_FINDINGS (present only if "smm" is selected):
{smm_audit_text or "Not applicable — SMM not selected."}

STRATEGY_FINDINGS:
{strategy_text}

MANUALLY_ENTERED_SEO_METRICS: {json.dumps(seo_metrics)}
MANUALLY_ENTERED_PPC_METRICS: {json.dumps(ppc_metrics)}
AUTO_FETCHED_SMM_METRICS: {json.dumps(smm_metrics)}

Remember: output valid JSON only, matching the schema exactly. Produce
independent per-category content for current_state/visibility_gap for each
of SELECTED_CATEGORIES, and one combined set of content for best_practices,
benchmarks, growth_recommendations, and summary_next_steps that draws on ALL
of SELECTED_CATEGORIES together."""

    llm = get_llm(temperature=0.6)
    result = llm.invoke([SystemMessage(content=SYSTEM_MESSAGE), HumanMessage(content=user_text)])

    try:
        data = _extract_json(result.content)
        return _normalize_content(data, categories)
    except (json.JSONDecodeError, AttributeError):
        return _empty_content(categories, industry)
