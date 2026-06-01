from backend.database.supabase_client import supabase_client
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AnalyticsRepository:
    """Track FAQ performance metrics"""
    
    def __init__(self):
        self.client = supabase_client.client
    
    def record_impression(self, faq_id: int):
        """Record when a FAQ is viewed/shown"""
        try:
            self.client.table('faq_analytics').insert({
                'faq_id': faq_id,
                'event_type': 'impression',
                'created_at': datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error recording impression: {str(e)}")
    
    def record_click(self, faq_id: int):
        """Record when a FAQ is clicked/expanded"""
        try:
            self.client.table('faq_analytics').insert({
                'faq_id': faq_id,
                'event_type': 'click',
                'created_at': datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error recording click: {str(e)}")
    
    def get_top_performing_faqs(self, company_name: str, limit: int = 10):
        """Get FAQs with most impressions"""
        try:
            result = self.client.rpc('get_top_faqs', {
                'company': company_name,
                'result_limit': limit
            }).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting top FAQs: {str(e)}")
            return []
    
    def get_category_performance(self, company_name: str):
        """Get performance breakdown by AEO/GEO/SEO"""
        try:
            result = self.client.rpc('get_category_performance', {
                'company': company_name
            }).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting category performance: {str(e)}")
            return []