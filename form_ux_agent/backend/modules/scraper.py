"""
scraper.py
Scrapes a public URL and extracts all form elements, fields,
labels, placeholders, error messages, CTA text and CSS theme colours.
Uses requests + BeautifulSoup (fast) with Playwright fallback for JS-rendered pages.
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "aol.com", "live.com", "msn.com",
}


def scrape_url(url: str) -> dict:
    """
    Main entry point. Returns a structured dict with:
      - page_title
      - forms: list of form dicts
      - css_theme: dict with dominant colours
      - raw_html snippet for AI context
    """
    url_clean = url.split("?")[0].split("#")[0]

    html = None
    error_msg = None
    try:
        resp = requests.get(url_clean, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        error_msg = str(e)

    # If requests failed or found no forms, try Playwright for JS-rendered pages
    if html:
        soup = BeautifulSoup(html, "html.parser")
        forms = _extract_forms(soup, url_clean)
        # If no forms found via requests, try Playwright fallback
        if not forms:
            js_html = _playwright_fetch(url_clean)
            if js_html:
                html = js_html
                soup = BeautifulSoup(html, "html.parser")
                forms = _extract_forms(soup, url_clean)
    else:
        js_html = _playwright_fetch(url_clean)
        if not js_html:
            return {"error": error_msg, "forms": [], "page_title": "", "css_theme": {}}
        html = js_html
        soup = BeautifulSoup(html, "html.parser")
        forms = _extract_forms(soup, url_clean)

    page_title = soup.title.string.strip() if soup.title else ""
    css_theme = _extract_css_theme(soup, url_clean)

    return {
        "page_title": page_title,
        "url": url_clean,
        "forms": forms,
        "css_theme": css_theme,
        "form_count": len(forms),
        "raw_snippet": html[:3000],
    }


def _playwright_fetch(url: str) -> str | None:
    """Playwright fallback for JS-rendered pages."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=20000)
            page.wait_for_load_state("networkidle", timeout=15000)
            content = page.content()
            browser.close()
            return content
    except Exception:
        return None


def _extract_forms(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """
    Extract every <form> on the page with full field details.
    Also detects non-standard form containers (divs with inputs) that
    many modern JS frameworks render without a <form> tag.
    """
    forms = []
    seen_field_sigs = set()

    def _add_form(container, index, action="", method="GET"):
        fields = _extract_fields(container)
        # Skip empty containers and pure search boxes (single text field, no label)
        if not fields:
            return
        if len(fields) == 1 and fields[0].get("type") in ("search", "text") and not fields[0].get("label"):
            return
        # Deduplicate by field signature
        sig = tuple(f.get("name", f.get("placeholder", "")) for f in fields[:4])
        if sig in seen_field_sigs:
            return
        seen_field_sigs.add(sig)

        cta = _extract_cta(container)
        error_messages = _extract_error_messages(container)
        has_progress = bool(container.find(class_=re.compile(r"progress|step", re.I)))
        has_gdpr = _detect_gdpr(container)
        has_trust_signals = _detect_trust_signals(container, soup)

        forms.append({
            "form_index": index,
            "action": action,
            "method": method,
            "field_count": len(fields),
            "fields": fields,
            "cta": cta,
            "error_messages": error_messages,
            "has_progress_indicator": has_progress,
            "has_gdpr_consent": has_gdpr,
            "has_trust_signals": has_trust_signals,
        })

    # ── Pass 1: Standard <form> tags ──────────────────────────
    for i, form in enumerate(soup.find_all("form")):
        action = form.get("action", "")
        if action:
            action = urljoin(base_url, action)
        method = form.get("method", "get").upper()
        _add_form(form, i, action, method)

    # ── Pass 2: Non-standard containers (JS framework forms) ──
    # Look for divs/sections that contain multiple inputs but no parent <form>
    CONTAINER_CLASSES = re.compile(
        r"form|contact|enquir|quote|register|signup|sign-up|subscribe|modal|popup|widget|lead|cta-form",
        re.I
    )
    idx = len(forms)
    for container in soup.find_all(["div", "section", "aside"], class_=CONTAINER_CLASSES):
        # Skip if already inside a <form> tag we've processed
        if container.find_parent("form"):
            continue
        # Must have at least one real input
        inputs = container.find_all(["input", "select", "textarea"])
        real_inputs = [i for i in inputs if i.get("type", "text") not in ("hidden", "submit", "button", "reset", "image")]
        if len(real_inputs) < 1:
            continue
        _add_form(container, idx)
        idx += 1

    return forms


def _extract_fields(form: BeautifulSoup) -> list[dict]:
    """Extract all input fields with their labels and attributes."""
    fields = []
    for inp in form.find_all(["input", "select", "textarea"]):
        input_type = inp.get("type", "text").lower()
        if input_type in ("submit", "button", "hidden", "reset", "image"):
            continue

        name = inp.get("name", inp.get("id", "unnamed"))
        placeholder = inp.get("placeholder", "")
        required = inp.has_attr("required") or inp.get("aria-required") == "true"
        autocomplete = inp.get("autocomplete", "")

        # Find associated label
        label_text = ""
        input_id = inp.get("id")
        if input_id:
            label_tag = form.find("label", {"for": input_id})
            if label_tag:
                label_text = label_tag.get_text(strip=True)

        if not label_text:
            parent = inp.parent
            label_tag = parent.find("label") if parent else None
            if label_tag:
                label_text = label_tag.get_text(strip=True)

        fields.append({
            "name": name,
            "type": input_type,
            "label": label_text,
            "placeholder": placeholder,
            "required": required,
            "autocomplete": autocomplete,
            "has_label": bool(label_text),
            "label_only_placeholder": not bool(label_text) and bool(placeholder),
        })
    return fields


def _extract_cta(form: BeautifulSoup) -> dict:
    """Find and analyse the submit button / CTA."""
    btn = form.find("button", {"type": "submit"})
    if not btn:
        btn = form.find("input", {"type": "submit"})
    if not btn:
        btn = form.find("button")

    if btn:
        text = btn.get_text(strip=True) or btn.get("value", "")
        weak_ctas = {"submit", "send", "go", "ok", "next", "continue"}
        is_weak = text.lower() in weak_ctas
        return {"text": text, "is_weak_cta": is_weak}
    return {"text": "", "is_weak_cta": True}


def _extract_error_messages(form: BeautifulSoup) -> list[str]:
    """Find inline error message containers."""
    msgs = []
    for el in form.find_all(class_=re.compile(r"error|invalid|alert|warn", re.I)):
        t = el.get_text(strip=True)
        if t:
            msgs.append(t)
    return msgs


def _detect_gdpr(form: BeautifulSoup) -> bool:
    text = form.get_text().lower()
    return any(kw in text for kw in ["gdpr", "privacy policy", "consent", "data protection", "opt-in"])


def _detect_trust_signals(form: BeautifulSoup, soup: BeautifulSoup) -> bool:
    """Look for trust signals near the form (SSL badge, testimonials, security icons)."""
    area = str(form) + str(soup.find("body") or "")
    keywords = ["secure", "ssl", "trusted", "verified", "no spam", "money back", "guarantee"]
    return any(kw in area.lower() for kw in keywords)


def crawl_site_for_forms(base_url: str, max_pages: int = 30) -> list:
    """
    Crawl a website and return a summary of every form found across all pages.
    Prioritises contact/quote/enquiry/booking pages. Returns list of form dicts.
    """
    parsed = urlparse(base_url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    base_url_clean = base_url.split("?")[0].rstrip("/")

    visited = set()
    form_summaries = []

    # Keywords that strongly suggest a page has a form
    PRIORITY_KEYWORDS = [
        "contact", "quote", "enquir", "enquiry", "book", "demo",
        "apply", "register", "sign-up", "signup", "get-in-touch",
        "touch", "request", "trial", "consult", "support", "help",
        "callback", "call-back", "free-trial", "free-quote",
        "appointment", "schedule", "form", "lead", "subscribe",
        "membership", "join", "feedback", "survey", "partner",
        "career", "job", "hire", "pricing", "getstarted", "start",
    ]

    def _score_url(url: str) -> int:
        """Higher score = check this page first."""
        url_lower = url.lower()
        return sum(2 for kw in PRIORITY_KEYWORDS if kw in url_lower)

    def _get_internal_links(soup: BeautifulSoup, current_url: str) -> list:
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            full = urljoin(current_url, href).split("?")[0].split("#")[0].rstrip("/")
            if full.startswith(domain) and full not in visited:
                links.append(full)
        return list(dict.fromkeys(links))  # deduplicate, preserve order

    def _summarise_forms(forms: list, page_url: str, page_title: str) -> list:
        summaries = []
        for i, form in enumerate(forms):
            fields = form.get("fields", [])
            if not fields:
                continue
            # Skip single-field search-only forms
            if len(fields) == 1 and fields[0].get("type") in ("search", "text") and not fields[0].get("label"):
                continue
            labels = [
                f.get("label") or f.get("placeholder") or f.get("name") or f"Field {j+1}"
                for j, f in enumerate(fields)
            ]
            cta_text = form.get("cta", {}).get("text", "")
            # Derive a friendly page-based name
            path = urlparse(page_url).path.strip("/").split("/")[-1].replace("-", " ").replace("_", " ").title()
            form_name = path or page_title or f"Form {i+1}"
            summaries.append({
                "form_index": i,
                "form_name": form_name,
                "field_count": len(fields),
                "field_labels": labels,
                "cta_text": cta_text,
                "page_url": page_url,
                "page_title": page_title,
                "has_gdpr": form.get("has_gdpr_consent", False),
                "has_trust": form.get("has_trust_signals", False),
            })
        return summaries

    def _fetch_and_extract(url: str):
        """Fetch a page, return (soup, forms, page_title) or None on error."""
        html = None
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            resp.raise_for_status()
            html = resp.text
        except Exception:
            pass

        if html:
            soup = BeautifulSoup(html, "html.parser")
            forms = _extract_forms(soup, url)
            # Try Playwright if no forms found (JS-rendered page)
            if not forms:
                js_html = _playwright_fetch(url)
                if js_html:
                    soup = BeautifulSoup(js_html, "html.parser")
                    forms = _extract_forms(soup, url)
        else:
            js_html = _playwright_fetch(url)
            if not js_html:
                return None
            soup = BeautifulSoup(js_html, "html.parser")
            forms = _extract_forms(soup, url)

        title = soup.title.string.strip() if soup.title else ""
        return soup, forms, title

    # ── Phase 1: Scrape the starting URL ──────────────────────
    result = _fetch_and_extract(base_url_clean)
    if not result:
        raise ValueError(f"Could not load {base_url_clean}")

    soup, forms, page_title = result
    visited.add(base_url_clean)
    form_summaries.extend(_summarise_forms(forms, base_url_clean, page_title))

    # Collect all internal links found on the homepage
    all_links = _get_internal_links(soup, base_url_clean)

    # ── Phase 2: Prioritised crawl of internal pages ──────────
    # Sort: priority (contact/quote) pages first, then rest
    priority = sorted([l for l in all_links if _score_url(l) > 0], key=_score_url, reverse=True)
    rest = [l for l in all_links if _score_url(l) == 0]
    queue = priority + rest

    pages_checked = 1
    for url in queue:
        if pages_checked >= max_pages:
            break
        if url in visited:
            continue
        visited.add(url)
        pages_checked += 1

        result = _fetch_and_extract(url)
        if not result:
            continue
        page_soup, page_forms, ptitle = result
        summaries = _summarise_forms(page_forms, url, ptitle)
        form_summaries.extend(summaries)

        # Collect more links from this page too (one level deep)
        if pages_checked < max_pages:
            new_links = _get_internal_links(page_soup, url)
            for nl in new_links:
                if nl not in visited and nl not in queue:
                    if _score_url(nl) > 0:
                        queue.insert(0, nl)  # priority pages go to front
                    else:
                        queue.append(nl)

    # Deduplicate: same field count + same first 3 labels = same form
    seen_signatures = set()
    unique = []
    for f in form_summaries:
        sig = (f["field_count"], tuple(f["field_labels"][:3]))
        if sig not in seen_signatures:
            seen_signatures.add(sig)
            unique.append(f)

    return unique


def _extract_css_theme(soup: BeautifulSoup, url: str) -> dict:
    """Extract dominant colours from inline styles for brand consistency check."""
    colours = []
    for tag in soup.find_all(style=True):
        found = re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})", tag["style"])
        colours.extend(found)
    # Also check <style> blocks
    for style_tag in soup.find_all("style"):
        found = re.findall(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})", style_tag.string or "")
        colours.extend(found)

    # Return top 5 most common
    from collections import Counter
    top = Counter(colours).most_common(5)
    return {
        "dominant_colours": [f"#{c}" for c, _ in top],
        "has_brand_colours": len(top) > 0,
    }
