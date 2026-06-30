from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from ga4.routes import router as ga4_router
from gsc.routes import router as gsc_router
from fastapi.middleware.cors import CORSMiddleware
import os

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

app.include_router(
    gsc_router,
    prefix="/gsc",
    tags=["Google Search Console"]
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join("frontend", "index.html"))