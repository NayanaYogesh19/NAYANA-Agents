import os
from config.config import SUPABASE_URL, SUPABASE_KEY

_client = None
_write_client = None


def get_client():
    """
    Return a cached Supabase client (publishable key — read access).
    Returns None gracefully when credentials are not configured.
    """
    global _client

    if _client is not None:
        return _client

    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _client
    except Exception:
        return None


def get_write_client():
    """
    Return a cached Supabase client using the service role key.
    Required for tables with RLS (rag_resolutions, writing_style_examples).
    Falls back to the publishable client if no service key is configured.
    """
    global _write_client

    if _write_client is not None:
        return _write_client

    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not SUPABASE_URL or not service_key:
        return get_client()

    try:
        from supabase import create_client
        _write_client = create_client(SUPABASE_URL, service_key)
        return _write_client
    except Exception:
        return get_client()
