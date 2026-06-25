from config.config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

print("URL:", SUPABASE_URL)
print("KEY LENGTH:", len(SUPABASE_KEY) if SUPABASE_KEY else 0)

try:
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    result = client.table("companies").select("*").limit(1).execute()

    print("\nSUCCESS")
    print(result)

except Exception as e:
    print("\nFAILED")
    print(type(e))
    print(e)