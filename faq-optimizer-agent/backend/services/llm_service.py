import json
import logging

from openai import OpenAI

from backend.config import settings

logger = logging.getLogger(__name__)


class LLMService:

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self):

        self.client = OpenAI(

            api_key=
                settings.openrouter_api_key,

            base_url=
                "https://openrouter.ai/api/v1"
        )

        self.model = "openai/gpt-4o-mini"

    # =====================================================
    # CLEAN JSON RESPONSE
    # =====================================================

    def clean_json_response(
        self,
        content: str
    ):

        content = content.strip()

        if content.startswith("```json"):

            content = (

                content
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

        elif content.startswith("```"):

            content = (

                content
                .replace("```", "")
                .strip()
            )

        return content

    # =====================================================
    # EXTRACT WEBSITE CONTEXT
    # =====================================================

    def extract_website_context(

        self,

        website_content: str
    ):

        try:

            logger.info(
                "Extracting structured website context"
            )

            prompt = f"""

Analyze this website content carefully.

Extract structured business information.

STRICT RULES:

1. Use ONLY information found
   or inferable from the website

2. Avoid hallucinations

3. Avoid assumptions

4. Keep entries concise

5. Return ONLY JSON

6. Products/services should reflect
   actual offerings from the website

7. Applications should reflect
   real use cases or industries

WEBSITE CONTENT:
{website_content[:5000]}

RETURN FORMAT:

{{
    "company_type": "",

    "products": [],

    "services": [],

    "industries": [],

    "applications": [],

    "features": [],

    "keywords": []
}}
"""

            response = self.client.chat.completions.create(

                model=self.model,

                messages=[

                    {
                        "role": "system",

                        "content":
                            "You extract structured business context."
                    },

                    {
                        "role": "user",

                        "content": prompt
                    }
                ],

                temperature=0.2
            )

            content = (

                response
                .choices[0]
                .message.content
            )

            content = self.clean_json_response(
                content
            )

            structured_context = json.loads(
                content
            )

            logger.info(
                f"Structured Context: "
                f"{structured_context}"
            )

            return structured_context

        except Exception as e:

            logger.error(
                f"Context extraction error: {e}"
            )

            return {

                "company_type": "",

                "products": [],

                "services": [],

                "industries": [],

                "applications": [],

                "features": [],

                "keywords": []
            }

    # =====================================================
    # GENERATE TOPICS
    # =====================================================

    def generate_topics(

        self,

        website_content: str
    ):

        logger.info(
            "Generating categorized topics"
        )

        structured_context = (

            self.extract_website_context(
                website_content
            )
        )

        prompt = f"""

Analyze this website carefully.

Generate two categories of FAQ topics:

1. product_topics
2. application_topics

STRUCTURED WEBSITE CONTEXT:
{json.dumps(structured_context, indent=2)}

STRICT RULES:

1. Topics must be highly relevant
   to the provided website

2. Avoid generic business wording

3. Avoid vague topics like:
   - efficiency
   - productivity
   - innovation
   - automation
   - digital transformation

4. Product topics must reflect
   actual offerings from the website

5. Application topics must reflect
   real industries, use cases,
   operational scenarios,
   or implementation environments

6. Make topics specific instead of generic

7. Generate:
   - at least 5 product topics
   - at least 5 application topics

8. Every topic must be unique

9. Topics should help generate:
   - buyer-focused FAQs
   - product-selection FAQs
   - comparison FAQs
   - use-case FAQs

10. Return ONLY JSON

11. Topics must be SHORT phrases

12. Topics should NOT be full questions

13. Topics should NOT sound like blog titles

14. Avoid starting topics with:
- How
- Why
- Benefits
- Best
- Top
- Features of

15. Product topics should be:
- product names
- service names
- platform names
- solution names

16. Application topics should be:
- industries
- operational use cases
- business functions
- implementation scenarios

17. Keep each topic under 6 words

RETURN FORMAT:

{{
    "product_topics": [],

    "application_topics": []
}}
"""

        response = self.client.chat.completions.create(

            model=self.model,

            messages=[

                {
                    "role": "system",

                    "content":
                        "You generate website-aware FAQ topics."
                },

                {
                    "role": "user",

                    "content": prompt
                }
            ],

            temperature=0.4
        )

        content = (

            response
            .choices[0]
            .message.content
        )

        content = self.clean_json_response(
            content
        )

        categorized_topics = json.loads(
            content
        )

        logger.info(
            f"Generated categorized topics: "
            f"{categorized_topics}"
        )

        return categorized_topics

    # =====================================================
    # GENERATE QUESTIONS
    # =====================================================

    def generate_questions(

        self,

        website_content: str,

        topic: str
    ):

        logger.info(
            f"Generating questions for: {topic}"
        )

        structured_context = (

            self.extract_website_context(
                website_content
            )
        )

        prompt = f"""

Generate realistic buyer-intent FAQ questions.

STRUCTURED WEBSITE CONTEXT:
{json.dumps(structured_context, indent=2)}

TOPIC:
{topic}

STRICT RULES:

STRICT RULES:

1. Generate EXACTLY 20 questions

2. Distribute questions across:

- SEO
- GEO
- AEO

3. Generate approximately:
- 7 SEO questions
- 7 GEO questions
- 6 AEO questions

4. Every question must contain
   the correct category label

5. Every question must be unique

6. Avoid semantic duplicates

7. Avoid reworded duplicate questions

8. Questions must feel realistic
   and buyer-focused

9. Questions must relate directly
   to the provided website

10. Avoid generic business questions

DO NOT generate questions like:
- How does X improve efficiency?
- How does X increase productivity?
- Why is X important?
- How does X streamline operations?

11. Focus on real buyer intent:
   - product selection
   - product comparison
   - compatibility
   - applications
   - use cases
   - implementation
   - integration
   - operational suitability
   - deployment scenarios
   - industry-specific usage

12. Questions should sound natural,
   realistic, and search-oriented

13. Avoid promotional wording

14. Questions should help users:
   - compare products
   - choose products
   - understand applications
   - evaluate suitability

15. Questions must feel
   website-specific instead of generic

16. Return ONLY JSON

RETURN FORMAT:

[
    {{
        "question": "...",
        "category": "SEO"
    }}
]
"""

        response = self.client.chat.completions.create(

            model=self.model,

            messages=[

                {
                    "role": "system",

                    "content":
                        "You generate realistic website-specific FAQ questions."
                },

                {
                    "role": "user",

                    "content": prompt
                }
            ],

            temperature=0.5
        )

        content = (

            response
            .choices[0]
            .message.content
        )

        content = self.clean_json_response(
            content
        )

        questions = json.loads(
            content
        )

        logger.info(
            f"Generated {len(questions)} questions"
        )

        return questions

    # =====================================================
    # GENERATE ANSWERS
    # =====================================================

    def generate_answers(

        self,

        website_content: str,

        topic: str,

        questions: list
    ):

        logger.info(
            f"Generating answers for: {topic}"
        )

        structured_context = (

            self.extract_website_context(
                website_content
            )
        )

        questions_text = "\n".join([

            f"- {q}"

            for q in questions
        ])

        prompt = f"""

Generate concise, factual,
website-specific FAQ answers.

STRUCTURED WEBSITE CONTEXT:
{json.dumps(structured_context, indent=2)}

TOPIC:
{topic}

QUESTIONS:
{questions_text}

STRICT RULES:

1. Keep each answer between 40-70 words

2. Maximum 3 sentences only

3. Start every answer with a direct,
   factual statement

4. Add 1-2 useful supporting points
   only when necessary

5. Avoid generic wording

6. Avoid repetitive phrases across answers

DO NOT repeatedly use:
- safety
- efficiency
- productivity
- workflow
- reliability
- automation

7. Use varied terminology

8. Use factual buyer-focused tone

9. Avoid promotional language

DO NOT use phrases like:
- game-changer
- cutting-edge
- industry-leading
- next-generation
- enhances productivity
- streamlines operations

10. Do NOT invent:
   - IoT monitoring
   - predictive maintenance
   - smart technology
   - training programs
   - certifications
   - automation systems

unless explicitly mentioned
in the website content

11. Answers must feel specific
   to the provided website

12. Avoid generic explanations
   that could apply to any company

13. Focus answers on:
   - product usage
   - product comparison
   - applications
   - compatibility
   - operational suitability
   - implementation scenarios
   - deployment environments

14. If website information is unclear,
   avoid making detailed claims

15. Use concise factual language

16. Return ONLY JSON

RETURN FORMAT:

[
    {{
        "question": "...",
        "answer": "...",
        "category": "SEO"
    }}
]
"""

        response = self.client.chat.completions.create(

            model=self.model,

            messages=[

                {
                    "role": "system",

                    "content":
                        "You generate concise website-specific FAQ answers."
                },

                {
                    "role": "user",

                    "content": prompt
                }
            ],

            temperature=0.4
        )

        content = (

            response
            .choices[0]
            .message.content
        )

        content = self.clean_json_response(
            content
        )

        faqs = json.loads(
            content
        )

        logger.info(
            f"Generated {len(faqs)} FAQs"
        )

        return faqs