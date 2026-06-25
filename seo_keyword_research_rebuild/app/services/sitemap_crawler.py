from app.services.sitemap_parser import (
    parse_sitemap
)

from app.services.sitemap_parser import (
    parse_sitemap
)

from app.services.product_classifier import (
    classify_product
)

# =========================================
# CRAWL SITEMAP
# =========================================

def crawl_sitemap(sitemap_url):

    print(
        "CRAWLING SITEMAP:",
        sitemap_url
    )

    urls = parse_sitemap(
        sitemap_url
    )

    print(
        "TOTAL URLS FOUND:",
        len(urls)
    )

    products = []

    # =====================================
    # DEBUG URLS
    # =====================================

    for url in urls:

        print("URL:", url)

        try:

            product = classify_product(
                url
            )

            # =================================
            # ACCEPTED
            # =================================

            if product:

                print(
                    "ACCEPTED:",
                    product
                )

                products.append(
                    product
                )

            # =================================
            # REJECTED
            # =================================

            else:

                print(
                    "REJECTED:",
                    url
                )

        except Exception as e:

            print(
                "SCRAPER ERROR:",
                e
            )

    # =====================================
    # REMOVE DUPLICATES
    # =====================================

    unique_products = []

    seen = set()

    for product in products:

        if product["url"] not in seen:

            seen.add(
                product["url"]
            )

            unique_products.append(
                product
            )

    print(
        "UNIQUE PRODUCTS:",
        len(unique_products)
    )

    return unique_products

