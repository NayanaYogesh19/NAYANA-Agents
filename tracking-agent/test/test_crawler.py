from tools.browser_tool import (
    open_website
)

from tools.crawler import (
    crawl_website
)


print("\nOpening Website...\n")

data = open_website(
    "https://jandhyalafoods.in/"
)

page = data["page"]

# Run crawler
pages = crawl_website(
    page,
    "https://jandhyalafoods.in/"
)

print("\nCrawled Pages:\n")

for url in pages:

    print(f"✔ {url}")

# Close browser
#data["browser"].close()

#data["playwright"].stop()

print("\nTest Completed")