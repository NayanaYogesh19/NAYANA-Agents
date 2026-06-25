import requests
import os

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)
print("OPENROUTER KEY:")
print(OPENROUTER_API_KEY)

async def generate_seo_content(

    product_name,

    keyword
):

    prompt = f"""
You are an expert SEO strategist for food and ecommerce websites.

Product Name:
{product_name}

Primary Keyword:
{keyword}

Brand:
Jandhyala Foods

Generate ONLY valid JSON.

{{
  "suggested_title": "",
  "suggested_meta_description": "",
  "h1": "",
  "h2": [],
  "h3_h6": [],
  "featured_snippet": "",
  "faqs": [],
  "main_image_alt": "",
  "other_image_alts": [],
  "internal_linking_ideas": [],
  "anchor_texts": []
}}

Rules:

- Title must be SEO optimized
- Title max 60-65 characters
- Meta description max 160 characters
- Use keyword naturally
- Avoid keyword stuffing
- Create 4 H2 headings
- Create 6 H3-H6 headings
- Create 4 FAQs
- Create 4 supporting image alt texts
- Create 4 anchor text suggestions
- Create 4 internal linking suggestions
- Featured snippet should directly answer the topic
- Use Andhra food terminology
- Sound human written
- Different for every product
- Return JSON only
"""

    response = requests.post(

        "https://openrouter.ai/api/v1/chat/completions",

        headers={

            "Authorization": f"Bearer {OPENROUTER_API_KEY}",

            "Content-Type": "application/json"
        },

        json={

            "model": "openai/gpt-4o-mini",

            "messages": [

                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
    )

    data = response.json()

    print("OPENROUTER RESPONSE:")
    print(data)

    # -----------------------------------
    # SAFE FALLBACK
    # -----------------------------------

    if "choices" not in data:

        print("OPENROUTER FAILED")

        return {

            "title": f"{product_name} | Jandhyala Foods",

            "meta_description": (

                f"Experience authentic "
                f"{product_name} from "
                f"Jandhyala Foods."
            ),

            "h2": [],

            "h3_h6": [],

            "featured_snippet": (

                f"{product_name} is a "
                f"traditional Andhra specialty."
            ),

            "faqs": [

                f"What is {product_name}?",

                f"How to store {product_name}?",

                f"Where to buy {product_name}?"
            ]
        }

    # -----------------------------------
    # SUCCESS RESPONSE
    # -----------------------------------

    content = data["choices"][0]["message"]["content"]

    return content