import requests

from bs4 import BeautifulSoup


HEADERS = {

    "User-Agent": "Mozilla/5.0"
}


async def scrape_page(url):

    try:

        print(f"Scraping: {url}")

        response = requests.get(

            url,

            headers=HEADERS,

            timeout=20
        )

        soup = BeautifulSoup(

            response.text,

            "html.parser"
        )

        # -----------------------------------
        # TITLE
        # -----------------------------------

        title = ""

        if soup.title:

            title = soup.title.text.strip()

        # -----------------------------------
        # META DESCRIPTION
        # -----------------------------------

        meta_description = ""

        meta_tag = soup.find(

            "meta",

            attrs={
                "name": "description"
            }
        )

        if meta_tag:

            meta_description = meta_tag.get(
                "content",
                ""
            ).strip()

        # -----------------------------------
        # H1
        # -----------------------------------

        h1 = ""

        h1_tag = soup.find("h1")

        if h1_tag:

            h1 = h1_tag.get_text(
                strip=True
            )

        # -----------------------------------
        # H2
        # -----------------------------------

        h2_tags = soup.find_all("h2")

        h2_list = [

            tag.get_text(strip=True)

            for tag in h2_tags
        ]

        # -----------------------------------
        # H3-H6
        # -----------------------------------

        heading_tags = soup.find_all(

            ["h3", "h4", "h5", "h6"]
        )

        heading_list = [

            tag.get_text(strip=True)

            for tag in heading_tags
        ]

        # -----------------------------------
        # IMAGES + ALT TAGS
        # -----------------------------------

        images = soup.find_all("img")

        image_alts = []

        for img in images:

            alt = img.get("alt", "").strip()

            if alt:

                image_alts.append(alt)

        # MAIN IMAGE ALT

        main_image_alt = ""

        if image_alts:

            main_image_alt = image_alts[0]

        # OTHER IMAGE ALTS

        other_image_alts = ", ".join(
            image_alts[1:]
        )

        # -----------------------------------
        # INTERNAL LINKS
        # -----------------------------------

        internal_links = []

        anchor_texts = []

        links = soup.find_all("a")

        for link in links:

            href = link.get("href")

            text = link.get_text(strip=True)

            if href and href.startswith("/"):

                internal_links.append(href)

                if text:

                    anchor_texts.append(text)

        # -----------------------------------
        # CANONICAL
        # -----------------------------------

        canonical = ""

        canonical_tag = soup.find(

            "link",

            rel="canonical"
        )

        if canonical_tag:

            canonical = canonical_tag.get(
                "href",
                ""
            )

        # -----------------------------------
        # OG TAGS
        # -----------------------------------

        og_title = ""

        og_description = ""

        og_title_tag = soup.find(

            "meta",

            property="og:title"
        )

        if og_title_tag:

            og_title = og_title_tag.get(
                "content",
                ""
            )

        og_desc_tag = soup.find(

            "meta",

            property="og:description"
        )

        if og_desc_tag:

            og_description = og_desc_tag.get(
                "content",
                ""
            )

        # -----------------------------------
        # SCHEMA
        # -----------------------------------

        schema_tags = soup.find_all(

            "script",

            type="application/ld+json"
        )

        schema_count = len(schema_tags)

        # -----------------------------------
        # CONTENT
        # -----------------------------------

        body_text = soup.get_text(
            separator=" ",
            strip=True
        )

        return {

            "url": url,

            "title": title,

            "title_length": len(title),

            "meta_description": meta_description,

            "meta_description_length": len(
                meta_description
            ),

            "h1": h1,

            "h2": h2_list,

            "h3_h6": heading_list,

            "main_image_alt": main_image_alt,

            "other_image_alts": other_image_alts,

            "anchor_texts": anchor_texts,

            "internal_links": internal_links,

            "canonical": canonical,

            "og_title": og_title,

            "og_description": og_description,

            "schema_count": schema_count,

            "content": body_text
        }

    except Exception as e:

        print(f"Scraping error: {e}")

        return {

            "url": url,

            "title": "",

            "title_length": 0,

            "meta_description": "",

            "meta_description_length": 0,

            "h1": "",

            "h2": [],

            "h3_h6": [],

            "main_image_alt": "",

            "other_image_alts": "",

            "anchor_texts": [],

            "internal_links": [],

            "canonical": "",

            "og_title": "",

            "og_description": "",

            "schema_count": 0,

            "content": ""
        }