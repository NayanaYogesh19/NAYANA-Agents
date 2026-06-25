from config.config import SUPABASE_URL, SUPABASE_KEY

_client = None


def get_client():
    """
    Return a cached Supabase client.
    Returns None gracefully when credentials are not configured so that the
    rest of the system degrades to local-only mode without crashing.
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
