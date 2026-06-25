
import requests
import urllib3

from bs4 import BeautifulSoup

# =========================================
# DISABLE SSL WARNINGS
# =========================================

urllib3.disable_warnings()

# =========================================
# HEADERS
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
# PARSE SITEMAP
# =========================================

def parse_sitemap(sitemap_url):

    urls = []

    try:

        response = requests.get(

            sitemap_url,

            timeout=30,

            headers=HEADERS,

            verify=False
        )

        if response.status_code != 200:

            print(
                "FAILED SITEMAP:",
                sitemap_url,
                response.status_code
            )

            return []

        soup = BeautifulSoup(

            response.text,

            "xml"
        )

        # =====================================
        # NESTED SITEMAPS
        # =====================================

        sitemap_tags = soup.find_all(
            "sitemap"
        )

        if sitemap_tags:

            for sitemap in sitemap_tags:

                loc = sitemap.find("loc")

                if loc:

                    child_urls = parse_sitemap(
                        loc.text.strip()
                    )

                    urls.extend(
                        child_urls
                    )

            return list(set(urls))

        # =====================================
        # NORMAL URLS
        # =====================================

        url_tags = soup.find_all("url")

        for url_tag in url_tags:

            loc = url_tag.find("loc")

            if loc:

                url = loc.text.strip()

                urls.append(url)

        return list(set(urls))

    except Exception as e:

        print(
            "SITEMAP PARSER ERROR:",
            e
        )

        return []

