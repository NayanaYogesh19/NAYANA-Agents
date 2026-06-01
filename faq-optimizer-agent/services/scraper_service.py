import requests
import re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def extract_website_content(url: str) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code != 200:
            return f"Error: Unable to fetch website ({response.status_code})"

        soup = BeautifulSoup(response.text, "html.parser")

        # Title
        title = soup.title.string.strip() if soup.title else ""

        # Meta description
        meta = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta["content"].strip() if meta and meta.get("content") else ""

        # Headings
        headings = []
        for tag in soup.find_all(["h1", "h2", "h3"]):
            text = tag.get_text(strip=True)
            if text:
                headings.append(text)

        # Remove junk
        for tag in soup(["script", "style", "noscript", "nav", "footer"]):
            tag.decompose()

        body = soup.get_text(separator=" ")
        body = re.sub(r"\s+", " ", body).strip()

        if len(body) > 8000:
            body = body[:8000]

        return f"""
TITLE: {title}

META: {meta_desc}

HEADINGS:
{' | '.join(headings[:20])}

CONTENT:
{body}
"""

    except Exception as e:
        return f"Error: {str(e)}"