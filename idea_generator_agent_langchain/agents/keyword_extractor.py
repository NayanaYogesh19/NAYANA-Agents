import re


def extract_keywords(extracted_data: dict, parsed_data: dict) -> dict:
    """
    Extracts meaningful keywords from all website content fields
    and passes rich website context forward for AI use.
    """

    headings   = extracted_data.get("headings", "")
    body       = extracted_data.get("body_text", "")
    meta       = extracted_data.get("meta_description", "")
    meta_kw    = extracted_data.get("meta_keywords", "")
    nav        = extracted_data.get("nav_items", "")
    list_items = extracted_data.get("list_items", "")
    sections   = extracted_data.get("section_summaries", "")
    ctas       = extracted_data.get("cta_text", "")
    page_title = extracted_data.get("page_title", "")
    og_title   = extracted_data.get("og_title", "")
    og_desc    = extracted_data.get("og_description", "")

    website_url  = parsed_data.get("website_url", "")
    domain       = parsed_data.get("domain", "")
    topic        = parsed_data.get("topic", "")
    lead_magnet  = parsed_data.get("lead_magnet", "none")

    # Combine all text sources for keyword extraction
    raw_text = f"{headings} {body} {meta} {meta_kw} {nav} {list_items} {sections} {ctas} {page_title} {og_title} {og_desc}".lower()

    stopwords = {
        "the","and","for","with","this","that","are","was","from",
        "your","our","we","it","in","on","to","a","of","is","be",
        "as","at","by","an","or","but","not","will","have","has",
        "more","all","also","can","you","they","their","them","been",
        "into","about","which","when","what","how","who","any","get",
        "new","its","here","than","then","only","some","over","after",
        "just","make","like","know","time","such","very","would","could"
    }

    words = re.findall(r"\b[a-z]{4,}\b", raw_text)
    seen = set()
    keywords = []
    for w in words:
        if w not in stopwords and w not in seen:
            seen.add(w)
            keywords.append(w)
        if len(keywords) >= 30:
            break

    if not keywords:
        keywords = [topic, domain, "marketing", "content", "social media"]

    return {
        "keywords": keywords,
        "website_url": website_url,
        "domain": domain,
        "topic": topic,
        "lead_magnet": lead_magnet,
        # pass rich website context forward — trimmed to avoid LLM token overflow
        "website_page_title": (page_title or og_title)[:150],
        "website_meta_description": (meta or og_desc)[:250],
        "website_headings": headings[:400],
        "website_nav": nav[:200],
        "website_services": list_items[:400],
        "website_sections": sections[:400],
        "website_ctas": ctas[:150],
    }
