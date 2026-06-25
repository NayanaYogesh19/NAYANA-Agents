
import requests
import urllib3

# =========================================
# DISABLE SSL WARNINGS
# =========================================

urllib3.disable_warnings()

# =========================================
# COMMON SITEMAPS
# =========================================

COMMON_SITEMAPS = [

    "/sitemap.xml",

    "/sitemap_index.xml",

    "/sitemap-index.xml"
]

# =========================================
# BROWSER HEADERS
# =========================================

HEADERS = {

    "User-Agent": (

        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),

    "Accept":
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",

    "Accept-Language":
    "en-US,en;q=0.5",

    "Connection":
    "keep-alive"
}

# =========================================
# DISCOVER SITEMAP
# =========================================

def discover_sitemap(base_url):

    base_url = base_url.rstrip("/")

    for sitemap in COMMON_SITEMAPS:

        sitemap_url = base_url + sitemap

        try:

            response = requests.get(

                sitemap_url,

                timeout=30,

                headers=HEADERS,

                verify=False
            )

            if response.status_code == 200:

                print(
                    "Sitemap Found:",
                    sitemap_url
                )

                return sitemap_url

            else:

                print(
                    "Sitemap Not Found:",
                    sitemap_url,
                    response.status_code
                )

        except Exception as e:

            print(
                "Sitemap Error:",
                e
            )

    return None

