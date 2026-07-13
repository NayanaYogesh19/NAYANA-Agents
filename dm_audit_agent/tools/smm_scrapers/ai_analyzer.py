"""
ai_analyzer.py — ported from Reach_Engagement_Follower_Analytics_Agent,
adapted to reuse this project's shared OpenRouter LLM factory (agents/llm.py)
instead of instantiating a second OpenAI client.
"""

from __future__ import annotations

import json

from agents.llm import get_llm


class AIAnalyzer:
    def analyze_social_profile(self, platform: str, text: str) -> dict:
        prompt = f"""Analyze this {platform} social media profile.

PROFILE DATA:
{text}

Return ONLY valid JSON in this exact shape:
{{
    "content_angles": [],
    "post_types": [],
    "target_audience": "",
    "brand_tone": "",
    "recommended_strategy": []
}}"""

        llm = get_llm(temperature=0.3)
        response = llm.invoke(prompt)

        try:
            return json.loads(response.content)
        except (json.JSONDecodeError, AttributeError):
            return {
                "content_angles": ["Branding"],
                "post_types": ["Image Posts"],
                "target_audience": "General Audience",
                "brand_tone": "Professional",
                "recommended_strategy": ["Post consistently", "Increase engagement"],
            }
