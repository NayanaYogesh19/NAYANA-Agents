"""
ux_engine.py
Runs 8 UX rule checks on the scraped form data.
Dynamic B2B / B2C logic adjusts thresholds and rules automatically.
Returns a scored result dict used by the AI diagnosis engine.
"""


MAX_FIELDS_B2B = 5
MAX_FIELDS_B2C = 3

WEAK_CTAS = {"submit", "send", "go", "ok", "next", "continue", "click here", ""}

STRONG_CTA_EXAMPLES_B2B = [
    "Get my free audit", "Book a call", "Talk to sales",
    "Download the guide", "Request a demo", "Get a quote",
]
STRONG_CTA_EXAMPLES_B2C = [
    "Get my quote", "Start free trial", "Claim my offer",
    "Yes, send it to me", "Get started", "Sign me up",
]

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "aol.com", "live.com", "msn.com", "ymail.com",
}

MOBILE_INPUT_TYPES = {
    "email": "email",
    "phone": "tel",
    "tel": "tel",
    "number": "number",
    "zip": "number",
    "postcode": "number",
}


def run_ux_checks(form_data: dict, audience: str, device_priority: str) -> dict:
    """
    Run all 8 UX checks against a single form dict.
    audience: 'b2b' or 'b2c'
    device_priority: 'mobile', 'desktop', or 'both'
    Returns dict with per-check results and a total UX score (0-100).
    """
    is_b2b = audience.lower() == "b2b"
    fields = form_data.get("fields", [])
    cta = form_data.get("cta", {})
    errors = form_data.get("error_messages", [])

    checks = {}

    # ── Check 1: Field count ─────────────────────────────────
    max_fields = MAX_FIELDS_B2B if is_b2b else MAX_FIELDS_B2C
    field_count = len(fields)
    checks["field_count"] = {
        "name": "Field Count",
        "passed": field_count <= max_fields,
        "score": 10 if field_count <= max_fields else max(0, 10 - (field_count - max_fields) * 2),
        "max_score": 10,
        "finding": f"{field_count} fields found. Max recommended for {audience.upper()}: {max_fields}.",
        "fix": f"Remove fields to reach {max_fields}. Prioritise removing: company size, title, address." if field_count > max_fields else "Field count is optimal.",
    }

    # ── Check 2: Label clarity ────────────────────────────────
    fields_missing_labels = [f for f in fields if not f.get("has_label")]
    placeholder_only = [f for f in fields if f.get("label_only_placeholder")]
    checks["label_clarity"] = {
        "name": "Label Clarity",
        "passed": len(fields_missing_labels) == 0,
        "score": 10 if not fields_missing_labels else max(0, 10 - len(fields_missing_labels) * 3),
        "max_score": 10,
        "finding": f"{len(fields_missing_labels)} fields missing labels. {len(placeholder_only)} use placeholder-only labels.",
        "fix": "Add visible labels above every field. Never use placeholder text as the only label — it disappears on focus.",
    }

    # ── Check 3: Mobile UX ───────────────────────────────────
    mobile_issues = []
    for f in fields:
        field_name = f.get("name", "").lower()
        for keyword, expected_type in MOBILE_INPUT_TYPES.items():
            if keyword in field_name and f.get("type") != expected_type:
                mobile_issues.append(f"Field '{f.get('name')}' should use type='{expected_type}' for correct mobile keyboard")
    is_mobile_relevant = device_priority in ("mobile", "both")
    checks["mobile_ux"] = {
        "name": "Mobile UX",
        "passed": len(mobile_issues) == 0,
        "score": 10 if not mobile_issues else max(0, 10 - len(mobile_issues) * 3),
        "max_score": 10,
        "finding": f"{len(mobile_issues)} mobile input type issue(s) found." if mobile_issues else "Mobile input types look correct.",
        "details": mobile_issues,
        "fix": "Set input type='email' for email, type='tel' for phone, type='number' for numeric fields. This opens the correct mobile keyboard.",
    }

    # ── Check 4: Email Validation ────────────────────────────
    email_fields = [f for f in fields if f.get("type") == "email" or "email" in f.get("name", "").lower()]
    b2b_note = "B2B: Ensure real-time ZeroBounce API blocks free-domain emails (gmail, hotmail)." if is_b2b else "B2C: Ensure NeverBounce validates syntax and deliverability without blocking free domains."
    checks["email_validation"] = {
        "name": "Email Validation",
        "passed": len(email_fields) > 0,
        "score": 8 if email_fields else 4,
        "max_score": 8,
        "finding": f"{len(email_fields)} email field(s) detected." if email_fields else "No email field detected — required for lead generation.",
        "fix": b2b_note,
        "api_recommended": "ZeroBounce" if is_b2b else "NeverBounce",
    }

    # ── Check 5: CTA Copy ────────────────────────────────────
    cta_text = cta.get("text", "").lower()
    is_weak = cta.get("is_weak_cta", True)
    examples = STRONG_CTA_EXAMPLES_B2B if is_b2b else STRONG_CTA_EXAMPLES_B2C
    checks["cta_copy"] = {
        "name": "CTA Copy",
        "passed": not is_weak,
        "score": 10 if not is_weak else 3,
        "max_score": 10,
        "finding": f"CTA text is '{cta.get('text', 'missing')}'. {'Weak — generic verb detected.' if is_weak else 'Action-oriented CTA detected.'}",
        "fix": f"Replace with a specific, value-driven CTA. Examples: {', '.join(examples[:3])}",
    }

    # ── Check 6: Trust Signals ───────────────────────────────
    has_trust = form_data.get("has_trust_signals", False)
    checks["trust_signals"] = {
        "name": "Trust Signals",
        "passed": has_trust,
        "score": 8 if has_trust else 0,
        "max_score": 8,
        "finding": "Trust signals detected near form." if has_trust else "No trust signals found near the form.",
        "fix": "Add: SSL badge, 'No spam' note, client logos, testimonial quote, or security badge near the submit button.",
    }

    # ── Check 7: Error Messages ───────────────────────────────
    has_good_errors = any(len(e) > 20 for e in errors)
    checks["error_messages"] = {
        "name": "Error Messages",
        "passed": has_good_errors,
        "score": 8 if has_good_errors else 2,
        "max_score": 8,
        "finding": f"{len(errors)} error message(s) found." if errors else "No error messages found in page source. May be dynamically injected.",
        "fix": "Error messages must say WHAT went wrong AND HOW to fix it. 'Invalid email' fails. 'Please enter a work email (e.g. name@company.com)' passes.",
        "examples": errors[:3] if errors else [],
    }

    # ── Check 8: GDPR Consent ────────────────────────────────
    has_gdpr = form_data.get("has_gdpr_consent", False)
    checks["gdpr_consent"] = {
        "name": "GDPR / Consent Copy",
        "passed": has_gdpr,
        "score": 8 if has_gdpr else 0,
        "max_score": 8,
        "finding": "GDPR / consent copy detected near form." if has_gdpr else "No GDPR consent copy found. Required for EU traffic.",
        "fix": "Add: 'By submitting you agree to our Privacy Policy. We will never share your data.' above the submit button.",
    }

    # ── Total UX Score ────────────────────────────────────────
    total = sum(c["score"] for c in checks.values())
    max_total = sum(c["max_score"] for c in checks.values())
    score_pct = round((total / max_total) * 100)

    grade = "A" if score_pct >= 85 else "B" if score_pct >= 70 else "C" if score_pct >= 55 else "D"

    return {
        "checks": checks,
        "ux_score": score_pct,
        "ux_grade": grade,
        "total_points": total,
        "max_points": max_total,
        "audience": audience,
        "device_priority": device_priority,
        "priority_fixes": _get_priority_fixes(checks),
    }


def _get_priority_fixes(checks: dict) -> list[dict]:
    """Return top 3 highest-impact failed checks."""
    failed = [
        {"check": k, "name": v["name"], "fix": v["fix"], "impact": v["max_score"] - v["score"]}
        for k, v in checks.items()
        if not v["passed"]
    ]
    return sorted(failed, key=lambda x: x["impact"], reverse=True)[:3]


def estimate_conversion_loss(ux_score: int, field_count: int, audience: str) -> dict:
    """
    Estimate monthly leads lost and projected lift from fixing issues.
    Based on industry CRO benchmarks.
    """
    baseline_rate = 0.12 if audience.lower() == "b2c" else 0.08
    penalty_per_extra_field = 0.015
    ux_penalty = max(0, (75 - ux_score) / 100 * 0.2)
    max_fields = MAX_FIELDS_B2B if audience.lower() == "b2b" else MAX_FIELDS_B2C
    extra_fields = max(0, field_count - max_fields)
    adjusted_rate = max(0.01, baseline_rate - (extra_fields * penalty_per_extra_field) - ux_penalty)
    optimised_rate = min(0.35, adjusted_rate * 1.4 + (ux_score / 100) * 0.05)
    lift_pct = round((optimised_rate - adjusted_rate) / adjusted_rate * 100)

    return {
        "current_estimated_rate": f"{round(adjusted_rate * 100, 1)}%",
        "projected_rate_after_fixes": f"{round(optimised_rate * 100, 1)}%",
        "estimated_lift": f"+{lift_pct}%",
        "assumptions": f"Based on {audience.upper()} benchmarks. Field count: {field_count}. UX Score: {ux_score}/100.",
    }
