from tools.browser_tool import open_website

data = open_website("https://example.com")

print("Website Opened Successfully")

print(data["html"][:500])