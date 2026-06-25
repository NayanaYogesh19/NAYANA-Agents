import requests

from bs4 import BeautifulSoup


HEADERS = {

    "User-Agent": "Mozilla/5.0"
}


EXCLUDED_KEYWORDS = [

    "checkout",
    "cart",
    "privacy",
    "policy",
    "terms",
    "condition",
    "cookie",
    "account",
    "login",
    "register",
    "wishlist",
    "my-account",
    "track-order",
    "refund",
    "shipping",
    "author",
    "feed",
    "tag",
    "wp-json"
]


PRODUCT_PATTERNS = [

    "/product/",
    "/pickles/",
    "/powders/",
    "/masalas/",
    "/pre-mixes/",
    "/all-products/"
]


def is_valid_url(url):

    url_lower = url.lower()

    # EXCLUDE BAD URLS

    for keyword in EXCLUDED_KEYWORDS:

        if keyword in url_lower:

            return False

    return True


def is_product_url(url):

    url_lower = url.lower()

    for pattern in PRODUCT_PATTERNS:

        if pattern in url_lower:

            return True

    return False


async def discover_urls(
    base_url,
    max_pages=10
):

    discovered = []

    sitemap_urls = [

        f"{base_url}/sitemap.xml",

        f"{base_url}/wp-sitemap.xml",

        f"{base_url}/sitemap_index.xml"
    ]

    visited_sitemaps = set()

    # ---------------------------------------
    # RECURSIVE SITEMAP PARSER
    # ---------------------------------------

    def parse_sitemap(sitemap_url):

        if sitemap_url in visited_sitemaps:

            return

        visited_sitemaps.add(sitemap_url)

        try:

            print(f"Parsing sitemap: {sitemap_url}")

            response = requests.get(

                sitemap_url,

                headers=HEADERS,

                timeout=20
            )

            if response.status_code != 200:

                return

            soup = BeautifulSoup(

                response.text,

                "xml"
            )

            loc_tags = soup.find_all("loc")

            print(f"Found {len(loc_tags)} loc tags")

            for loc in loc_tags:

                url = loc.text.strip()

                # -----------------------------------
                # NESTED XML SITEMAP
                # -----------------------------------

                if url.endswith(".xml"):

                    parse_sitemap(url)

                    continue

                # -----------------------------------
                # VALIDATION
                # -----------------------------------

                if not is_valid_url(url):

                    continue

                # -----------------------------------
                # PRIORITIZE PRODUCT URLS
                # -----------------------------------

                if is_product_url(url):

                    discovered.append(url)

        except Exception as e:

            print(f"Sitemap parse error: {e}")

    # ---------------------------------------
    # START PARSING
    # ---------------------------------------

    for sitemap in sitemap_urls:

        parse_sitemap(sitemap)

    # ---------------------------------------
    # FALLBACK HOMEPAGE CRAWL
    # ---------------------------------------

    if not discovered:

        try:

            print("Fallback homepage crawl")

            response = requests.get(

                base_url,

                headers=HEADERS,

                timeout=20
            )

            soup = BeautifulSoup(

                response.text,

                "html.parser"
            )

            links = soup.find_all("a")

            for link in links:

                href = link.get("href")

                if not href:

                    continue

                # RELATIVE URL

                if href.startswith("/"):

                    href = base_url.rstrip("/") + href

                # INTERNAL ONLY

                if base_url not in href:

                    continue

                # VALIDATION

                if not is_valid_url(href):

                    continue

                # PRODUCT FILTER

                if is_product_url(href):

                    discovered.append(href)

        except Exception as e:

            print(f"Fallback error: {e}")

    # ---------------------------------------
    # REMOVE DUPLICATES
    # ---------------------------------------

    discovered = list(set(discovered))

    # ---------------------------------------
    # LIMIT
    # ---------------------------------------

    discovered = discovered[:max_pages]

    print("FINAL DISCOVERED URLS:")
    print(discovered)

    return discovered