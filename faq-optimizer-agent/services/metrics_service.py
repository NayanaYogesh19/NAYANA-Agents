def calculate_metrics(faq_data):

    seo_score = 0
    aeo_score = 0
    geo_score = 0

    faq_list = faq_data.get("faq", [])

    total = len(faq_list)

    if total == 0:

        return {
            "seo_score": 0,
            "aeo_score": 0,
            "geo_score": 0
        }

    for item in faq_list:

        category = item.get("category", "").upper()

        answer = item.get("answer", "")

        # SEO scoring
        if category == "SEO":

            seo_score += 1

            if len(answer) > 80:
                seo_score += 1

        # AEO scoring
        elif category == "AEO":

            aeo_score += 1

            if "AI" in answer or "search" in answer:
                aeo_score += 1

        # GEO scoring
        elif category == "GEO":

            geo_score += 1

            if "local" in answer.lower() or "regional" in answer.lower():
                geo_score += 1

    return {

        "seo_score": round((seo_score / total) * 10, 1),

        "aeo_score": round((aeo_score / total) * 10, 1),

        "geo_score": round((geo_score / total) * 10, 1)
    }