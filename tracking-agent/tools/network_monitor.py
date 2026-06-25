tracked_requests = []


def handle_request(request):

    url = request.url.lower()

    # Google Analytics
    if "google-analytics.com" in url:
        tracked_requests.append({
            "platform": "Google Analytics",
            "url": url
        })

    # Google Tag Manager
    if "googletagmanager.com" in url:
        tracked_requests.append({
            "platform": "Google Tag Manager",
            "url": url
        })

    # Meta Pixel
    if "facebook.com/tr" in url:
        tracked_requests.append({
            "platform": "Meta Pixel",
            "url": url
        })

    # LinkedIn
    if "linkedin" in url or "licdn" in url:
        tracked_requests.append({
            "platform": "LinkedIn Insight Tag",
            "url": url
        })


def get_tracked_requests():

    return tracked_requests
