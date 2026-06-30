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

    def get_overall_analytics(self):
        """Get overall analytics summary"""
        try:
            # Get total websites
            websites_response = self.client.table("websites").select("*").execute()
            total_websites = len(websites_response.data)

            # Get total FAQs and sum impressions/clicks across all websites
            total_faqs = 0
            total_impressions = 0
            total_clicks = 0

            for website in websites_response.data:
                table_name = website.get("table_name")
                if table_name:
                    try:
                        faqs_response = self.client.table(table_name).select("*").execute()
                        total_faqs += len(faqs_response.data)
                        for faq in faqs_response.data:
                            total_impressions += faq.get("impressions", 0)
                            total_clicks += faq.get("clicks", 0)
                    except Exception as e:
                        logger.warning(f"Could not fetch from {table_name}: {str(e)}")
                        continue

            # Calculate average CTR
            avg_ctr = 0.0
            if total_impressions > 0:
                avg_ctr = (total_clicks / total_impressions) * 100

            return {
                "total_websites": total_websites,
                "total_faqs": total_faqs,
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "avg_ctr": round(avg_ctr, 2)
            }
        except Exception as e:
            logger.error(f"Error getting overall analytics: {str(e)}")
            return {
                "total_websites": 0,
                "total_faqs": 0,
                "total_impressions": 0,
                "total_clicks": 0,
                "avg_ctr": 0.0
            }
