from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from backend.config import settings
from backend.database.faq_repository import FAQRepository
from backend.database.website_repository import WebsiteRepository
from backend.database.analytics_repository import AnalyticsRepository
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

faq_repo = FAQRepository()
website_repo = WebsiteRepository()
analytics_repo = AnalyticsRepository()

security = HTTPBearer()

class LoginRequest(BaseModel):
    password: str

# =================================================
# ADMIN LOGIN
# =================================================
@router.post("/admin/login")
async def admin_login(request: LoginRequest):
    if request.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"status": "success", "message": "Login successful"}

# =================================================
# GET ALL WEBSITES
# =================================================
@router.get("/admin/websites")
async def get_websites():
    try:
        websites = website_repo.get_all_websites()
        return {"websites": websites}
    except Exception as e:
        logger.error(f"Error fetching websites: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch websites")

# =================================================
# GET FAQS BY WEBSITE
# =================================================
@router.get("/admin/faqs/{website_url}")
async def get_admin_faqs(website_url: str):
    try:
        faqs = faq_repo.get_faqs(website_url)
        return {"faqs": faqs}
    except Exception as e:
        logger.error(f"Error fetching FAQs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch FAQs")

# =================================================
# GET ANALYTICS
# =================================================
@router.get("/admin/analytics")
async def get_analytics():
    try:
        logger.info("Fetching analytics...")
        analytics = analytics_repo.get_overall_analytics()
        logger.info(f"Analytics data: {analytics}")
        return {"analytics": analytics}
    except Exception as e:
        logger.error(f"Error fetching analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch analytics")

# =================================================
# DELETE FAQ
# =================================================
@router.delete("/admin/faqs/{website_url}/{faq_id}")
async def delete_faq(website_url: str, faq_id: int):
    try:
        # TODO: Implement delete in FAQRepository
        return {"status": "success", "message": "FAQ deleted (placeholder)"}
    except Exception as e:
        logger.error(f"Error deleting FAQ: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete FAQ")
