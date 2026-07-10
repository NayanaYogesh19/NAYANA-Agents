"""
OpenRouter Governance Analyzer
-------------------------------
Sends a structured resolution object to an LLM via OpenRouter and returns
a rich governance analysis object.

No OpenAI SDK is used — calls are made with the standard `requests` library
against the OpenRouter chat-completions endpoint.
"""

import json
import re
import requests

from config.config import OPENROUTER_API_KEY, OPENROUTER_MODEL

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM_PROMPT = """You are a senior institutional governance analyst specializing in
Indian listed companies (SEBI, Companies Act 2013, LODR). You analyze AGM, EGM, and
Postal Ballot resolutions for proxy advisory firms.

You always return your analysis as a valid JSON object. Never include markdown fences or
extra prose — only raw JSON."""

_USER_TEMPLATE = """Analyze the following governance resolution and return a JSON object
with EXACTLY these keys:

{{
  "governance_analysis":    "<2-3 sentence analysis of the governance quality>",
  "policy_analysis":        "<which policies / SEBI regulations apply and whether they are satisfied>",
  "historical_comparison":  "<comparison with similar historical cases if any, else state 'No comparable cases'>",
  "risk_assessment":        "<identified risks: related-party, dilution, conflict-of-interest, etc.>",
  "governance_concerns":    ["<concern 1>", "<concern 2>"],
  "recommendation":         "FOR" | "FOR*" | "AGAINST",
  "confidence":             "High" | "Medium" | "Low",
  "reasoning":              ["<point 1>", "<point 2>", "<point 3>"]
}}

Resolution details:
{resolution_json}

Historical precedents:
{precedents_json}

Policy in effect:
{policy_json}
"""


def _build_prompt(resolution: dict) -> str:
    safe = {
        k: v for k, v in resolution.items()
        if k != "resolution_text" or len(str(v)) <= 3000
    }

    # Truncate resolution_text if very long
    if "resolution_text" in resolution:
        text = resolution["resolution_text"]
        safe["resolution_text"] = text[:3000] + ("..." if len(text) > 3000 else "")

    precedents = resolution.get("precedents", [])
    policy     = resolution.get("policy", {})

    return _USER_TEMPLATE.format(
        resolution_json = json.dumps(safe, indent=2, ensure_ascii=False),
        precedents_json = json.dumps(precedents, indent=2, ensure_ascii=False),
        policy_json     = json.dumps(policy, indent=2, ensure_ascii=False),
    )


def _call_openrouter(prompt: str) -> dict:
    """
    POST to OpenRouter chat completions and return parsed JSON.
    Raises RuntimeError on any failure.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set in .env")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://ingovern.ai",
        "X-Title":       "InGovern Governance Agent",
    }

    payload = {
        "model": "google/gemini-2.5-flash-lite",
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens":  1200,
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=90,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"OpenRouter error {response.status_code}: {response.text[:400]}"
        )

    content = (
        response.json()
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


def analyze_resolution(resolution: dict) -> dict:
    """
    Main entry point.

    Accepts a structured resolution object (as produced by the pipeline) and
    returns an AI governance analysis dict.  On any failure, returns a minimal
    error dict so the pipeline never crashes.

    Return shape:
    {
        governance_analysis   : str,
        policy_analysis       : str,
        historical_comparison : str,
        risk_assessment       : str,
        governance_concerns   : [str, ...],
        recommendation        : "FOR" | "FOR*" | "AGAINST",
        confidence            : "High" | "Medium" | "Low",
        reasoning             : [str, ...],
        ai_powered            : True,
        error                 : str | None,
    }
    """
    try:
        prompt = _build_prompt(resolution)
        result = _call_openrouter(prompt)

        # Enforce expected keys exist
        result.setdefault("governance_analysis",    "")
        result.setdefault("policy_analysis",        "")
        result.setdefault("historical_comparison",  "")
        result.setdefault("risk_assessment",        "")
        result.setdefault("governance_concerns",    [])
        result.setdefault("recommendation",         "FOR")
        result.setdefault("confidence",             "Medium")
        result.setdefault("reasoning",              [])

        result["ai_powered"] = True
        result["error"]      = None
        return result

    except Exception as exc:
        return {
            "governance_analysis":    "",
            "policy_analysis":        "",
            "historical_comparison":  "",
            "risk_assessment":        "",
            "governance_concerns":    [],
            "recommendation":         "FOR",
            "confidence":             "Low",
            "reasoning":              ["AI analysis unavailable."],
            "ai_powered":             False,
            "error":                  str(exc),
        }
