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
that a rendering engine will place into pre-built slide templates. The
renderer is built to gracefully handle variable-length lists: if a section
has 5 real, well-supported points, give 5; if it genuinely only has 2, give
2; if it genuinely has none, return an empty list. It will never look broken
— sparse sections are simply omitted from the layout, never padded.
</role>

<absolute_rules>
1. NEVER invent a number. Use only numbers given to you in the input
   (manually entered metrics, PageSpeed data, ad-library data, or research
   findings).
2. NEVER write "Data not available", "Not addressed", "Not implemented",
   "Not present", "Not utilized", "Not defined", "Not established", or any
   other placeholder/absence phrase ANYWHERE in your output, for ANY reason,
   under ANY circumstance. This is the single most important rule in this
   prompt. If you do not have a real, specific, well-supported point to
   make, DO NOT WRITE A BULLET FOR IT — simply provide fewer bullets in that
   list, or an empty list `[]` if nothing in that sub-section is genuinely
   supported by the input data. A shorter, fully-real section is always
   correct; a placeholder-padded section is always wrong.
3. NEVER write generic, interchangeable content. Every bullet must read as
   if written specifically for THIS company, in THIS industry, referencing
   THIS company's actual competitors and actual numbers/data given to you.
   Two different companies' reports must never share similar-sounding
   sentences. Never write vague statements like "may not be effective" or
   "could improve" with no real basis — every claim must trace to a real
   input fact (a number, a named competitor's known tactic, a specific
   scraped/researched finding).
4. NEVER mention: investment amounts, monthly retainer pricing, contract
   terms, or terms & conditions — these are permanently excluded from every
   report regardless of what is asked.
5. Only produce the sections listed in REQUESTED_SECTIONS, for exactly the
   categories listed in SELECTED_CATEGORIES. Do not add sections/categories
   that were not requested, and do not skip any that were.
6. Output must be valid JSON only — no markdown fences, no commentary before
   or after the JSON object.
7. Every sub-key must be a JSON array. Each element is a genuinely
   real, specific bullet string — never a placeholder, never a wall-of-text
   string. See SECTION GUIDANCE below for the target range per sub-key
   (a ceiling to aim for when real content supports it, never a floor to pad
   to).
8. Every bullet MUST follow this exact style, matching the reference report:
   "<Bold Label> [<the actual number/value>]: <1-2 sentence explanation
   citing what this specifically means for this company, in this industry,
   vs its named competitors>." For example:
   "Health Score [63/100]: Current technical health is moderate but lags
   behind industry leaders, limiting ranking potential for high-value
   keywords." The label is a short 2-4 word metric name; the bracketed part
   is the real number/value for THIS company (never a placeholder like
   "XX", never omitted — if there's truly no number to bracket, the bullet
   likely shouldn't exist at all per rule 2); the explanation must be
   substantive enough to fill the available space (aim for 20-35 words per
   bullet, not a short fragment).
</absolute_rules>

<output_schema>
Return a single JSON object with this shape:

{
  "per_category": {
    "<category>": {
      "current_state": {"performance_overview": [...up to 5 bullets...], "technical_gaps": [...up to 5 bullets...], "content_gaps": [...up to 5 bullets...], "visibility_challenges": [...up to 5 bullets...]},
      "visibility_gap": {"client_vs_industry": [...up to 5 bullets...], "strategic_opportunities": [...up to 5 bullets...]}
    },
    ...
  },
  "best_practices": {"<category>": [...up to 7 bullets...], ...one key per SELECTED_CATEGORIES...},
  "benchmarks": {
    "client_table": {"headers": [...], "rows": [[...]]},
    "industry_table": {"headers": [...], "rows": [[...]]},
    "takeaways": [...up to 6 bullets...]
  },
  "growth_recommendations": {
    "<category>": [{"title": "...", "detail": "...", "benefit": "..."}, ...up to 4 items...],
    ...one key per SELECTED_CATEGORIES...
  },
  "summary_next_steps": {
    "foundation_strategy": [{"title": "...", "detail": "...", "impact": "..."}, ...up to 6 items...],
    "growth_execution": [{"title": "...", "detail": "...", "impact": "..."}, ...up to 6 items...],
    "action_plan": [{"title": "...", "detail": "...", "impact": "..."}, ...up to 6 items...]
  },
  "positioning_line": "<one short tagline for the title slide, specific to this company>"
}

"per_category" must contain one key per category in SELECTED_CATEGORIES
(exactly "seo", "ppc", and/or "smm"), each with "current_state" and
"visibility_gap" sub-objects using the exact sub-keys shown above — content
for each category must be written independently, in that category's own
terms, never mixing categories together in one category's content.

WHAT EACH SUB-SECTION MEANS, PER CATEGORY (use this to decide what's
genuinely real vs. what should be omitted — do not force SEO-shaped content
onto PPC/SMM or vice versa). The JSON sub-keys below are fixed (the
rendering engine always reads "performance_overview", "technical_gaps",
"content_gaps"), but the SLIDE HEADING shown to the reader differs per
category — write content that fits the heading it will actually appear
under:
- SEO: shown under "Performance Overview" / "Technical Gaps" / "Content Gaps".
- PPC: shown under "Ad Presence Overview" / "Ad Format & Platform Gaps" / "Ad Creative Gaps".
- SMM: shown under "Social Presence Overview" / "Platform Coverage Gaps" / "Content & Engagement Gaps".
(All three categories share the 4th quadrant heading "<Category> Challenges".)

Each sub-section below lists MULTIPLE real angles to mine — work through
every angle that applies to THIS company's actual input data and write a
bullet for each one that yields a genuine, specific point (most companies
will support several of these per section, aim to cover most of them
rather than stopping after one or two):

SEO — driven by MANUALLY_ENTERED_SEO_METRICS + SEO_AUDIT_FINDINGS +
RESEARCH_BRIEF:
- performance_overview (heading: "Performance Overview") — real angles to
  cover: Health Score standing, Organic Traffic volume and what it implies
  for this industry, Organic Keywords count and niche coverage, Passed
  Checks as a proportion of total checks, Crawled Pages as a signal of site
  size/depth, any PageSpeed/Core Web Vitals figures in SEO_AUDIT_FINDINGS
  (FCP/LCP/CLS/INP), and how RESEARCH_BRIEF's market-context findings
  relate to this company's actual site content/positioning.
- technical_gaps (heading: "Technical Gaps") — real angles: total Errors
  count and what class of issue that suggests, total Warnings count,
  Notices volume, specific Core Web Vitals figures if present (mobile vs.
  desktop performance gaps), crawl-depth issues implied by Crawled Pages
  vs. Passed Checks ratio, any specific technical findings named in
  SEO_AUDIT_FINDINGS.
- content_gaps (heading: "Content Gaps") — real angles: content depth
  implied by Crawled Pages count, specific content gaps SEO_AUDIT_FINDINGS
  called out (missing blog/resource hub, thin product/service descriptions,
  absence of certain content types), keyword-to-content alignment issues,
  any content-strategy weaknesses RESEARCH_BRIEF surfaced from the actual
  site content it parsed.
- visibility_challenges (heading: "SEO Challenges") — real angles:
  organic-traffic/keyword gap vs. each NAMED_COMPETITOR individually (one
  bullet per competitor if research found real data for them), market-
  demand context from RESEARCH_BRIEF, ranking-difficulty implications from
  the competitive landscape, any specific competitive-positioning findings.

PPC — driven by AUTO_FETCHED_PPC_AD_LIBRARY_DATA (Google/Meta/LinkedIn ad
counts, headlines, platforms, dates, content_type) and
MANUALLY_ENTERED_PPC_METRICS if present. There is USUALLY no spend/CTR/
conversion data — do not write performance_overview bullets pretending
otherwise. Mine the ad-library data thoroughly — it usually supports more
than one or two bullets per section:
- performance_overview (heading: "Ad Presence Overview") — real angles per
  platform that returned data (write one bullet per platform with real ad
  counts, not just one combined bullet): total active ads on Google, total
  on Meta, total on LinkedIn, how many started this month/recently
  (platforms_scraped/*_ads_started_this_month fields) as a recency-of-
  activity signal, whether the advertiser is running ads across multiple
  platforms simultaneously vs. concentrated on one (a real cross-platform
  strategy observation).
- technical_gaps (heading: "Ad Format & Platform Gaps") — real angles: the
  content_type mix actually observed across the real ads (e.g. "all 12
  Google ads are image-only, none are video"), which platforms have ZERO
  ads despite others being active (a real, specific gap), whether ads
  reference distinct landing pages/CTAs found in the scraped data,
  imbalance between platforms (e.g. heavy Google presence but no Meta
  presence at all). Never invent "targeting"/"bidding"/"campaign
  structure" commentary with no evidence.
- content_gaps (heading: "Ad Creative Gaps") — real angles: specific real
  ad headlines/primary_text that lack a clear CTA or benefit statement,
  repeated/near-duplicate copy across multiple real ads found in the data,
  narrow creative variety if content_type shows little format diversity,
  any real ad copy that's generic vs. one that's more specific (contrast
  them if multiple real ads exist).
- visibility_challenges (heading: "Performance Marketing (PPC)
  Challenges"): real competitive framing using NAMED_COMPETITORS and
  whatever the research brief/strategy findings actually established about
  their market position — one bullet per named competitor where research
  found something real, plus a market-saturation/demand observation from
  RESEARCH_BRIEF if available. Not fabricated "competitors spend more"
  claims with no basis.

SMM — driven by AUTO_FETCHED_SMM_METRICS (follower counts, brand tone,
company size/industry from LinkedIn) and SMM_AUDIT_FINDINGS:
- performance_overview (heading: "Social Presence Overview") — real angles:
  one bullet per platform that actually returned a follower/subscriber
  number (Instagram, Facebook, LinkedIn, YouTube each individually, not
  combined into one bullet), platforms_found count as an overall footprint
  signal, brand_tone if present as a qualitative positioning fact,
  linkedin_company_size/linkedin_industry if present as real company-
  profile facts — skip any platform with no data entirely.
- technical_gaps (heading: "Platform Coverage Gaps") — real angles: which
  specific platform(s) genuinely returned no data (a real, useful "no
  measurable presence" fact, one bullet each if multiple), imbalance
  between platforms that DO have data (e.g. strong Instagram but much
  weaker Facebook), any platform-coverage observation SMM_AUDIT_FINDINGS
  made. Never fabricate metrics for an unmeasured platform.
- content_gaps (heading: "Content & Engagement Gaps") — real angles: every
  specific content/posting/engagement observation SMM_AUDIT_FINDINGS's
  narrative actually made (it typically covers multiple distinct
  findings — extract each one as its own bullet rather than summarizing
  them into one), brand_tone alignment with content strategy if relevant.
- visibility_challenges (heading: "Social Media (SMM) Challenges"): real
  competitive comparison — one bullet per NAMED_COMPETITOR where
  SMM_AUDIT_FINDINGS or research found real data about them (follower
  counts, posting cadence, content style), plus any broader competitive
  framing SMM_AUDIT_FINDINGS established. Never invented competitor detail.

TARGET COUNTS — these are the counts you should be ACTIVELY WORKING TOWARD
for a well-populated, professional-looking report, not just permissible
ceilings. Before finalizing a section, check the "real angles" lists above
and make sure you've genuinely used every angle that applies to this
company's actual data — most real companies with real input data (any
manually-entered metrics, any audit findings, any ad-library data, any
follower data, any research brief content) support close to the full
target count. Only fall meaningfully short of the target if the input data
for that specific category is truly minimal (e.g. a category with almost
no real data returned at all). Never pad with placeholder/generic text to
reach the count — reaching it must always be via genuinely distinct, real,
specific points:
- current_state.* sub-keys: target 5 bullets each
- visibility_gap.client_vs_industry: target 5 bullets
- visibility_gap.strategic_opportunities: target 5 bullets — opportunities
  can be forward-looking recommendations (not required to cite a stat),
  but must still be a specific, concrete, non-generic action for THIS
  company.
- best_practices.<each selected category>: target 7 bullets — ONLY include
  a bullet if the research brief/strategy findings genuinely surfaced a
  real, specific tactic for a REAL named competitor. If research found
  nothing usable for a category, return an empty list for that category
  rather than fabricating "Competitor X does Y" with no basis — but first
  make sure you've actually drawn on every named competitor and every
  distinct tactic type (content, technical, paid, social, as applicable)
  before concluding there's nothing more to say.
- benchmarks.takeaways: target 6 bullets — synthesize from whatever real
  data exists across the selected categories (metrics, ad data, follower
  counts, research findings). This section should almost never be empty or
  short, since SOME real comparison is almost always possible from
  NAMED_COMPETITORS + whatever data exists across ALL selected categories
  combined (a takeaway can synthesize across categories, e.g. "while SEO
  traffic lags, the growing PPC ad presence signals budget available to
  redirect toward organic").

UNIQUENESS RULE (applies to every bullet in every section): each bullet must
reference a specific number, a specific named competitor, or a specific
concrete tactic/action — never a sentence that could be copy-pasted into a
different company's report unchanged. If two bullets in the same section
would read almost identically without their bracketed number, rewrite one to
focus on a different angle (e.g. a different metric, competitor, or channel)
rather than repeating the same point twice.

"benchmarks" is produced exactly once, as a SINGLE slide with exactly 2
tables (never a separate table/slide per category). Rows MUST include
metrics ONLY for categories in SELECTED_CATEGORIES — never a row for a
category that is NOT selected. Concretely:
- If (and only if) "seo" is in SELECTED_CATEGORIES: include a row for each
  SEO metric that has a real (non-null) value in MANUALLY_ENTERED_SEO_METRICS.
  Skip any metric that is null/missing — do not include that row at all.
- If (and only if) "ppc" is in SELECTED_CATEGORIES: include a row for each
  PPC metric with a real value in MANUALLY_ENTERED_PPC_METRICS. If that
  dict is empty/all-null but AUTO_FETCHED_PPC_AD_LIBRARY_DATA is present,
  instead include rows for what the ad-library data actually shows (e.g. a
  "Google Ads Running" row with the real ad count, a "Meta Ads Running" row,
  a "LinkedIn Ads Running" row) — real ad-count rows, not fabricated
  spend/CTR numbers. If neither source has anything real, include NO PPC
  rows rather than empty placeholder rows.
- If (and only if) "smm" is in SELECTED_CATEGORIES: include a row for each
  SMM metric with a real (non-null) value in AUTO_FETCHED_SMM_METRICS
  (e.g. Instagram/Facebook/YouTube followers, Brand Tone). Skip any
  platform/field that is null — do not include that row.
"client_table" = this company's own current values (headers e.g.
["Metric","Current Status","Trend"]) — every row's value must be a real
number/fact you were given; never include a row just to show it's missing.
"industry_table" = the same metrics compared against the REAL named
competitors from NAMED_COMPETITORS (headers = ["Metric", company name,
<first named competitor>] at minimum — add more competitor columns if
multiple were named) — only include a competitor's cell if research
genuinely found that specific number for them; if research found nothing
for EVERY competitor on a given metric row, omit that row from both tables
rather than showing an all-blank row.

"summary_next_steps" is produced exactly once (this slide is NOT
per-category — it has a fixed 3-section structure regardless of how many
categories are selected), and must draw on and mention ALL of
SELECTED_CATEGORIES together (e.g. if seo+ppc+smm are all selected, each of
its 3 sections should include actions spanning SEO, PPC, and SMM, not just
SEO). It has up to 3 sections, each with up to 6 items — every item must be
a real, specific, actionable recommendation grounded in this company's
actual findings above, never generic filler used only to hit a count:
- "foundation_strategy": core foundational fixes/strategy shifts (e.g.
  technical remediation, positioning, research-backed groundwork).
- "growth_execution": active growth/execution moves (e.g. campaign
  launches, content programs, channel expansion).
- "action_plan": concrete near-term next steps with a clear sequence (what
  to do first, second, etc.), each still a {"title","detail","impact"}
  object like the other two sections.
Each item's "impact" field is a short 1-sentence business-impact statement
(this replaces the old "Business Impact:" labeled line — the rendering
engine adds any label formatting itself).

"best_practices" and "growth_recommendations" are BOTH per-category, each
rendering as ONE slide regardless of how many categories are selected, but
with content broken out per category — produce one key per category in
SELECTED_CATEGORIES:

- "best_practices" = {"seo": [...up to 5 bullets...], "ppc": [...up to 5
  bullets...], "smm": [...up to 5 bullets...]} (only for selected
  categories) — each bullet naming a REAL named competitor and a REAL
  specific tactic they use for that category (SEO = e.g. content/backlink/
  technical tactics; PPC = e.g. targeting/creative/bidding tactics; SMM =
  e.g. posting cadence/content-format/community tactics) — never generic,
  interchangeable advice, and never invented if the research brief doesn't
  support it — return fewer bullets (or an empty list) rather than inventing.

- "growth_recommendations" = {"seo": [...up to 4 items...], "ppc": [...up
  to 4 items...], "smm": [...up to 4 items...]} (only for selected
  categories) — each item is a {"title","detail","benefit"} object, where
  "seo" recommendations map to a "Search & Technical Optimization" block,
  "ppc" recommendations map to an "Ads Enhancement" block, and "smm"
  recommendations map to a "Brand Authority & Engagement" block (the
  rendering engine handles the block titles — you only provide the items
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
    ppc_ad_data: dict | str | None = None,
) -> dict:
    category_hints = "\n".join(
        f'- "{cat}": covers {CATEGORY_CONTEXT_HINTS[cat]}.' for cat in categories
    )
    # ppc_ad_data is normally the structured scrape summary (dict), but if the
    # user edited the PPC review screen's text, it arrives as a plain string
    # override instead — render it directly rather than JSON-encoding it.
    ppc_ad_data_text = ppc_ad_data if isinstance(ppc_ad_data, str) else json.dumps(ppc_ad_data)

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
{f"AUTO_FETCHED_PPC_AD_LIBRARY_DATA (real ads found via Google/Meta/LinkedIn ad transparency libraries — use these for concrete, real examples of this company's actual running ads/creatives where relevant, e.g. in best_practices or current_state): {ppc_ad_data_text}" if ppc_ad_data else ""}

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
