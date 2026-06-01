from fastapi import APIRouter, HTTPException

from backend.models import (
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    Question
)

from backend.services.scraper import WebScraper
from backend.services.llm_service import LLMService
from backend.services.duplicate_checker import DuplicateChecker

import logging

logger = logging.getLogger(__name__)

# =====================================================
# ROUTER
# =====================================================

router = APIRouter(
    tags=["questions"]
)

# =====================================================
# SERVICES
# =====================================================

scraper = WebScraper()

llm_service = LLMService()

duplicate_checker = DuplicateChecker()

# =====================================================
# GENERATE QUESTIONS
# =====================================================

@router.post(
    "/generate-questions",
    response_model=QuestionGenerationResponse
)

async def generate_questions(
    request: QuestionGenerationRequest
):

    """
    Generate FAQ Questions

    Flow:
    1. Scrape website
    2. Generate AI questions
    3. Remove duplicates
    4. Return unique questions
    """

    try:

        logger.info(
            f"Question generation for: {request.website_url}"
        )

        # =============================================
        # COMPANY NAME
        # =============================================

        company_name = scraper.extract_domain(
            request.website_url
        )

        logger.info(
            f"Company: {company_name}"
        )

        # =============================================
        # STEP 1 - SCRAPE WEBSITE
        # =============================================

        try:

            website_content = scraper.scrape_website(
                request.website_url
            )

            if not website_content:

                raise HTTPException(

                    status_code=400,

                    detail="Failed to scrape website"
                )

            logger.info(
                f"Scraped content length: {len(website_content)}"
            )

        except Exception as e:

            logger.error(
                f"Scraping failed: {str(e)}"
            )

            raise HTTPException(

                status_code=400,

                detail=f"Website scraping failed: {str(e)}"
            )

        # =============================================
        # STEP 2 - GENERATE QUESTIONS
        # =============================================

        try:

            questions_data = (
                llm_service.generate_questions(
                    website_content,
                    request.topic
                )
            )

            logger.info(
                f"Generated {len(questions_data)} questions"
            )

        except Exception as e:

            logger.error(
                f"Question generation failed: {str(e)}"
            )

            raise HTTPException(

                status_code=500,

                detail=f"Question generation failed: {str(e)}"
            )

        # =============================================
        # STEP 3 - REMOVE DUPLICATES
        # =============================================

        duplicates_removed = 0

        try:

            unique_questions = (
                duplicate_checker.filter_duplicates(
                    questions_data,
                    company_name
                )
            )

            duplicates_removed = (
                len(questions_data)
                - len(unique_questions)
            )

            if duplicates_removed > 0:

                logger.info(
                    f"Removed {duplicates_removed} duplicates"
                )

            if len(unique_questions) < 3:

                logger.warning(
                    "Most generated questions were duplicates"
                )

        except Exception as e:

            logger.error(
                f"Duplicate check failed: {str(e)}"
            )

            # CONTINUE WITHOUT DUPLICATE FILTER

            unique_questions = questions_data

        # =============================================
        # STEP 4 - FORMAT RESPONSE
        # =============================================

        questions = [

            Question(

                question=q["question"],

                category=q["category"]
            )

            for q in unique_questions
        ]

        # =============================================
        # RESPONSE MESSAGE
        # =============================================

        message = (
            f"Generated {len(questions)} questions"
        )

        if duplicates_removed > 0:

            message += (
                f" ({duplicates_removed} duplicates filtered)"
            )

        logger.info(message)

        # =============================================
        # RETURN RESPONSE
        # =============================================

        return QuestionGenerationResponse(

            questions=questions,

            total_count=len(questions),

            message=message
        )

    # =================================================
    # HTTP EXCEPTION
    # =================================================

    except HTTPException:

        raise

    # =================================================
    # UNEXPECTED ERROR
    # =================================================

    except Exception as e:

        logger.error(
            f"Unexpected error: {str(e)}",
            exc_info=True
        )

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )