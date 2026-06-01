from supabase import create_client

from config.settings import (
    SUPABASE_URL,
    SUPABASE_KEY
)

from urllib.parse import urlparse


# -----------------------------------
# CONNECT SUPABASE
# -----------------------------------
supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# -----------------------------------
# EXTRACT COMPANY NAME
# -----------------------------------
def extract_company_name(url: str):

    domain = urlparse(url).netloc

    domain = domain.replace(
        "www.",
        ""
    )

    company = domain.split(".")[0]

    return company


# -----------------------------------
# SAVE FAQS
# -----------------------------------
def save_faqs(
    url: str,
    topic: str,
    faq_data: list
):

    company_name = extract_company_name(url)

    records = []

    for item in faq_data:

        records.append({

            "company_name": company_name,

            "website_url": url,

            "topic": topic,

            "question": item.get("question"),

            "answer": item.get("answer"),

            "category": item.get("category")

        })

    response = supabase.table(
        "faq_records"
    ).insert(records).execute()

    return response


# -----------------------------------
# GET COMPANY FAQS
# -----------------------------------
def get_company_faqs(url: str):

    company_name = extract_company_name(url)

    response = supabase.table(
        "faq_records"
    ).select("*").eq(
        "company_name",
        company_name
    ).execute()

    return response.data