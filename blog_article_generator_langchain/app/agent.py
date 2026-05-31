from app.tools.tavily_search import tavily_search
from app.models.openrouter import call_openrouter
from app.memory.session_memory import session_data
import json

def agent(user_input):

        # ==========================
        # PHASE 2 - TOPIC SELECTION
        # ==========================

        if user_input in [
            "1", "2", "3", "4",
            "5", "6", "7", "8"
        ]:

            if "topics" not in session_data:
                return {
                    "status": "error",
                    "message": "No topics found. Please provide a company URL first."
                }

            topic_index = int(user_input) - 1

            selected_topic = session_data["topics"][topic_index]

            keyword_prompt = f"""
        You are an SEO Keyword Research Specialist.

        Topic:
        {selected_topic}

        Generate:

        1. Primary Keywords (5)
        2. Secondary Keywords (10)
        3. Long Tail Keywords (10)

        Return ONLY valid JSON.

        {{
            "primary_keywords": [],
            "secondary_keywords": [],
            "long_tail_keywords": []
        }}
        """

            keyword_response = call_openrouter(
                keyword_prompt
            )

            keyword_content = keyword_response["choices"][0]["message"]["content"]

            keyword_content = keyword_content.replace(
                "```json",
                ""
            )

            keyword_content = keyword_content.replace(
                "```",
                ""
            )

            keyword_content = keyword_content.strip()

            keyword_data = json.loads(
                keyword_content
            )

            session_data["primary_keywords"] = (
                keyword_data["primary_keywords"]
            )

            session_data["secondary_keywords"] = (
                keyword_data["secondary_keywords"]
            )

            session_data["long_tail_keywords"] = (
                keyword_data["long_tail_keywords"]
            )

            outline_prompt = f"""
You are an expert SEO strategist.

Topic:
{selected_topic}

Primary Keywords:
{session_data["primary_keywords"]}

Secondary Keywords:
{session_data["secondary_keywords"]}

Long Tail Keywords:
{session_data["long_tail_keywords"]}

Create:

1. H1 Title
2. Introduction Hook
3. Search Intent
4. H2 Sections
5. Suggested Visuals
6. CTA

Return ONLY valid JSON.

{{
    "h1": "",
    "introduction_hook": "",
    "search_intent": "",
    "h2_sections": [],
    "visual_suggestions": [],
    "cta": ""
}}
"""
            outline_response = call_openrouter(
                outline_prompt
            )

            outline_content = (
                outline_response["choices"][0]["message"]["content"]
            )

            outline_content = outline_content.replace(
                "```json",
                ""
            )

            outline_content = outline_content.replace(
                "```",
                ""
            )

            outline_content = outline_content.strip()

            outline_data = json.loads(
                outline_content
            )

            session_data["outline"] = outline_data

            session_data["selected_topic"] = selected_topic

            return {
                "status": "success",
                "step": "content_preferences",
                "selected_topic": selected_topic,
                "primary_keywords": keyword_data["primary_keywords"],
                "secondary_keywords": keyword_data["secondary_keywords"],
                "long_tail_keywords": keyword_data["long_tail_keywords"],
                "outline": outline_data,
                "content_types": [
                    "Blog",
                    "Article"
                ],
                "word_counts": [
                    800,
                    1200,
                    1500
                ]
            }
        # ==========================
        # PHASE 3 - CONTENT TYPE + WORD COUNT
        # ==========================

        if "," in user_input:

            try:

                content_type, word_count = user_input.split(",")

                content_type = content_type.strip()
                word_count = int(word_count.strip())

                session_data["content_type"] = content_type
                session_data["word_count"] = word_count

                return {
                        "status": "success",
                        "step": "structure_selection",
                        "selected_topic": session_data["selected_topic"],
                        "content_type": content_type,
                        "word_count": word_count,
                        "structures": [
                            "How-To",
                            "Listicle",
                            "Case Study"
                        ]
                    }

            except Exception:

                return {
                        "status": "error",
                        "message": "Invalid format. Use: Blog,1200"
                    }

        # ==========================
        # PHASE 4 - STRUCTURE SELECTION + CONTENT GENERATION
        # ==========================

        if user_input in ["How-To", "Listicle", "Case Study"]:

            session_data["structure"] = user_input

            prompt = f"""
        ```

        You are a professional SEO content writer.

        Company Summary:
        {session_data["company_summary"]}

        Topic:
        {session_data["selected_topic"]}

        Content Type:
        {session_data["content_type"]}

        Word Count:
        {session_data["word_count"]}

        Structure:
        {session_data["structure"]}

        Instructions:

        * Generate a complete SEO optimized content.
        * Use proper Markdown formatting.
        * Use exactly one H1 title (# Title).
        * Use H2 headings (## Heading).
        * Put every heading on a new line.
        * Put every paragraph on a new line.
        * Leave a blank line between sections.
        * Write approximately the requested word count.
        * Maintain a professional tone.
        * Make the content human-like.
        * Include an introduction.
        * Include main sections.
        * Include a conclusion.
        * Do not mention these instructions.

        Generate the final content now.
        """


            response = call_openrouter(prompt)

            if "choices" not in response:
                return {
                    "status": "error",
                    "message": response
                }

            final_content = response["choices"][0]["message"]["content"]

            return {
                "status": "success",
                "step": "completed",
                "topic": session_data["selected_topic"],
                "content_type": session_data["content_type"],
                "word_count": session_data["word_count"],
                "structure": session_data["structure"],
                "content": final_content
            }

        # ==========================
        # PHASE 1 - ADVANCED RESEARCH
        # ==========================

        company_data = tavily_search(user_input)

        industry_trends = tavily_search(
            f"{user_input} industry trends 2026"
        )

        competitor_data = tavily_search(
            f"{user_input} competitors"
        )

        pain_points = tavily_search(
            f"{user_input} customer challenges"
        )

        research_context = f"""
        ```

        Company Research:
        {company_data}

        Industry Trends:
        {industry_trends}

        Competitor Insights:
        {competitor_data}

        Pain Points:
        {pain_points}
        """


        prompt = f"""
        ```

        You are an expert SEO Strategist and Content Marketing Specialist.

        Analyze the company research below:

        {research_context}

        Perform:

        1. Industry Identification

        * Determine the company's primary industry.
        * Identify key products, services and technologies.

        2. Trend Analysis

        * Identify current and emerging industry trends.
        * Highlight innovations and technology advancements.

        3. Competitor Analysis

        * Identify likely competitors.
        * Determine content opportunities and gaps.

        4. User Pain Point Analysis

        * Identify common challenges faced by customers.
        * Identify common questions and search intent.

        5. Content Strategy

        * Identify evergreen topics.
        * Identify trending topics.
        * Identify high-value educational topics.

        Generate:

        Return ONLY valid JSON.

        {{
        "company_summary": "...",
        "industry": "...",
        "topics": [
        "...",
        "...",
        "...",
        "...",
        "...",
        "...",
        "...",
        "..."
        ]
        }}
        """


        response = call_openrouter(prompt)

        if "choices" not in response:
            return {
                "status": "error",
                "message": response
            }

        content = response["choices"][0]["message"]["content"]

        content = content.replace("```json", "")
        content = content.replace("```", "")
        content = content.strip()

        try:

            parsed = json.loads(content)

            session_data["company_summary"] = parsed["company_summary"]
            session_data["industry"] = parsed["industry"]
            session_data["topics"] = parsed["topics"]

            return {
                "status": "success",
                "step": "topic_selection",
                "company_summary": parsed["company_summary"],
                "industry": parsed["industry"],
                "topics": parsed["topics"]
            }

        except Exception as e:

            return {
                "status": "error",
                "message": f"JSON Parse Error: {str(e)}",
                "raw_output": content
            }

