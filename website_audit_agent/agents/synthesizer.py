"""
synthesizer.py — Calls OpenRouter (Claude) to generate AI-powered insights.

All synthesis output is dynamically generated per audit run.
Zero hardcoded content — every field comes from Claude's analysis of
the actual crawl data passed in the prompt.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List
from openai import OpenAI

from config import Config

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class QuickWin:
    action: str
    expected_impact: str
    effort: str    # Low | Med | High


@dataclass
class StrategicRecommendation:
    recommendation: str
    rationale: str
    priority: str   # P1 | P2 | P3
    timeline: str   # "30 days" | "60 days" | "90 days"


@dataclass
class SynthesisResult:
    executive_summary: str = ""
    target_strengths: List[str] = field(default_factory=list)
    target_weaknesses: List[str] = field(default_factory=list)
    competitor_advantages: List[str] = field(default_factory=list)
    quick_wins: List[QuickWin] = field(default_factory=list)
    strategic_recommendations: List[StrategicRecommendation] = field(default_factory=list)
    content_gaps: List[str] = field(default_factory=list)
    ux_comparison_verdict: str = ""
    overall_verdict: str = ""
    # Roadmap broken out explicitly so pdf_generator never needs fallbacks
    roadmap_30_days: List[str] = field(default_factory=list)
    roadmap_60_days: List[str] = field(default_factory=list)
    roadmap_90_days: List[str] = field(default_factory=list)
    raw_response: str = ""
    error: str = ""


# ── Audit summary builder ─────────────────────────────────────────────────────

def _build_audit_summary(bundle: Dict[str, Any]) -> Dict[str, Any]:
    crawl   = bundle["crawl"]
    tech    = bundle["tech"]
    onpage  = bundle["onpage"]
    content = bundle["content"]
    ux      = bundle["ux"]
    perf    = bundle["perf"]
    scores  = bundle["scores"]

    tech_checks = [
        {"name": c.name, "status": c.status, "detail": c.detail}
        for c in tech.checks
    ]

    onpage_summary = {
        "title_coverage_pct":    onpage.title_coverage_pct,
        "meta_desc_coverage_pct":onpage.meta_desc_coverage_pct,
        "h1_health_pct":         onpage.h1_health_pct,
        "alt_text_coverage_pct": onpage.alt_text_coverage_pct,
        "orphan_pages_count":    len(onpage.orphan_pages),
        "top_issue_pages":       onpage.top_issues_pages[:5],
    }

    pages = content.pages
    avg_wc = sum(p.word_count for p in pages) // max(len(pages), 1) if pages else 0

    content_summary = {
        "total_pages_crawled":    len(pages),
        "thin_content_count":     len(content.thin_content_urls),
        "thin_content_urls":      content.thin_content_urls[:5],
        "duplicate_groups_count": len(content.duplicate_groups),
        "action_counts":          content.action_counts,
        "avg_word_count":         avg_wc,
    }

    ux_summary = {
        "checks": [
            {"name": c.name, "status": c.status, "detail": c.detail}
            for c in ux.checks
        ],
        "trust_signals_present": ux.trust_signals_present,
        "trust_signals_missing": ux.trust_signals_missing,
        "cta_count":             ux.cta_count,
        "cta_above_fold":        ux.cta_above_fold,
    }

    perf_summary: Dict[str, Any] = {}
    if perf.mobile:
        m = perf.mobile
        perf_summary["mobile"] = {
            "performance_score":   m.performance_score,
            "accessibility_score": m.accessibility_score,
            "best_practices_score":m.best_practices_score,
            "seo_score":           m.seo_score,
            "lcp_ms":              round(m.lcp_ms),
            "fcp_ms":              round(m.fcp_ms),
            "ttfb_ms":             round(m.ttfb_ms),
            "cls":                 m.cls,
            "speed_index":         round(m.speed_index),
            "total_blocking_time_ms": round(m.total_blocking_time_ms),
            "top_opportunities": [
                {"title": o.get("title","") if isinstance(o,dict) else str(o),
                 "savings_ms": o.get("savings_ms",0) if isinstance(o,dict) else 0}
                for o in m.opportunities[:5]
            ],
        }
    if perf.desktop:
        d = perf.desktop
        perf_summary["desktop"] = {
            "performance_score": d.performance_score,
            "seo_score":         d.seo_score,
        }

    return {
        "domain":        crawl.domain,
        "pages_crawled": len(crawl.pages),
        "scores": {
            "overall":      scores.overall,
            "performance":  scores.performance,
            "technical_seo":scores.technical_seo,
            "onpage_seo":   scores.onpage_seo,
            "content":      scores.content,
            "ux":           scores.ux,
            "grade":        scores.grade,
        },
        "performance":   perf_summary,
        "technical_seo": tech_checks,
        "onpage_seo":    onpage_summary,
        "content":       content_summary,
        "ux":            ux_summary,
    }


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_prompt(
    target_json: str,
    competitor_json: str,
    target_domain: str,
    competitor_domain: str,
) -> str:
    return f"""You are a senior digital strategy consultant analysing two websites.

Target domain:     {target_domain}
Competitor domain: {competitor_domain}

TARGET AUDIT DATA:
{target_json}

COMPETITOR AUDIT DATA:
{competitor_json}

IMPORTANT RULES:
- Base ALL analysis on the actual data above — do not invent or assume anything.
- Every strength, weakness, recommendation, and roadmap item must reference
  specific numbers, URLs, or findings from the data.
- If the competitor has 0 crawled pages, acknowledge this limitation explicitly
  in the relevant fields — do not pretend to have competitor data you do not have.
- roadmap_30_days must map to the most urgent P1 issues found in the data.
- roadmap_60_days must map to P2 issues.
- roadmap_90_days must map to P3 strategic items.
- All roadmap items must be specific to these two domains — never generic.

Return ONLY a valid JSON object. No markdown fences. No extra text before or after.

Exact JSON schema (fill every field based on the audit data above):

{{
  "executive_summary": "3 sentences comparing {target_domain} vs {competitor_domain} using specific scores and findings from the data",

  "target_strengths": [
    "Strength 1 with specific metric or finding as evidence",
    "Strength 2 with specific metric or finding as evidence",
    "Strength 3 with specific metric or finding as evidence",
    "Strength 4 with specific metric or finding as evidence",
    "Strength 5 with specific metric or finding as evidence"
  ],

  "target_weaknesses": [
    "Weakness 1 with specific metric or URL as evidence",
    "Weakness 2 with specific metric or URL as evidence",
    "Weakness 3 with specific metric or URL as evidence",
    "Weakness 4 with specific metric or URL as evidence",
    "Weakness 5 with specific metric or URL as evidence"
  ],

  "competitor_advantages": [
    "Advantage 1 competitor has over target with specific evidence",
    "Advantage 2 competitor has over target with specific evidence",
    "Advantage 3 competitor has over target with specific evidence"
  ],

  "quick_wins": [
    {{"action": "Specific action for {target_domain} based on the data", "expected_impact": "Measurable impact", "effort": "Low"}},
    {{"action": "Specific action for {target_domain} based on the data", "expected_impact": "Measurable impact", "effort": "Low"}},
    {{"action": "Specific action for {target_domain} based on the data", "expected_impact": "Measurable impact", "effort": "Med"}},
    {{"action": "Specific action for {target_domain} based on the data", "expected_impact": "Measurable impact", "effort": "Med"}},
    {{"action": "Specific action for {target_domain} based on the data", "expected_impact": "Measurable impact", "effort": "High"}}
  ],

  "strategic_recommendations": [
    {{"recommendation": "Specific recommendation for {target_domain}", "rationale": "Why based on data", "priority": "P1", "timeline": "30 days"}},
    {{"recommendation": "Specific recommendation for {target_domain}", "rationale": "Why based on data", "priority": "P1", "timeline": "30 days"}},
    {{"recommendation": "Specific recommendation for {target_domain}", "rationale": "Why based on data", "priority": "P2", "timeline": "60 days"}},
    {{"recommendation": "Specific recommendation for {target_domain}", "rationale": "Why based on data", "priority": "P2", "timeline": "60 days"}},
    {{"recommendation": "Specific recommendation for {target_domain}", "rationale": "Why based on data", "priority": "P3", "timeline": "90 days"}}
  ],

  "content_gaps": [
    "Specific content topic or type {target_domain} is missing based on analysis",
    "Specific content topic or type {target_domain} is missing based on analysis",
    "Specific content topic or type {target_domain} is missing based on analysis",
    "Specific content topic or type {target_domain} is missing based on analysis",
    "Specific content topic or type {target_domain} is missing based on analysis"
  ],

  "ux_comparison_verdict": "2 sentences comparing UX of both sites using specific findings from checks data",

  "overall_verdict": "2 sentences stating which domain is stronger and why, using specific scores and findings",

  "roadmap_30_days": [
    "Specific P1 action item for {target_domain} derived from the most critical findings in the data",
    "Specific P1 action item for {target_domain} derived from the most critical findings in the data",
    "Specific P1 action item for {target_domain} derived from the most critical findings in the data",
    "Specific P1 action item for {target_domain} derived from the most critical findings in the data",
    "Specific P1 action item for {target_domain} derived from the most critical findings in the data"
  ],

  "roadmap_60_days": [
    "Specific P2 growth action for {target_domain} based on medium-priority findings",
    "Specific P2 growth action for {target_domain} based on medium-priority findings",
    "Specific P2 growth action for {target_domain} based on medium-priority findings",
    "Specific P2 growth action for {target_domain} based on medium-priority findings",
    "Specific P2 growth action for {target_domain} based on medium-priority findings"
  ],

  "roadmap_90_days": [
    "Specific P3 authority-building action for {target_domain} based on strategic gaps",
    "Specific P3 authority-building action for {target_domain} based on strategic gaps",
    "Specific P3 authority-building action for {target_domain} based on strategic gaps",
    "Specific P3 authority-building action for {target_domain} based on strategic gaps",
    "Specific P3 authority-building action for {target_domain} based on strategic gaps"
  ]
}}"""


# ── Response parser ───────────────────────────────────────────────────────────

def _safe_str_list(data: dict, key: str) -> List[str]:
    """Extract a list of strings from parsed JSON, handling dicts defensively."""
    items = data.get(key, [])
    result = []
    for item in items:
        if isinstance(item, str):
            result.append(item.strip())
        elif isinstance(item, dict):
            # Flatten dict values to string
            for k in ("action","recommendation","title","description","text"):
                if k in item and item[k]:
                    result.append(str(item[k]).strip())
                    break
            else:
                result.append("; ".join(str(v) for v in item.values() if v))
        else:
            result.append(str(item).strip())
    return [r for r in result if r]


def _parse_synthesis(raw: str) -> SynthesisResult:
    result = SynthesisResult(raw_response=raw)

    clean = raw.strip()

    # Strip markdown fences if present
    if "```" in clean:
        lines = clean.splitlines()
        inside = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if in_block or not any(l.strip().startswith("```") for l in lines):
                inside.append(line)
        clean = "\n".join(inside).strip()

    # Extract JSON object even if there's surrounding text
    first = clean.find("{")
    last  = clean.rfind("}")
    if first != -1 and last != -1 and last > first:
        clean = clean[first:last+1]

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as exc:
        result.error = f"JSON parse error: {exc}"
        logger.error("Parse failed: %s\nFirst 500 chars: %s", exc, raw[:500])
        return result

    result.executive_summary      = data.get("executive_summary", "")
    result.ux_comparison_verdict  = data.get("ux_comparison_verdict", "")
    result.overall_verdict        = data.get("overall_verdict", "")

    result.target_strengths       = _safe_str_list(data, "target_strengths")
    result.target_weaknesses      = _safe_str_list(data, "target_weaknesses")
    result.competitor_advantages  = _safe_str_list(data, "competitor_advantages")
    result.content_gaps           = _safe_str_list(data, "content_gaps")

    # Roadmap — explicitly parsed into their own fields
    result.roadmap_30_days        = _safe_str_list(data, "roadmap_30_days")
    result.roadmap_60_days        = _safe_str_list(data, "roadmap_60_days")
    result.roadmap_90_days        = _safe_str_list(data, "roadmap_90_days")

    # Quick wins
    for qw in data.get("quick_wins", []):
        if isinstance(qw, dict):
            result.quick_wins.append(QuickWin(
                action=qw.get("action", ""),
                expected_impact=qw.get("expected_impact", ""),
                effort=qw.get("effort", "Med"),
            ))
        else:
            result.quick_wins.append(QuickWin(action=str(qw), expected_impact="", effort="Med"))

    # Strategic recommendations
    for sr in data.get("strategic_recommendations", []):
        if isinstance(sr, dict):
            result.strategic_recommendations.append(StrategicRecommendation(
                recommendation=sr.get("recommendation", ""),
                rationale=sr.get("rationale", ""),
                priority=sr.get("priority", "P2"),
                timeline=sr.get("timeline", "60 days"),
            ))
        else:
            result.strategic_recommendations.append(StrategicRecommendation(
                recommendation=str(sr), rationale="", priority="P2", timeline="60 days"
            ))

    # If roadmap fields are missing but strategic_recommendations exist,
    # derive roadmap from them (never use hardcoded strings)
    if not result.roadmap_30_days:
        result.roadmap_30_days = [
            r.recommendation for r in result.strategic_recommendations
            if r.priority == "P1"
        ]
    if not result.roadmap_60_days:
        result.roadmap_60_days = [
            r.recommendation for r in result.strategic_recommendations
            if r.priority == "P2"
        ]
    if not result.roadmap_90_days:
        result.roadmap_90_days = [
            r.recommendation for r in result.strategic_recommendations
            if r.priority == "P3"
        ]

    logger.info(
        "Synthesis OK — %d strengths, %d weaknesses, %d QW, %d recs, "
        "roadmap: %d/%d/%d items",
        len(result.target_strengths), len(result.target_weaknesses),
        len(result.quick_wins), len(result.strategic_recommendations),
        len(result.roadmap_30_days), len(result.roadmap_60_days), len(result.roadmap_90_days),
    )
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def run_synthesis(target_bundle: Dict, competitor_bundle: Dict) -> SynthesisResult:
    """
    Call Claude via OpenRouter with both domains' real audit data.
    Returns fully dynamic SynthesisResult — nothing hardcoded.
    """
    t_domain = target_bundle["crawl"].domain
    c_domain = competitor_bundle["crawl"].domain
    logger.info("Running synthesis for %s vs %s", t_domain, c_domain)

    if not Config.OPENROUTER_API_KEY:
        result = SynthesisResult()
        result.error = "OPENROUTER_API_KEY not set — skipping AI synthesis"
        result.executive_summary = "AI synthesis skipped: OPENROUTER_API_KEY not configured."
        logger.warning(result.error)
        return result

    target_summary    = _build_audit_summary(target_bundle)
    competitor_summary = _build_audit_summary(competitor_bundle)

    target_json    = json.dumps(target_summary,    indent=2, default=str)
    competitor_json = json.dumps(competitor_summary, indent=2, default=str)

    prompt = _build_prompt(
        target_json=target_json,
        competitor_json=competitor_json,
        target_domain=t_domain,
        competitor_domain=c_domain,
    )

    logger.info("Prompt length: %d chars", len(prompt))

    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=Config.OPENROUTER_API_KEY,
        )

        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4096,
    )

        raw_text = response.choices[0].message.content
        logger.info("OpenRouter response: %d chars", len(raw_text))

        # Debug print (safe to remove once confirmed working)
        print("\n===== SYNTHESIS RESPONSE (first 800 chars) =====")
        print(raw_text[:800])
        print("================================================\n")

        return _parse_synthesis(raw_text)

    except Exception as exc:
        logger.error("OpenRouter call failed: %s", exc)
        result = SynthesisResult()
        result.error = str(exc)
        result.executive_summary = f"AI synthesis failed: {exc}"
        return result