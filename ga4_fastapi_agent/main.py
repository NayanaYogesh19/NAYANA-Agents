from fastapi import FastAPI
from ga4.routes import router as ga4_router
from gsc.routes import router as gsc_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="GA4 Analytics Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    ga4_router,
    prefix="/ga4",
    tags=["GA4"]
)

@app.get("/")
async def root():
    return {"status": "running"}

app.include_router(
    gsc_router,
    prefix="/gsc",
    tags=["Google Search Console"]
)