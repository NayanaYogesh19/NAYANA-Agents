from tools.sitemap_tool import discover_urls

from tools.scraper_tool import scrape_page

from tools.seranking_tool import (
    get_keyword_data,
    get_keyword_rank
)

from tools.keyword_extractor import extract_keywords

from tools.keyword_mapper import normalize_keyword

from data.product_master import PRODUCTS

from tools.seo_ai_generator import generate_seo_content
import json


async def run_seo_agent(
    website_url,
    company_name,
    max_pages
):

    # -----------------------------------
    # DISCOVER URLS
    # -----------------------------------

    urls = await discover_urls(

        website_url,

        max_pages
    )

    results = []

    # -----------------------------------
    # LOOP THROUGH URLS
    # -----------------------------------

    for url in urls:

        # -----------------------------------
        # FILTER ONLY TARGET PRODUCTS
        # -----------------------------------

        matched = False

        product_name = ""

        for slug, product_name in PRODUCTS.items():

            if slug in url.lower():

                matched = True

                break

        if not matched:

            continue

        print(f"MATCHED PRODUCT URL: {url}")

        print(f"PRODUCT NAME: {product_name}")

        # -----------------------------------
        # SCRAPE PAGE
        # -----------------------------------

        extracted = await scrape_page(url)

        # -----------------------------------
        # EXTRACT KEYWORDS
        # -----------------------------------

        keywords = await extract_keywords(

            extracted.get(
                "title",
                ""
            ),

            url
        )

        primary_keywords = keywords.get(
            "primary",
            []
        )

        keyword = ""

        lsi_keywords = []

        if primary_keywords:

            raw_keyword = primary_keywords[0]

            print(f"RAW KEYWORD: {raw_keyword}")

            # -----------------------------------
            # NORMALIZE KEYWORD
            # -----------------------------------

            keyword = normalize_keyword(
                raw_keyword
            )

            print(f"NORMALIZED KEYWORD: {keyword}")

            # -----------------------------------
            # LSI KEYWORDS
            # -----------------------------------

            lsi_keywords = [

                keyword,

                f"best {keyword}",

                f"homemade {keyword}",

                f"andhra {keyword}",

                f"buy {keyword} online"
            ]

        else:

            raw_keyword = ""

        print(f"PRIMARY KEYWORD: {keyword}")

        # -----------------------------------
        # FETCH REAL SEO METRICS
        # -----------------------------------

        keyword_data = await get_keyword_data(
            keyword
        )

        current_ranking = await get_keyword_rank(

            keyword,

            website_url
        )

        print("SE RANKING DATA:")
        print(keyword_data)

        print("CURRENT RANKING:")
        print(current_ranking)

        # -----------------------------------
        # AI GENERATED SEO CONTENT
        # -----------------------------------

        ai_content = await generate_seo_content(

            product_name,

            keyword
        )

        print("AI SEO CONTENT:")
        print(ai_content)

        # -----------------------------------
        # PARSE AI JSON
        # -----------------------------------

        try:

            cleaned_content = (

                ai_content
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            ai_data = json.loads(
                cleaned_content
            )

        except Exception as e:

            print("AI PARSE ERROR:")
            print(e)

            ai_data = {}

        # -----------------------------------
        # AI GENERATED FIELDS
        # -----------------------------------

        suggested_url = (

            f"/{keyword.replace(' ', '-')}"
        )

        suggested_title = ai_data.get(

            "suggested_title",

            f"{product_name} | Jandhyala Foods"
        )

        suggested_meta = ai_data.get(

            "suggested_meta_description",

            f"Experience authentic {product_name}"
        )

        h1 = ai_data.get(

            "h1",

            extracted.get(
                "h1",
                ""
            )
        )

        dynamic_h2 = ai_data.get(

            "h2",

            []
        )

        dynamic_h3_h6 = ai_data.get(

            "h3_h6",

            []
        )

        featured_snippet = ai_data.get(

            "featured_snippet",

            ""
        )

        faqs = ai_data.get(

            "faqs",

            []
        )

        main_image_alt = ai_data.get(

            "main_image_alt",

            extracted.get(
                "main_image_alt",
                ""
            )
        )

        other_image_alts = ai_data.get(

            "other_image_alts",

            []
        )

        anchor_texts = ai_data.get(

            "anchor_texts",

            extracted.get(
                "anchor_texts",
                []
            )
        )

        internal_linking_ideas = ai_data.get(

            "internal_linking_ideas",

            []
        )

        # -----------------------------------
        # COMBO KEYWORDS
        # -----------------------------------

        combo_keywords = [

            keyword,

            f"best {keyword}",

            f"homemade {keyword}",

            f"buy {keyword}"
        ]

        # -----------------------------------
        # APPEND RESULTS
        # -----------------------------------

        results.append({

            "product_name": product_name,

            "url": url,

            "title": extracted.get(
                "title",
                ""
            ),

            "title_length": extracted.get(
                "title_length",
                0
            ),

            "meta_description": extracted.get(
                "meta_description",
                ""
            ),

            "meta_description_length": extracted.get(
                "meta_description_length",
                0
            ),

"h1": h1,

"h2": dynamic_h2,

"h3_h6": dynamic_h3_h6,

"main_image_alt": main_image_alt,

"other_image_alts": other_image_alts,

"anchor_texts": anchor_texts,

"internal_linking_ideas": internal_linking_ideas,
            "internal_links": extracted.get(
                "internal_links",
                []
            ),

            "canonical": extracted.get(
                "canonical",
                ""
            ),

            "og_title": extracted.get(
                "og_title",
                ""
            ),

            "og_description": extracted.get(
                "og_description",
                ""
            ),

            "schema_count": extracted.get(
                "schema_count",
                0
            ),

            "keyword": keyword_data.get(
                "keyword",
                keyword
            ),

            "volume": keyword_data.get(
                "volume",
                0
            ),

            "intent": keyword_data.get(
                "intent",
                ""
            ),

            "cpc": keyword_data.get(
                "cpc",
                0
            ),

            "competition": keyword_data.get(
                "competition",
                0
            ),

            "keyword_difficulty": keyword_data.get(
                "keyword_difficulty",
                0
            ),

            "current_ranking": current_ranking,

            "lsi_keywords": lsi_keywords,

            "suggested_url": suggested_url,

            "suggested_title": suggested_title,

            "suggested_meta": suggested_meta,

            "featured_snippet": featured_snippet,

            "combo_keywords": combo_keywords,

            "faqs": faqs,

            "ai_generated_content": ai_content
        })

    return results