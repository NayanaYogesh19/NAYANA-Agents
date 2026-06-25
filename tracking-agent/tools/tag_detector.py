from bs4 import BeautifulSoup


def detect_tags(html):

    detected_tags = []

    soup = BeautifulSoup(html, "html.parser")

    scripts = soup.find_all("script")

    script_sources = []

    for script in scripts:

        src = script.get("src")

        if src:
            script_sources.append(src.lower())

        # also check inline scripts
        if script.string:
            script_sources.append(script.string.lower())

    combined_content = " ".join(script_sources)

    # Google Tag Manager
    if "googletagmanager.com" in combined_content:
        detected_tags.append("Google Tag Manager")

    # Google Analytics
    if "google-analytics.com" in combined_content or "gtag(" in combined_content:
        detected_tags.append("Google Analytics")

    # Meta Pixel
    if "connect.facebook.net" in combined_content or "fbq(" in combined_content:
        detected_tags.append("Meta Pixel")

    # LinkedIn Insight Tag
    if "snap.licdn.com" in combined_content:
        detected_tags.append("LinkedIn Insight Tag")

    # TikTok Pixel
    if "analytics.tiktok.com" in combined_content:
        detected_tags.append("TikTok Pixel")

    return detected_tags