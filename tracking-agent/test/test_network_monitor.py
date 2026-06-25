from tools.browser_tool import open_website
from tools.network_monitor import (
    handle_request,
    get_tracked_requests
)


data = open_website("https://www.shopify.com")

page = data["page"]

# Attach listener
page.on("request", handle_request)

# Reload page
page.reload()

# Wait for requests
page.wait_for_timeout(8000)

requests = get_tracked_requests()

print("\nTracked Requests:\n")

if requests:

    for req in requests:
        print(req["platform"])

else:
    print("No tracking requests detected")


# Keep browser open briefly
page.wait_for_timeout(5000)

# Close properly
data["browser"].close()
data["playwright"].stop()