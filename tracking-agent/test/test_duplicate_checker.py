from tools.browser_tool import open_website

from tools.network_monitor import (
    handle_request,
    get_tracked_requests
)

from tools.duplicate_checker import check_duplicates


print("\nOpening Website...\n")

# Open Website
data = open_website("https://www.shopify.com")

page = data["page"]

# Attach Network Listener
page.on("request", handle_request)

print("Monitoring Tracking Requests...\n")

# Reload page to capture requests
page.reload()

# Wait for tracking scripts to fire
page.wait_for_timeout(8000)

# Get tracked requests
requests = get_tracked_requests()

print("\nCaptured Requests:\n")

if requests:

    for req in requests:
        print(req)

else:
    print("No tracking requests captured")


# Check duplicates
duplicates = check_duplicates(requests)

print("\nDuplicate Tracking Detection:\n")

if duplicates:

    for dup in duplicates:

        print(
            f"{dup['platform']} fired {dup['count']} times"
        )

else:
    print("No duplicates detected")


print("\nClosing Browser...\n")

# Close browser properly
data["browser"].close()

# Stop Playwright
data["playwright"].stop()

print("Test Completed Successfully")