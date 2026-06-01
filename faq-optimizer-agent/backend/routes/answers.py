from fastapi import APIRouter, HTTPException, Request

from backend.services.scraper import WebScraper
from backend.services.llm_service import LLMService
from backend.database.faq_repository import FAQRepository

import logging

logger = logging.getLogger(__name__)

# =====================================================
# ROUTER
# =====================================================

router = APIRouter(

    tags=["answers"]
)

# =====================================================
# SERVICES
# =====================================================

scraper = WebScraper()

llm_service = LLMService()

faq_repository = FAQRepository()

# =====================================================
# GENERATE ANSWERS
# =====================================================

@router.post("/generate-answers")
async def generate_answers(
    request: Request
):

    try:

        # =============================================
        # RAW JSON BODY
        # =============================================

        body = await request.json()

        print("\n====================")
        print("REQUEST BODY")
        print("====================")
        print(body)

        website_url = body.get(
            "website_url",
            ""
        )

        topic = body.get(
            "topic",
            ""
        )

        selected_questions = body.get(
            "selected_questions",
            []
        )

        logger.info(
            f"Answer generation for: "
            f"{website_url}"
        )

        # =============================================
        # SCRAPE WEBSITE
        # =============================================

        website_content = scraper.scrape_website(
            website_url
        )

        if not website_content:

            raise HTTPException(

                status_code=400,

                detail="Failed to scrape website"
            )

        # =============================================
        # EXTRACT QUESTION TEXTS
        # =============================================

        questions = []

        for q in selected_questions:

            if isinstance(q, dict):

                questions.append(

                    q.get(
                        "question",
                        ""
                    )
                )

            elif isinstance(q, str):

                questions.append(q)

        logger.info(
            f"Questions received: "
            f"{len(questions)}"
        )

        # =============================================
        # GENERATE ANSWERS
        # =============================================

        generated_faqs = (

            llm_service.generate_answers(

                website_content=
                    website_content,

                topic=
                    topic,

                questions=
                    questions
            )
        )

        logger.info(
            f"Generated FAQs: "
            f"{len(generated_faqs)}"
        )

        # =============================================
        # STORE FAQS
        # =============================================

        for faq in generated_faqs:

            try:

                faq_repository.create_faq(

                    website_url=
                        website_url,

                    topic=
                        topic,

                    question=
                        faq.get(
                            "question",
                            ""
                        ),

                    answer=
                        faq.get(
                            "answer",
                            ""
                        ),

                    category=
                        faq.get(
                            "category",
                            "SEO"
                        )
                )

            except Exception as db_error:

                logger.error(
                    f"DB insert error: "
                    f"{str(db_error)}"
                )

        # =============================================
        # COMPANY NAME
        # =============================================

        company_name = (

            website_url

            .replace(
                "https://",
                ""
            )

            .replace(
                "http://",
                ""
            )

            .replace(
                "www.",
                ""
            )

            .split("/")[0]
        )

        # =============================================
        # RESPONSE
        # =============================================

        return {

            "faqs":
                generated_faqs,

            "company_name":
                company_name,

            "topic":
                topic,

            "analytics": {

                "total_faqs":
                    len(generated_faqs)
            },

            "message":
                "Answers generated successfully"
        }

    except Exception as e:

        logger.error(
            f"Answer generation error: "
            f"{str(e)}"
        )

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )