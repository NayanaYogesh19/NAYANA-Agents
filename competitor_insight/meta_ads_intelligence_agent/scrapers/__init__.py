def __init__(self):

                print("APIFY GOOGLE SCRAPER LOADED")

                print(os.getenv("APIFY_TOKEN"))

                self.client = ApifyClient(
                    os.getenv("APIFY_TOKEN")
            )