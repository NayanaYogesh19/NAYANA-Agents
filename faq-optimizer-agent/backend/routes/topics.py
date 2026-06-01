from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.scraper import WebScraper
from backend.services.llm_service import LLMService

import logging

logger = logging.getLogger(__name__)

# =====================================================
# ROUTER
# =====================================================

router = APIRouter(

    tags=["topics"]
)

# =====================================================
# SERVICES
# =====================================================

scraper = WebScraper()

llm_service = LLMService()

# =====================================================
# REQUEST MODEL
# =====================================================

class TopicRequest(BaseModel):

    website_url: str

# =====================================================
# GENERATE TOPICS
# =====================================================

@router.post("/generate-topics")
async def generate_topics(
    request: TopicRequest
):

    try:

        logger.info(
            f"Generating topics for: "
            f"{request.website_url}"
        )

        # ============================================
        # SCRAPE WEBSITE
        # ============================================

        website_content = scraper.scrape_website(

            request.website_url
        )

        if not website_content:

            raise HTTPException(

                status_code=400,

                detail="Failed to scrape website"
            )

        logger.info(
            f"Scraped content length: "
            f"{len(website_content)}"
        )

        # ============================================
        # GENERATE CATEGORIZED TOPICS
        # ============================================

        categorized_topics = (

            llm_service.generate_topics(
                website_content
            )
        )

        logger.info(
            f"Generated categorized topics: "
            f"{categorized_topics}"
        )

        # ============================================
        # RESPONSE
        # ============================================

        return {

            "success": True,

            "product_topics":

                categorized_topics.get(
                    "product_topics",
                    []
                ),

            "application_topics":

                categorized_topics.get(
                    "application_topics",
                    []
                )
        }

    except HTTPException:

        raise

    except Exception as e:

        logger.error(
            f"Topic generation error: {str(e)}"
        )

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )