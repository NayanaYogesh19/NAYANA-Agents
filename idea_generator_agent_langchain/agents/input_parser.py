import re
from typing import Dict


def parse_input(
    website_url: str,
    domain: str,
    topic: str,
    lead_magnet: str = "none"
) -> Dict:
    """
    Validates and parses user inputs.
    Raises a descriptive error for invalid/unreachable website URLs.
    """

    website_url = (website_url or "").strip()
    domain      = (domain or "").strip()
    topic       = (topic or "").strip()
    lead_magnet = (lead_magnet or "none").strip()

    # ── Required fields ──
    if not website_url:
        raise Exception("Please provide a website URL.")

    if not domain:
        raise Exception("Please provide a domain / industry.")

    if not topic:
        raise Exception("Please provide a topic.")

    # ── Auto-prefix https:// ──
    if not website_url.startswith(("http://", "https://")):
        website_url = "https://" + website_url

    # ── Basic URL format check ──
    url_pattern = re.compile(
        r"^https?://"
        r"([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)"
        r"+[a-zA-Z]{2,}"
        r"(/[^\s]*)?$"
    )
    if not url_pattern.match(website_url):
        raise Exception(
            f"Invalid website URL: '{website_url}'. "
            "Please enter a valid URL like https://yourwebsite.com"
        )

    # ── Reachability check ──
    try:
        import requests
        from requests.exceptions import SSLError, ConnectionError, Timeout

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

        try:
            resp = requests.head(website_url, timeout=10, headers=headers, verify=True, allow_redirects=True)
        except SSLError:
            resp = requests.head(website_url, timeout=10, headers=headers, verify=False, allow_redirects=True)

        if resp.status_code >= 400:
            raise Exception(
                f"Website returned error {resp.status_code}: '{website_url}' does not appear to be a valid or live website. "
                "Please check the URL and try again."
            )

    except ConnectionError:
        raise Exception(
            f"Cannot reach '{website_url}'. The website does not exist or is currently offline. "
            "Please check the URL and try again."
        )
    except Timeout:
        raise Exception(
            f"Website '{website_url}' took too long to respond (timeout). "
            "Please check if the site is online and try again."
        )
    except Exception as e:
        # re-raise our own exceptions as-is
        if "does not appear" in str(e) or "Cannot reach" in str(e) or "too long" in str(e) or "Invalid website" in str(e):
            raise
        raise Exception(
            f"Could not validate website '{website_url}': {str(e)}. "
            "Please enter a correct and reachable website URL."
        )

    return {
        "website_url": website_url,
        "domain": domain,
        "topic": topic,
        "lead_magnet": lead_magnet
    }
