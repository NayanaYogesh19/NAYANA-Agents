import re
from bs4 import BeautifulSoup


def extract_html_content(html: str) -> dict:
    """
    Extracts rich, structured content from the website HTML so the AI
    gets enough specific context to generate non-generic ideas.
    """

    soup = BeautifulSoup(html, "lxml")

    # Remove script/style noise
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    # ── Headings (h1–h4) ──
    headings = []
    for tag in soup.select("h1, h2, h3, h4"):
        t = tag.get_text(separator=" ", strip=True)
        if t and len(t) > 3:
            headings.append(t)
    headings_text = " | ".join(headings[:30])

    # ── Meta tags ──
    meta_description = ""
    meta_tag = soup.select_one('meta[name="description"]')
    if meta_tag:
        meta_description = meta_tag.get("content", "").strip()

    meta_keywords = ""
    mk = soup.select_one('meta[name="keywords"]')
    if mk:
        meta_keywords = mk.get("content", "").strip()

    og_title = ""
    og = soup.select_one('meta[property="og:title"]')
    if og:
        og_title = og.get("content", "").strip()

    og_desc = ""
    ogd = soup.select_one('meta[property="og:description"]')
    if ogd:
        og_desc = ogd.get("content", "").strip()

    # ── Page title ──
    page_title = ""
    title_tag = soup.select_one("title")
    if title_tag:
        page_title = title_tag.get_text(strip=True)

    # ── Navigation links (reveal site sections/services) ──
    nav_items = []
    for nav in soup.select("nav a, header a, .nav a, .menu a, .navbar a"):
        t = nav.get_text(strip=True)
        if t and len(t) > 2 and t not in nav_items:
            nav_items.append(t)
    nav_text = ", ".join(nav_items[:20])

    # ── Paragraphs (meaningful ones only, min 40 chars) ──
    paragraphs = []
    for tag in soup.select("p"):
        t = tag.get_text(separator=" ", strip=True)
        if t and len(t) >= 40:
            paragraphs.append(t)
    body_text = " ".join(paragraphs[:40])

    # ── Lists — often contain services, features, USPs ──
    list_items = []
    for tag in soup.select("li"):
        t = tag.get_text(separator=" ", strip=True)
        if t and len(t) > 5 and len(t) < 200:
            list_items.append(t)
    list_text = " | ".join(list_items[:30])

    # ── Button & CTA text — reveals offers and actions ──
    ctas = []
    for tag in soup.select("button, a.btn, a.button, .cta, [class*='cta'], [class*='btn']"):
        t = tag.get_text(strip=True)
        if t and len(t) > 2 and len(t) < 80 and t not in ctas:
            ctas.append(t)
    cta_text = ", ".join(ctas[:15])

    # ── Section headings with nearby text (service blocks) ──
    sections = []
    for tag in soup.select("section, .section, article, .service, .feature, .card, .block"):
        heading = tag.find(re.compile(r"^h[1-4]$"))
        if heading:
            h = heading.get_text(strip=True)
            # grab first paragraph near it
            p = tag.find("p")
            desc = p.get_text(separator=" ", strip=True)[:150] if p else ""
            if h:
                sections.append(f"{h}: {desc}" if desc else h)
    section_text = " | ".join(sections[:20])

    return {
        "headings": headings_text,
        "meta_description": meta_description,
        "meta_keywords": meta_keywords,
        "og_title": og_title,
        "og_description": og_desc,
        "page_title": page_title,
        "nav_items": nav_text,
        "body_text": body_text[:3000],
        "list_items": list_text,
        "cta_text": cta_text,
        "section_summaries": section_text
    }
