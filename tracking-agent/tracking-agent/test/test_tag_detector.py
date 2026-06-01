from tools.browser_tool import open_website
from tools.tag_detector import detect_tags


data = open_website("https://www.shopify.com")

html = data["html"]

tags = detect_tags(html)

print("\nDetected Tags:\n")

if tags:

    for tag in tags:
        print(tag)

else:
    print("No tags detected")