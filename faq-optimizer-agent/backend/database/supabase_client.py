from supabase import create_client, Client
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Singleton Supabase client"""
    _instance = None
    _client: Client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                cls._client = create_client(
                    settings.supabase_url,
                    settings.supabase_key
                )
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase: {e}")
                raise
        return cls._instance
    
    @property
    def client(self) -> Client:
        return self._client

# Singleton instance
supabase_client = SupabaseClient()