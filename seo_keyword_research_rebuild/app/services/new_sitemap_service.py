from app.services.sitemap_discovery import discover_sitemap
from app.services.sitemap_parser import parse_sitemap
from app.services.product_classifier import classify_product


def get_service_product_urls(website_url):
    """Discover sitemap, parse all URLs, and return only service/product page entries."""
    print(f"DISCOVERING SITEMAP FOR: {website_url}")

    sitemap_url = discover_sitemap(website_url)

    if not sitemap_url:
        print("NO SITEMAP FOUND")
        return []

    print(f"SITEMAP: {sitemap_url}")

    all_urls = parse_sitemap(sitemap_url)
    print(f"TOTAL URLS IN SITEMAP: {len(all_urls)}")

    pages = []
    seen = set()

    for url in all_urls:
        if url in seen:
            continue
        seen.add(url)

        product = classify_product(url)
        if product:
            pages.append(product)

    print(f"SERVICE/PRODUCT PAGES FOUND: {len(pages)}")
    return pages
