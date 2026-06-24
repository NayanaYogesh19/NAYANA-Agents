"""
RAG store using Supabase + pgvector.

Tables required (run once in Supabase SQL Editor):

  -- Enable pgvector
  create extension if not exists vector;

  -- Historical resolutions with embeddings
  create table if not exists rag_resolutions (
      id              uuid primary key default gen_random_uuid(),
      company_name    text,
      financial_year  text,
      notice_type     text,           -- AGM / EGM / Postal Ballot
      industry        text,
      resolution_type text,
      resolution_title text,
      resolution_text text,
      management_rec  text,
      ingovern_rec    text,
      commentary_json jsonb,
      embedding       vector(1536),   -- text-embedding-ada-002 / any 1536-dim model
      created_at      timestamptz default now()
  );

  create index if not exists rag_resolutions_embedding_idx
      on rag_resolutions using ivfflat (embedding vector_cosine_ops)
      with (lists = 100);

  -- Writing style examples
  create table if not exists writing_style_examples (
      id              uuid primary key default gen_random_uuid(),
      resolution_type text,
      ingovern_rec    text,
      example_text    text,           -- the model commentary to imitate
      embedding       vector(1536),
      created_at      timestamptz default now()
  );
"""

import json
import requests

from config.config import OPENROUTER_API_KEY, SUPABASE_URL, SUPABASE_KEY
from database.supabase_client import get_client, get_write_client


# ── Embedding helper ──────────────────────────────────────────────────────────

def _get_embedding(text: str) -> list[float] | None:
    """
    Get a 1536-dim embedding via OpenRouter (uses text-embedding-ada-002 compat).
    Returns None on any failure so callers degrade gracefully.
    """
    if not OPENROUTER_API_KEY:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type":  "application/json",
        }
        payload = {
            "model": "openai/text-embedding-ada-002",
            "input": text[:8000],
        }
        r = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if r.status_code == 200:
            return r.json()["data"][0]["embedding"]
    except Exception:
        pass
    return None


# ── Store a resolution in RAG ─────────────────────────────────────────────────

def store_resolution_rag(
    company_name:     str,
    financial_year:   str,
    notice_type:      str,
    industry:         str,
    resolution:       dict,
    commentary:       dict,
) -> bool:
    """
    Embed + store a resolution + its commentary in rag_resolutions.
    Returns True on success.
    """
    client = get_write_client()
    if client is None:
        return False

    text_to_embed = (
        f"{resolution.get('resolution_type','')} "
        f"{resolution.get('title','')} "
        f"{resolution.get('resolution_text','')[:2000]}"
    )
    embedding = _get_embedding(text_to_embed)

    row = {
        "company_name":     company_name,
        "financial_year":   financial_year,
        "notice_type":      notice_type,
        "industry":         industry,
        "resolution_type":  resolution.get("resolution_type", ""),
        "resolution_title": resolution.get("title", ""),
        "resolution_text":  resolution.get("resolution_text", "")[:6000],
        "management_rec":   commentary.get("management_recommendation", "FOR"),
        "ingovern_rec":     commentary.get("ingovern_recommendation", "FOR"),
        "commentary_json":  json.dumps(commentary),
    }
    if embedding:
        row["embedding"] = embedding

    try:
        # Deduplication: skip if same company + year + title already stored
        existing = (
            client.table("rag_resolutions")
            .select("id")
            .eq("company_name",     company_name)
            .eq("financial_year",   financial_year)
            .eq("resolution_title", resolution.get("title", ""))
            .limit(1)
            .execute()
        )
        if existing.data:
            return True  # already exists, skip

        client.table("rag_resolutions").insert(row).execute()
        return True
    except Exception:
        return False


# ── Semantic search ───────────────────────────────────────────────────────────

def search_similar_resolutions(
    query_text:      str,
    resolution_type: str = None,
    notice_type:     str = None,
    industry:        str = None,
    limit:           int = 5,
) -> list[dict]:
    """
    Semantic search over stored resolutions using pgvector cosine similarity.
    Falls back to keyword search if embedding is unavailable.
    """
    client = get_client()
    if client is None:
        return []

    embedding = _get_embedding(query_text)

    try:
        if embedding:
            # pgvector RPC — requires a Supabase SQL function (see below)
            params = {
                "query_embedding": embedding,
                "match_count":     limit,
            }
            if resolution_type:
                params["filter_resolution_type"] = resolution_type
            if notice_type:
                params["filter_notice_type"] = notice_type
            if industry:
                params["filter_industry"] = industry

            resp = client.rpc("match_rag_resolutions", params).execute()
            rows = resp.data or []
        else:
            # Keyword fallback
            q = client.table("rag_resolutions").select("*").limit(limit)
            if resolution_type:
                q = q.eq("resolution_type", resolution_type)
            if notice_type:
                q = q.eq("notice_type", notice_type)
            resp = q.execute()
            rows = resp.data or []

        return [
            {
                "company_name":     r.get("company_name"),
                "financial_year":   r.get("financial_year"),
                "notice_type":      r.get("notice_type"),
                "industry":         r.get("industry"),
                "resolution_type":  r.get("resolution_type"),
                "resolution_title": r.get("resolution_title"),
                "management_rec":   r.get("management_rec"),
                "ingovern_rec":     r.get("ingovern_rec"),
                "commentary_json":  r.get("commentary_json"),
                "similarity":       r.get("similarity"),
            }
            for r in rows
        ]

    except Exception:
        return []


# ── Writing style store/retrieve ──────────────────────────────────────────────

def store_style_example(
    resolution_type: str,
    ingovern_rec:    str,
    example_text:    str,
) -> bool:
    client = get_write_client()
    if client is None:
        return False
    embedding = _get_embedding(example_text[:4000])
    row = {
        "resolution_type": resolution_type,
        "ingovern_rec":    ingovern_rec,
        "example_text":    example_text[:8000],
    }
    if embedding:
        row["embedding"] = embedding
    try:
        client.table("writing_style_examples").insert(row).execute()
        return True
    except Exception:
        return False


def retrieve_style_examples(
    resolution_type: str,
    ingovern_rec:    str = None,
    limit:           int = 3,
) -> list[str]:
    """Return example commentary texts for the given resolution type."""
    client = get_client()
    if client is None:
        return []
    try:
        q = (
            client.table("writing_style_examples")
            .select("example_text")
            .eq("resolution_type", resolution_type)
            .limit(limit)
        )
        if ingovern_rec:
            q = q.eq("ingovern_rec", ingovern_rec)
        resp = q.execute()
        return [r["example_text"] for r in (resp.data or [])]
    except Exception:
        return []
