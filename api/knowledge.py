"""
Steps 7, 8, 9, 11 — Knowledge base endpoints:
  GET  /knowledge/search_history   — RAG semantic search (Step 7)
  POST /knowledge/add_style        — Store writing style example (Step 8)
  GET  /knowledge/style_examples   — Retrieve style examples (Step 8)
  GET  /knowledge/policy_review    — Policy guidelines review (Step 9)
  GET  /knowledge/stats            — Knowledge base stats (Step 11)
"""

import os
import json

from fastapi import APIRouter, Query, Body

from database.rag_store import (
    search_similar_resolutions,
    store_style_example,
    retrieve_style_examples,
)
from database.supabase_client import get_client
from policy_retrieval.policies import POLICIES

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


# ── Step 7: RAG historical search ─────────────────────────────────────────────

@router.get("/search_history")
async def rag_search_history(
    query:           str  = Query(..., description="Free-text query, e.g. 'director reappointment ESOP dilution'"),
    resolution_type: str  = Query(None, description="Director Appointment / RPT / ESOP / Remuneration / Auditor / Borrowing / ..."),
    notice_type:     str  = Query(None, description="AGM / EGM / Postal Ballot"),
    industry:        str  = Query(None, description="Technology / FMCG / Banking / ..."),
    limit:           int  = Query(5,    description="Max results to return"),
):
    """
    Semantic search over historical resolutions using pgvector similarity.
    Falls back to keyword filter when embeddings are unavailable.
    """
    results = search_similar_resolutions(
        query_text      = query,
        resolution_type = resolution_type,
        notice_type     = notice_type,
        industry        = industry,
        limit           = limit,
    )
    return {
        "status":  "success",
        "total":   len(results),
        "results": results,
    }


# ── Step 8a: Store writing style example ──────────────────────────────────────

@router.post("/add_style")
async def add_style_example(data: dict = Body(...)):
    """
    Store a writing style example in Supabase so the AI can learn from it.

    Body:
    {
      "resolution_type": "Director Appointment",
      "ingovern_rec":    "FOR",
      "example_text":    "<full InGovern commentary text to learn from>"
    }
    """
    resolution_type = data.get("resolution_type", "")
    ingovern_rec    = data.get("ingovern_rec", "")
    example_text    = data.get("example_text", "")

    if not resolution_type or not example_text:
        return {"status": "error", "message": "resolution_type and example_text are required."}

    ok = store_style_example(resolution_type, ingovern_rec, example_text)
    return {
        "status":  "success" if ok else "warning",
        "stored":  ok,
        "message": "Stored in Supabase." if ok else "Supabase not configured — not stored.",
    }


# ── Step 8b: Retrieve style examples ─────────────────────────────────────────

@router.get("/style_examples")
async def get_style_examples(
    resolution_type: str = Query(..., description="e.g. Director Appointment"),
    ingovern_rec:    str = Query(None, description="FOR / FOR* / AGAINST"),
    limit:           int = Query(3),
):
    """
    Retrieve stored writing style examples for a given resolution type.
    Used internally by the AI to calibrate its commentary style.
    """
    examples = retrieve_style_examples(resolution_type, ingovern_rec, limit)
    return {
        "status":   "success",
        "total":    len(examples),
        "examples": examples,
    }


# ── Step 9: Policy guidelines review ─────────────────────────────────────────

@router.get("/policy_review")
async def policy_guidelines_review(
    resolution_type: str = Query(None, description="Resolution type to review (omit for all)"),
):
    """
    Return applicable policy guidelines and SEBI/Companies Act check-items
    for a resolution type (or all types).
    """
    if resolution_type:
        policy = POLICIES.get(resolution_type)
        if not policy:
            # Try case-insensitive match
            for k, v in POLICIES.items():
                if k.lower() == resolution_type.lower():
                    policy = v
                    break
        if not policy:
            return {
                "status":          "not_found",
                "resolution_type": resolution_type,
                "message":         f"No policy found for '{resolution_type}'. Available: {list(POLICIES.keys())}",
            }
        return {
            "status":          "success",
            "resolution_type": resolution_type,
            "policy":          policy,
        }

    # Return all policies
    return {
        "status":   "success",
        "policies": POLICIES,
        "total":    len(POLICIES),
    }


# ── Step 11: Knowledge base stats / visualization data ───────────────────────

@router.get("/stats")
async def knowledge_base_stats():
    """
    Return counts and breakdowns from the Supabase knowledge base —
    used to power the Knowledge Base visualisation dashboard.
    """
    client = get_client()

    stats = {
        "supabase_connected": client is not None,
        "local_approved":     0,
        "resolution_types":   {},
        "notice_types":       {},
        "recommendation_dist": {"FOR": 0, "FOR*": 0, "AGAINST": 0},
        "companies":          [],
        "rag_total":          0,
        "style_examples":     0,
    }

    # Local approved JSON count
    approved_dir = os.path.join(STORAGE_DIR, "approved")
    if os.path.exists(approved_dir):
        local_files = [f for f in os.listdir(approved_dir) if f.endswith(".json")]
        stats["local_approved"] = len(local_files)
        for fname in local_files:
            try:
                with open(os.path.join(approved_dir, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                stats["companies"].append({
                    "company_name":   data.get("company_name"),
                    "financial_year": data.get("financial_year"),
                    "status":         data.get("status"),
                    "approved_by":    data.get("approved_by"),
                })
                for r in data.get("resolutions", []):
                    rt = r.get("resolution_type", "Other")
                    stats["resolution_types"][rt] = stats["resolution_types"].get(rt, 0) + 1
                    rec = r.get("recommendation", {})
                    if isinstance(rec, dict):
                        rv = rec.get("recommendation", "")
                        if rv in stats["recommendation_dist"]:
                            stats["recommendation_dist"][rv] += 1
            except Exception:
                continue

    # Supabase stats
    if client:
        try:
            r1 = client.table("rag_resolutions").select("id", count="exact").execute()
            stats["rag_total"] = r1.count or 0
        except Exception:
            pass
        try:
            r2 = client.table("writing_style_examples").select("id", count="exact").execute()
            stats["style_examples"] = r2.count or 0
        except Exception:
            pass
        try:
            nt_rows = client.table("rag_resolutions").select("notice_type").execute()
            for row in (nt_rows.data or []):
                nt = row.get("notice_type", "Unknown")
                stats["notice_types"][nt] = stats["notice_types"].get(nt, 0) + 1
        except Exception:
            pass

    return {"status": "success", **stats}
