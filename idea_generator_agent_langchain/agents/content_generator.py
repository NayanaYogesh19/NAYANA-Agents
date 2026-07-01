import random

from langchain_core.messages import SystemMessage, HumanMessage

from services.openrouter import get_llm
from prompts.prompt import SYSTEM_PROMPT, USER_PROMPT


def generate_content(data: dict) -> str:
    """
    Equivalent to the n8n AI Agent node.
    Feeds rich website context + trends to the LLM.
    """

    llm = get_llm()

    domain       = data.get("domain", "")
    topic        = data.get("topic", "")
    keywords     = data.get("keywords", [])
    lead_magnet  = data.get("lead_magnet", "none")

    # Rich website context (keys set by keyword_extractor)
    page_title   = data.get("website_page_title", "")
    meta_desc    = data.get("website_meta_description", "")
    headings     = data.get("website_headings", "")
    nav          = data.get("website_nav", "")
    services     = data.get("website_services", "")
    sections     = data.get("website_sections", "")
    ctas         = data.get("website_ctas", "")
    website_url  = data.get("website_url", "")

    # Truncate safety — keep total prompt context manageable
    page_title  = page_title[:150]
    meta_desc   = meta_desc[:250]
    headings    = headings[:400]
    nav         = nav[:200]
    services    = services[:400]
    sections    = sections[:400]
    ctas        = ctas[:150]

    # Trending searches — extract just the query strings for the prompt
    related_queries  = data.get("related_queries", {})
    rising           = related_queries.get("rising", []) if isinstance(related_queries, dict) else []
    # Convert to clean list of query strings (not raw JSON objects)
    trending_list = [item.get("query", "") for item in rising if isinstance(item, dict) and item.get("query")]
    trending_searches = ", ".join(trending_list) if trending_list else "none"

    print(f"\n[TRENDS] Fetched {len(trending_list)} rising trends for topic '{topic}':")
    for t in trending_list:
        print(f"  • {t}")

    keyword_string = ", ".join(keywords)

    # Inject a random seed token so LLM never gives the same output
    # for the same inputs — forces fresh angle each run
    random_seed = random.randint(100000, 999999)

    fmt = dict(
        domain=domain, topic=topic,
        keywords=keyword_string, trending_searches=trending_searches,
        page_title=page_title, meta_desc=meta_desc,
        headings=headings, nav=nav,
        services=services, ctas=ctas,
        website_url=website_url, random_seed=random_seed,
        lead_magnet=lead_magnet,
    )

    system_prompt_filled = SYSTEM_PROMPT.format(**fmt)
    user_prompt_filled   = USER_PROMPT.format(**fmt)

    response = llm.invoke([
        SystemMessage(content=system_prompt_filled),
        HumanMessage(content=user_prompt_filled)
    ])

    return response.content
