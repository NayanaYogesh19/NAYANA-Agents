import requests


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
}


def fetch_website(website_url: str) -> str:
    """
    Equivalent to the n8n HTTP Request node.
    Fetches HTML from any URL, falling back to SSL-unverified if needed.
    """

    try:
        response = requests.get(
            website_url,
            timeout=30,
            headers=HEADERS,
            verify=True
        )
        response.raise_for_status()
        return response.text

    except requests.exceptions.SSLError:
        # Retry without SSL verification for sites with cert issues
        response = requests.get(
            website_url,
            timeout=30,
            headers=HEADERS,
            verify=False
        )
        response.raise_for_status()
        return response.text

    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch website: {str(e)}")