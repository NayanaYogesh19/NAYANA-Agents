import os
import json

from fastapi import APIRouter
from fastapi import Body
from config.storage import NOTICES_DIR, REPORTS_DIR, SESSION_PATH, STORAGE_DIR

router = APIRouter()


@router.get("/review_report")
async def review_report():

    session_path = SESSION_PATH

    if not os.path.exists(session_path):
        return {
            "status":  "error",
            "message": "No active session.",
        }

    with open(session_path, "r", encoding="utf-8") as f:
        session = json.load(f)

    return {
        "status":        "success",
        "company_name":  session.get("company_name"),
        "financial_year": session.get("financial_year"),
        "report":        session.get("report",       []),
        "resolutions":   session.get("resolutions",  []),
    }


@router.post("/approve_report")
async def approve_report(
    data: dict = Body(...)
):
    session_path = SESSION_PATH

    if not os.path.exists(session_path):
        return {"status": "error"}

    with open(session_path, "r", encoding="utf-8") as f:
        session = json.load(f)

    session["approved_by"] = data.get("approved_by")
    session["comments"]    = data.get("comments")
    session["status"]      = "approved"

    # Local JSON backup (always)
    folder = os.path.join(STORAGE_DIR, "approved")
    os.makedirs(folder, exist_ok=True)

    filename = (
        session["company_name"]
        + "_"
        + session["financial_year"]
        + "_approved.json"
    )
    filepath = os.path.join(folder, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=4)

    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=4)

    # Supabase sync + KB learning (graceful degradation)
    supabase_synced = False
    supabase_error  = None

    try:
        from database.save_company       import save_company
        from database.save_report        import save_report
        from database.save_resolution    import save_resolution
        from database.rag_store          import store_resolution_rag, store_style_example
        from scripts.seed_knowledge_base import _classify_resolution_type

        company_name   = session["company_name"]
        financial_year = session["financial_year"]

        company_id = save_company(
            company_name   = company_name,
            financial_year = financial_year,
        )

        if company_id:
            report_id = save_report(
                company_id  = company_id,
                status      = "approved",
                approved_by = session.get("approved_by", ""),
                comments    = session.get("comments", ""),
                report_json = session.get("report", []),
            )

            if report_id:
                for r in session.get("resolutions", []):
                    rec_obj  = r.get("recommendation", {})
                    rec_val  = rec_obj.get("recommendation", "") if isinstance(rec_obj, dict) else ""
                    conf_val = rec_obj.get("confidence",    "") if isinstance(rec_obj, dict) else ""

                    save_resolution(
                        report_id         = report_id,
                        resolution_number = r.get("resolution_number", 0),
                        resolution_type   = r.get("resolution_type", ""),
                        recommendation    = rec_val,
                        confidence        = conf_val,
                        governance_json   = {
                            "title":               r.get("title", ""),
                            "ordinary_resolution": r.get("ordinary_resolution", False),
                            "special_resolution":  r.get("special_resolution",  False),
                            "director_name":       r.get("director_name", ""),
                            "board_recommendation":r.get("board_recommendation", ""),
                            "annexures":           r.get("annexures", []),
                            "governance_factors":  r.get("governance_factors", {}),
                            "risk_flags":          r.get("risk_flags", []),
                            "governance_evaluation": r.get("governance_evaluation", {}),
                            "ai_analysis":         r.get("ai_analysis", {}),
                        },
                    )

                    # Feed knowledge base with approved commentary
                    ai = r.get("ai_analysis") or rec_obj or {}
                    if isinstance(ai, dict) and ai.get("ai_powered"):
                        res_type_classified = _classify_resolution_type(r.get("title", ""))
                        ig_rec = ai.get("ingovern_recommendation", rec_val)

                        paras    = ai.get("summary_paragraphs", [])
                        concerns = ai.get("governance_concerns", [])
                        closing  = ai.get("closing_recommendation", "")
                        example_text = "\n\n".join(paras)
                        if concerns:
                            example_text += "\n\nWe note the following observations:\n" + "\n".join(concerns)
                        if closing:
                            example_text += f"\n\n{closing}"

                        if example_text.strip():
                            store_style_example(
                                resolution_type = res_type_classified,
                                ingovern_rec    = ig_rec,
                                example_text    = example_text,
                            )

                        store_resolution_rag(
                            company_name   = company_name,
                            financial_year = financial_year,
                            notice_type    = session.get("notice_type", "AGM"),
                            industry       = session.get("industry", ""),
                            resolution     = {
                                "resolution_type":   res_type_classified,
                                "title":             r.get("title", ""),
                                "resolution_text":   r.get("resolution_text", ""),
                                "resolution_number": r.get("resolution_number", 0),
                            },
                            commentary     = {
                                "ingovern_recommendation":   ig_rec,
                                "management_recommendation": r.get("management_recommendation", "FOR"),
                                "governance_concerns":       concerns,
                                "closing_recommendation":    closing,
                                "body_text":                 example_text,
                            },
                        )

                supabase_synced = True

    except Exception as exc:
        supabase_error = str(exc)

    return {
        "status":          "approved",
        "approved_by":     session["approved_by"],
        "saved_as":        filename,
        "supabase_synced": supabase_synced,
        "supabase_error":  supabase_error,
    }
