"""
llm.py — Shared OpenRouter chat model factory for all LangChain agents.

Mirrors the "OpenRouter Chat Model*" nodes wired into every agent in the n8n
workflow (model: openai/gpt-4o-mini via OpenRouter).
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from config import Config


def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    return ChatOpenAI(
        model=Config.OPENROUTER_MODEL,
        api_key=Config.OPENROUTER_API_KEY,
        base_url=Config.OPENROUTER_BASE_URL,
        temperature=temperature,
    )
