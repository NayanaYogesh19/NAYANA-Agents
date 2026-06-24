from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.upload      import router as upload_router
from api.analyze     import router as analyze_router
from api.review      import router as review_router
from api.ai_analyze  import router as ai_analyze_router
from api.report      import router as report_router
from api.notice      import router as notice_router
from api.board       import router as board_router
from api.commentary  import router as commentary_router
from api.knowledge   import router as knowledge_router
from api.full_report import router as full_report_router

app = FastAPI(
    title="InGovern Governance Agent",
    version="3.0",
    description=(
        "AI-powered proxy advisory agent for AGM, EGM, and Postal Ballot notices. "
        "Produces InGovern-style governance commentary with RAG, Supabase pgvector, "
        "writing-style learning, policy review, and downloadable PDF reports."
    ),
)

# ── Serve frontend static files ───────────────────────────────────────────────
import os
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Existing routers (unchanged) ─────────────────────────────────────────────
app.include_router(upload_router)
app.include_router(analyze_router)
app.include_router(review_router)
app.include_router(ai_analyze_router)
app.include_router(report_router)

# ── New phase routers ─────────────────────────────────────────────────────────
app.include_router(notice_router)          # /notice/*
app.include_router(board_router)           # /board/*
app.include_router(commentary_router)      # /generate_commentary
app.include_router(knowledge_router)       # /knowledge/*
app.include_router(full_report_router)     # /full_report/*


@app.get("/api/workflow")
def workflow():
    return {
        "status":  "running",
        "agent":   "InGovern Governance Agent",
        "version": "3.0",
        "workflow": {
            "1_upload":          "POST /upload_notice",
            "2_metadata":        "GET  /notice/metadata",
            "3_board":           "GET  /board/full",
            "4_resolutions":     "GET  /extract_resolutions",
            "5_commentary":      "GET  /generate_commentary",
            "6_ai_analysis":     "GET  /analyze_governance  (optional deeper AI)",
            "7_review":          "GET  /review_report",
            "8_approve":         "POST /approve_report",
            "9_report":          "GET  /full_report/generate",
            "10_download":       "GET  /full_report/download",
            "11_search_history": "GET  /knowledge/search_history",
            "12_policy_review":  "GET  /knowledge/policy_review",
            "13_kb_stats":       "GET  /knowledge/stats",
        },
    }


# ── Historical search (legacy + new RAG) ─────────────────────────────────────
from fastapi import Query
from precedent_retrieval.retrieve_precedent import search_precedents


@app.get("/search_history")
def search_history(
    resolution_type: str  = Query(None),
    recommendation:  str  = Query(None),
    director_name:   str  = Query(None),
    ordinary:        bool = Query(None),
    special:         bool = Query(None),
):
    results = search_precedents(
        resolution_type=resolution_type,
        recommendation=recommendation,
        director_name=director_name,
        ordinary=ordinary,
        special=special,
    )
    return {"status": "success", "total": len(results), "results": results}


# ── Frontend serving ──────────────────────────────────────────────────────────
@app.get("/")
def serve_frontend():
    index_path = "static/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "status":  "running",
        "agent":   "InGovern Governance Agent",
        "version": "3.0",
        "docs":    "/docs",
    }
