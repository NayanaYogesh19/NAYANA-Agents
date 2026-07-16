"""
tavily_tool.py — Tavily web search tool.

Mirrors the "Tavily3" / "Search in Tavily" nodes used across the Keyword
Research, SEO Audit, SMM Gap Analysis and Strategy agents in the n8n workflow.
"""

from __future__ import annotations

import logging

import requests
from langchain.tools import tool

from config import Config

logger = logging.getLogger("dm_audit_agent")


@tool("tavily_search", return_direct=False)
def tavily_search(query: str) -> str:
    """Search the web using Tavily. Use this to research competitors, industry
    context, social media presence, or any information not available from the
    other tools."""
    if not Config.TAVILY_API_KEY:
        return "Tool Unavailable — Tavily API key not configured."

    url = "https://api.tavily.com/search"
    headers = {
        "Authorization": f"Bearer {Config.TAVILY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"query": query}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        return f"Tavily search failed: {exc}"


def tavily_search_raw(query: str, max_results: int = 5) -> list[dict]:
    """Plain (non-agent-tool) Tavily search, used for direct programmatic
    lookups such as discovering a company's social profile URLs. Returns the
    list of result dicts (each with at least "url" and "title"), or an empty
    list on any failure/misconfiguration — never raises. Failures are logged
    (not silently swallowed) so a Tavily outage/quota limit is diagnosable
    instead of looking like "no profiles found"."""
    if not Config.TAVILY_API_KEY:
        logger.warning("tavily_search_raw skipped: TAVILY_API_KEY not configured")
        return []

    url = "https://api.tavily.com/search"
    headers = {
        "Authorization": f"Bearer {Config.TAVILY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"query": query, "max_results": max_results}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json().get("results", [])
    except requests.exceptions.HTTPError as exc:
        body = exc.response.text[:300] if exc.response is not None else str(exc)
        logger.error("Tavily search failed (query=%r): HTTP %s — %s", query, exc.response.status_code if exc.response is not None else "?", body)
        return []
    except Exception as exc:
        logger.error("Tavily search failed (query=%r): %s", query, exc)
        return []
