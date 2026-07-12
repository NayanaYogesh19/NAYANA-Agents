"""
content_agent.py — replaces the old rigid presentation_generator_agent.

Produces the dynamic, per-section narrative text (and benchmark/KPI table
data) used to render the final PDF. Unlike the old presentation generator,
this agent:
  - Only ever writes sections the caller actually asks for (dynamic topic
    inclusion/exclusion — a section not requested is never generated).
  - Is explicitly instructed to make every section's reasoning unique to the
    specific company/industry/competitors, never generic boilerplate that
    could be copy-pasted between companies.
  - Never invents numbers: it must reuse the exact manually-entered metrics
    and numbers surfaced by the upstream research/audit agents, and must
    otherwise say "Data not available."
  - Emits parseable JSON, so slide_renderers.py can place each section's text
    (and any table rows) into the fixed-layout PDF template exactly.
"""

from __future__ import annotations

import json
import re

from langchain_core.prompts import ChatPromptTemplate

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
4. Only produce the sections listed in REQUESTED_SECTIONS. Do not add
   sections that were not requested, and do not skip any that were.
5. Output must be valid JSON only — no markdown fences, no commentary before
   or after the JSON object.
</absolute_rules>

<output_schema>
Return a single JSON object with this shape:
{
  "sections": {
    "<section_slug>": "<3-6 sentences of plain-text narrative for that section>",
    ...
  },
  "benchmarks": {
    "seo": {"headers": ["Metric","<Company>","Industry Avg / Competitor"], "rows": [[..],[..]], "takeaways": ["...","..."]},
    "smm": {"headers": [...], "rows": [[...]], "takeaways": [...]},
    "ppc": {"headers": [...], "rows": [[...]], "takeaways": [...]}
  },
  "kpi_targets": {
    "headers": ["Metric","Current State","6-Month Target","Strategic Impact"],
    "rows": [["...","...","...","..."], ...]
  },
  "positioning_line": "<one short tagline for the title slide, specific to this company>"
}

Only include "benchmarks" sub-keys and "kpi_targets" if the corresponding
section slugs (benchmarks_seo / benchmarks_smm / benchmarks_ppc /
kpis_targets) appear in REQUESTED_SECTIONS.
</output_schema>
"""


SECTION_HINTS = {
    "current_state": "Cover: Performance Overview, Technical Gaps, Content Gaps, Visibility Challenges — each grounded in the exact manually-entered metrics given.",
    "visibility_gap": "Cover: Client vs. Industry comparison (using named competitors from research) and Strategic Opportunities.",
    "best_practices": "3-5 bullets, each naming a real competitor and a specific tactic they use, drawn from the research brief.",
    "growth_recommendations": "Cover: Search & Technical Optimization ideas AND Brand Authority & Engagement ideas, each tied to a specific finding above.",
    "summary_next_steps": "Cover: Foundation & Strategy actions AND Growth & Execution actions, phrased as a numbered roadmap.",
    "executive_summary": "Cover: Strengths worth scaling, and Performance Gaps to fix now, plus a one-line strategic imperative.",
    "positioning_audit": "Cover: what this company's brand stands for (grounded in its actual site content) and a market gap analysis naming real competitors and their weaknesses.",
    "performance_marketing": "Cover: channel-by-channel read (Search/Social/etc.) of the manually entered PPC metrics and what the funnel reality looks like for this company.",
    "seo_technical_audit": "Cover: structural/technical gaps implied by the manually entered error/warning/notice counts, specific to this company's site.",
    "smm_audit": "Cover: competitive gap analysis using the manually entered target SMM metrics vs researched competitor social presence.",
    "conversion_funnel": "Cover: a diagnosis of where this company's funnel likely leaks (based on available context) and a fix-oriented set of design principles.",
    "strategic_recommendations": "Cover: a two-phase roadmap (Phase 1 foundation repair, Phase 2 growth/scale) specific to the gaps already identified.",
}


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def run_content_generation(
    *,
    company_name: str,
    industry: str,
    requested_sections: list[str],
    research_brief: str,
    seo_audit_text: str,
    smm_audit_text: str,
    strategy_text: str,
    seo_metrics: dict,
    ppc_metrics: dict,
    smm_metrics: dict,
    competitor_names: str,
) -> dict:
    hints = "\n".join(f"- {slug}: {SECTION_HINTS[slug]}" for slug in requested_sections if slug in SECTION_HINTS)

    user_text = f"""COMPANY: {company_name}
INDUSTRY: {industry}
NAMED_COMPETITORS: {competitor_names}

REQUESTED_SECTIONS (produce exactly these, no more, no less):
{requested_sections}

SECTION GUIDANCE:
{hints}

RESEARCH_BRIEF:
{research_brief}

SEO_AUDIT_FINDINGS:
{seo_audit_text}

SMM_AUDIT_FINDINGS:
{smm_audit_text}

STRATEGY_FINDINGS:
{strategy_text}

MANUALLY_ENTERED_SEO_METRICS: {json.dumps(seo_metrics)}
MANUALLY_ENTERED_PPC_METRICS: {json.dumps(ppc_metrics)}
MANUALLY_ENTERED_SMM_METRICS: {json.dumps(smm_metrics)}

Remember: output valid JSON only, matching the schema exactly, covering only
the REQUESTED_SECTIONS above."""

    llm = get_llm(temperature=0.6)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_MESSAGE),
            ("human", "{input}"),
        ]
    )
    chain = prompt | llm
    result = chain.invoke({"input": user_text})

    try:
        return _extract_json(result.content)
    except (json.JSONDecodeError, AttributeError):
        return {"sections": {}, "benchmarks": {}, "kpi_targets": {}, "positioning_line": industry}
