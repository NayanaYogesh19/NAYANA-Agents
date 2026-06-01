from tools.browser_tool import open_website

from tools.network_monitor import (
    handle_request,
    get_tracked_requests
)

from tools.event_validator import (
    extract_events
)


print("\nOpening Website...\n")

data = open_website(
    "https://www.shopify.com"
)

page = data["page"]

# Attach request listener
page.on("request", handle_request)

print("Monitoring Events...\n")

# Reload page
page.reload()

# Wait for tracking events
page.wait_for_timeout(8000)

# Get requests
requests = get_tracked_requests()

# Extract events
events = extract_events(requests)

print("\nDetected Events:\n")

if events:

    for event in events:

        print(f"✔ {event}")

else:

    print("No events detected")


# Close browser
data["browser"].close()

data["playwright"].stop()

print("\nTest Completed")