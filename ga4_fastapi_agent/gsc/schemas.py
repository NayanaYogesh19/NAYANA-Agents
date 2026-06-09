from pydantic import BaseModel

class PerformanceRequest(BaseModel):
    site_url: str
    start_date: str
    end_date: str
    row_limit: int = 100



class SitemapRequest(BaseModel):
    site_url: str


class URLRequest(BaseModel):
    url: str

    