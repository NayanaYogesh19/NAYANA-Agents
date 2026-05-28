from fastapi import FastAPI
from ga4.routes import router as ga4_router

app = FastAPI(title="GA4 Analytics Agent")

app.include_router(
    ga4_router,
    prefix="/ga4",
    tags=["GA4"]
)

@app.get("/")
async def root():
    return {"status": "running"}