from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi import UploadFile, File

from scrapers.google_scraper import GoogleAdsScraper
from scrapers.meta_scraper import AdsLibraryBrowser
from scrapers.linkedin_scraper import LinkedInAdsScraper




app = FastAPI()


# ---------------------------------------------------
# GOOGLE REQUEST MODEL
# ---------------------------------------------------

class GoogleAdsRequest(BaseModel):

    url: str

    max_ads: int = 20


# ---------------------------------------------------
# ROOT
# ---------------------------------------------------

@app.get("/")

def home():

    return {
        "message": "Ads Intelligence API Running"
    }


# ---------------------------------------------------
# META ADS
# ---------------------------------------------------

@app.post("/meta-ads")

def scrape_meta_ads(payload: dict):

    try:

        scraper = AdsLibraryBrowser()

        scraper.open(
            payload["url"]
        )

        ads = scraper.collect_ads(
            max_ads=payload.get(
                "max_ads",
                10
            )
        )

        scraper.close()

        return {

            "platform": "Meta",

            "source": "Selenium",

            "total_ads": len(ads),

            "ads": ads
        }

    except Exception as e:

        import traceback

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ---------------------------------------------------
# GOOGLE ADS
# ---------------------------------------------------

@app.post("/google-ads")

def scrape_google_ads(payload: GoogleAdsRequest):

    try:

        scraper = GoogleAdsScraper()

        scraper.open(
            payload.url
        )

        ads = scraper.collect_ads(
            max_ads=payload.max_ads
        )

        scraper.close()

        return {

            "platform": "Google",

            "source": "Apify",

            "total_ads": len(ads),

            "total_active_ads": len(ads),

            "ads": ads
        }

    except Exception as e:

        import traceback

        traceback.print_exc()

        return {
            "status": "error",
            "message": str(e)
        }
    
# ---------------------------------------------------
# LINKEDIN ADS
# ---------------------------------------------------

# ---------------------------------------------------
# LINKEDIN ADS IMAGE
# ---------------------------------------------------

@app.post("/linkedin-ads")

async def scrape_linkedin_ads(

    file: UploadFile = File(...),

    max_ads: int = 20
):

    try:

        image_path = f"temp_{file.filename}"

        with open(image_path, "wb") as f:

            f.write(await file.read())

        scraper = LinkedInAdsScraper()

        scraper.open(
            image_path
        )

        ads = scraper.collect_ads(
            max_ads=max_ads
        )

        scraper.close()

        return {

            "platform": "LinkedIn",

            "source": "OCR + Screenshot",

            "total_ads": len(ads),

            "total_active_ads": len(ads),

            "ads": ads
        }

    except Exception as e:

        import traceback

        traceback.print_exc()

        return {

            "status": "error",

            "message": str(e)
        }