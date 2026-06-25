import os
import json

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


class AIAnalyzer:

    def analyze_social_profile(
        self,
        platform,
        text
    ):

        prompt = f"""
        Analyze this {platform} social media profile.

        PROFILE DATA:
        {text}

        Return ONLY valid JSON.

        Example format:

        {{
            "content_angles": [],
            "post_types": [],
            "target_audience": "",
            "brand_tone": "",
            "recommended_strategy": []
        }}
        """

        response = client.chat.completions.create(

            model="openai/gpt-4o-mini",

            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.3
        )

        content = response.choices[0].message.content

        try:

            return json.loads(content)

        except:

            return {
                "content_angles": [
                    "Branding"
                ],
                "post_types": [
                    "Image Posts"
                ],
                "target_audience": "General Audience",
                "brand_tone": "Professional",
                "recommended_strategy": [
                    "Post consistently",
                    "Increase engagement"
                ]
            }