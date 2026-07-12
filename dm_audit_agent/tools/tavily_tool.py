"""
tavily_tool.py — Tavily web search tool.

Mirrors the "Tavily3" / "Search in Tavily" nodes used across the Keyword
Research, SEO Audit, SMM Gap Analysis and Strategy agents in the n8n workflow.
"""

from __future__ import annotations

import requests
from langchain.tools import tool

from config import Config


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
