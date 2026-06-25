"""
ai_engine.py
Uses Claude (via OpenRouter) to:
  1. Diagnose root causes of UX issues
  2. Generate field-level copy rewrites
  3. Produce CTA improvements and error message rewrites
  4. Create an A/B test plan
  5. Generate paid ads form specs (Meta, Google, LinkedIn)
"""

import os
import json
import httpx


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-4o-mini"



def _call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    """Make a request to Claude via OpenRouter."""
    if not OPENROUTER_API_KEY:
        return _fallback_response("OpenRouter API key not set. Add OPENROUTER_API_KEY to your .env file.")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://trilliantdigital.com",
        "X-Title": "Form UX Optimisation Agent",
    }
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        resp = httpx.post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return _fallback_response(str(e))


def _fallback_response(error: str) -> str:
    return json.dumps({
        "error": error,
        "note": "AI diagnosis unavailable. Rule-based findings still apply.",
    })


# ── Website Form Diagnosis ─────────────────────────────────────────────────────

def diagnose_form(
    form_data: dict,
    ux_results: dict,
    analytics: dict,
    audience: str,
    business_goal: str,
    user_description: str = "",
) -> dict:
    """Generate full AI diagnosis and recommendations for a website form."""

    system = (
        "You are an expert CRO (Conversion Rate Optimisation) analyst specialising in form UX "
        "for B2B and B2C lead generation. You analyse form data, UX rule violations, and behavioural "
        "analytics to diagnose root causes and generate specific, actionable fix recommendations. "
        "CRITICAL: Always respond with ONLY a valid JSON object — no markdown fences, no extra text, no explanation outside the JSON."
    )

    fields_summary = form_data.get('fields', [])
    field_names = [f.get('name', f.get('label', 'unnamed')) for f in fields_summary]

    user = f"""
Analyse this form and provide a full CRO diagnosis:

AUDIENCE: {audience.upper()}
BUSINESS GOAL: {business_goal}
FIELD COUNT: {form_data.get('field_count', 0)}
FIELDS DETECTED: {json.dumps(field_names)}
FIELD DETAILS: {json.dumps(fields_summary, indent=2)}
CTA: {json.dumps(form_data.get('cta', {}), indent=2)}
HAS TRUST SIGNALS: {form_data.get('has_trust_signals', False)}
HAS GDPR CONSENT: {form_data.get('has_gdpr_consent', False)}
UX SCORE: {ux_results.get('ux_score', 0)}/100 (Grade {ux_results.get('ux_grade', 'N/A')})
FAILED CHECKS: {json.dumps(ux_results.get('priority_fixes', []), indent=2)}
ANALYTICS: {json.dumps(analytics, indent=2)}
USER REQUIREMENTS: {user_description if user_description else "None provided — base diagnosis on scraped form data above."}

IMPORTANT: If USER REQUIREMENTS are provided, incorporate those specific requirements into your recommendations — field suggestions, CTA copy, form structure, and redesign recommendations must reflect the user's stated needs.

Return ONLY a JSON object with ALL of these keys populated (never leave arrays empty):
{{
  "key_issues": [
    "Issue 1: specific problem found and its conversion impact",
    "Issue 2: specific problem found and its conversion impact",
    "Issue 3: specific problem found and its conversion impact"
  ],
  "root_causes": [
    "Root cause 1 ranked by conversion impact — be specific to this form",
    "Root cause 2 ranked by conversion impact — be specific to this form",
    "Root cause 3 ranked by conversion impact — be specific to this form"
  ],
  "field_rewrites": {{"old_label": "new_label"}},
  "cta_variants": [
    "CTA variant 1 specific to {business_goal} and {audience.upper()} audience",
    "CTA variant 2 specific to {business_goal} and {audience.upper()} audience",
    "CTA variant 3 specific to {business_goal} and {audience.upper()} audience"
  ],
  "error_message_rewrites": {{"field_name": "improved error message text"}},
  "quick_wins": [
    "Quick win 1: specific action doable in under 1 hour with expected impact",
    "Quick win 2: specific action doable in under 1 hour with expected impact",
    "Quick win 3: specific action doable in under 1 hour with expected impact"
  ],
  "strategic_fixes": [
    "Strategic fix 1 requiring dev work — ranked by conversion impact",
    "Strategic fix 2 requiring dev work — ranked by conversion impact",
    "Strategic fix 3 requiring dev work — ranked by conversion impact"
  ],
  "ux_optimisation_plan": [
    "UX improvement 1: specific form layout or interaction change with rationale",
    "UX improvement 2: specific field or label change with rationale",
    "UX improvement 3: specific trust/GDPR/error UX change with rationale",
    "UX improvement 4: specific CTA or submit flow change with rationale"
  ],
  "form_redesign_recommendations": [
    "Recommendation 1: what to change in the form structure and why",
    "Recommendation 2: what to change in field design and why",
    "Recommendation 3: what to change in form copy and messaging and why"
  ],
  "ab_test_plan": [
    {{
      "test_id": "T1",
      "hypothesis": "specific hypothesis for this form",
      "control": "current state",
      "variant": "proposed change",
      "metric": "conversion rate",
      "duration_days": 14
    }},
    {{
      "test_id": "T2",
      "hypothesis": "second test hypothesis",
      "control": "current state",
      "variant": "proposed change",
      "metric": "form completion rate",
      "duration_days": 14
    }}
  ]
}}
"""
    raw = _call_claude(system, user, max_tokens=3000)
    # Strip markdown fences if model wraps response
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        result = json.loads(raw)
        # Build backward-compatible executive_summary from key_issues
        if "key_issues" in result and "executive_summary" not in result:
            result["executive_summary"] = result["key_issues"]
        elif "executive_summary" in result and isinstance(result["executive_summary"], str):
            # Convert paragraph to list of sentences for bullet rendering
            sentences = [s.strip() for s in result["executive_summary"].replace(". ", ".|").split("|") if s.strip()]
            result["key_issues"] = sentences if sentences else [result["executive_summary"]]
        return result
    except Exception:
        # Fallback: return whatever we can with guaranteed non-empty arrays
        checks = ux_results.get("checks", {})
        failed = [v["finding"] for v in checks.values() if not v.get("passed")]
        fixes = [v["fix"] for v in checks.values() if not v.get("passed")]
        return {
            "key_issues": failed if failed else ["Form analysis complete. See UX check results for details."],
            "root_causes": fixes[:3] if fixes else ["Review UX check findings for root cause details."],
            "quick_wins": fixes[:3] if fixes else ["Address failed UX checks listed in the UX Checks tab."],
            "cta_variants": ["Request a Demo", "Get a Free Consultation", "Talk to Our Team"],
            "strategic_fixes": ["Implement real-time form validation", "Add GDPR consent checkbox", "Add trust badges near submit button"],
            "ux_optimisation_plan": ["Add visible labels above all fields", "Improve error message copy to be specific", "Add social proof near submit button", "Optimise CTA button copy for intent"],
            "form_redesign_recommendations": ["Restructure form to reduce field count", "Add inline field validation", "Add progress indicator for multi-step forms"],
            "ab_test_plan": [],
            "error": "AI response could not be parsed — showing rule-based fallback.",
        }


# ── Create New Form Blueprint ──────────────────────────────────────────────────

def generate_new_form_blueprint(
    account_name: str,
    website_url: str,
    page_title: str,
    site_content_summary: str,
    business_goal: str,
    audience: str,
    device_priority: str,
    user_description: str = "",
) -> dict:
    """Generate a complete new form blueprint based on website content analysis."""

    is_b2b = audience.lower() == "b2b"
    max_fields = 5 if is_b2b else 3

    system = (
        "You are an expert CRO and UX form designer. You analyse a website's content, "
        "business goal, and audience to design the highest-converting form possible. "
        "Be specific to THIS website — use their actual business, products, and audience. "
        "CRITICAL: Respond with ONLY a valid JSON object, no markdown fences."
    )

    user = f"""
Design a high-converting form for this website:

ACCOUNT: {account_name}
WEBSITE: {website_url}
PAGE TITLE: {page_title}
BUSINESS GOAL: {business_goal}
AUDIENCE: {audience.upper()} ({'Max ' + str(max_fields) + ' fields recommended'})
DEVICE PRIORITY: {device_priority}
WEBSITE CONTENT SUMMARY:
{site_content_summary}
USER REQUIREMENTS: {user_description if user_description else "None provided — base design on website content above."}

IMPORTANT: If USER REQUIREMENTS are provided, treat them as the primary brief. Every field, CTA, form title, and recommendation must directly address the user's stated requirements first, then be enhanced by the website content analysis.

Return ONLY a JSON object with ALL keys populated:
{{
  "form_title": "Recommended form heading specific to this business",
  "form_description": "1-2 sentence subheading shown above the form",
  "recommended_fields": [
    {{
      "field_name": "field identifier",
      "label": "User-facing label",
      "type": "text|email|tel|select|textarea|checkbox",
      "placeholder": "helpful placeholder text",
      "required": true,
      "options": ["option1", "option2"],
      "why_include": "specific reason this field helps conversion for this business"
    }}
  ],
  "cta_button_text": "Specific action-oriented CTA for this business goal",
  "form_position_recommendation": "Where on the page this form should appear and why",
  "projected_ux_score": 85,
  "projected_conversion_rate": "12-18%",
  "why_this_works": [
    "Reason 1 specific to this business and audience",
    "Reason 2 specific to this business and audience",
    "Reason 3 specific to this business and audience"
  ],
  "what_happens_next": [
    "Step 1: what the business receives when a lead submits",
    "Step 2: recommended follow-up action within X hours",
    "Step 3: CRM/email automation recommendation"
  ],
  "optimization_strategies": [
    "Strategy 1: specific tactic to improve this form over time",
    "Strategy 2: A/B test recommendation for this specific form",
    "Strategy 3: trust signal recommendation specific to this industry",
    "Strategy 4: follow-up sequence recommendation"
  ],
  "field_optimization_tips": [
    "Tip for field 1: how to maximise completion of this specific field",
    "Tip for field 2: how to maximise completion of this specific field"
  ],
  "trust_signals_to_add": [
    "Trust signal 1 specific to this business type",
    "Trust signal 2 specific to this business type"
  ],
  "gdpr_consent_text": "Specific GDPR consent copy for this business",
  "error_messages": {{
    "field_name": "specific helpful error message"
  }},
  "implementation_plan": [
    "Step 1: technical implementation instruction",
    "Step 2: copy/content instruction",
    "Step 3: testing instruction before going live"
  ],
  "ab_test_plan": [
    {{
      "test_id": "T1",
      "hypothesis": "specific hypothesis for this form and business",
      "control": "current proposed design",
      "variant": "what to change",
      "metric": "conversion rate",
      "duration_days": 14
    }}
  ]
}}
"""
    raw = _call_claude(system, user, max_tokens=3500)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        return {
            "form_title": f"Contact {account_name}",
            "form_description": f"Get in touch with us about your {business_goal.lower()} needs.",
            "recommended_fields": [
                {"field_name": "name", "label": "Full Name", "type": "text", "placeholder": "Your name", "required": True, "options": [], "why_include": "Essential for personalised follow-up"},
                {"field_name": "email", "label": "Email Address", "type": "email", "placeholder": "your@email.com", "required": True, "options": [], "why_include": "Primary contact channel"},
                {"field_name": "message", "label": "How can we help?", "type": "textarea", "placeholder": "Tell us about your requirements...", "required": False, "options": [], "why_include": "Qualifies lead intent"},
            ],
            "cta_button_text": "Get in Touch",
            "projected_ux_score": 78,
            "projected_conversion_rate": "10-15%",
            "why_this_works": ["Minimal fields reduce friction", "Clear CTA communicates value", "Mobile-optimised field types"],
            "what_happens_next": ["Lead details received in CRM", "Follow up within 2 hours", "Send automated confirmation email"],
            "optimization_strategies": ["A/B test CTA copy", "Add social proof near submit", "Implement real-time validation"],
            "field_optimization_tips": ["Use autocomplete on name/email", "Add inline validation"],
            "trust_signals_to_add": ["Add SSL badge", "Add response time promise"],
            "gdpr_consent_text": "By submitting you agree to our Privacy Policy. We will never share your data.",
            "error_messages": {"email": "Please enter a valid work email address"},
            "implementation_plan": ["Build form with correct input types", "Add GDPR consent checkbox", "Test on mobile before launch"],
            "ab_test_plan": [],
            "error": "AI unavailable — showing default blueprint",
        }


# ── Meta Instant Form Generator ────────────────────────────────────────────────

def generate_meta_form_spec(
    account_name: str,
    business_goal: str,
    audience: str,
    website_url: str,
    contact_fields: list[str],
    custom_questions: list[str] = None,
    user_description: str = "",
    form_type: str = "",
    flexible_delivery: bool = True,
    intro_headline: str = "",
    intro_description: str = "",
    questions_description: str = "",
    privacy_policy_url: str = "",
    privacy_link_text: str = "",
) -> dict:
    """Generate a complete Meta instant form specification matching Meta Ads Manager structure."""

    is_b2b = audience.lower() == "b2b"
    # Use provided form_type or smart default
    resolved_form_type = form_type or ("Higher intent" if is_b2b else "More volume")
    email_tool = "ZeroBounce (block free domains)" if is_b2b else "NeverBounce (syntax + deliverability check)"
    review_screen = resolved_form_type == "Higher intent"

    system = (
        "You are an expert Meta Ads lead generation specialist. "
        "You design high-converting Meta instant lead forms for B2B and B2C campaigns. "
        "Structure your output to exactly match the Meta Ads Manager Create Form screens: "
        "Form type, Intro, Questions (Contact information), Privacy Policy, Review screen, Ending. "
        "Always respond in valid JSON only."
    )

    default_privacy_url = privacy_policy_url or f"{website_url}/privacy"

    default_privacy_text = (
        privacy_link_text
        or f"Visit {account_name}'s Privacy Policy."
    )

    work_email_mode = "true" if is_b2b else "false"

    review_enabled = "true" if review_screen else "false"

    review_note = (
        "review step lets leads confirm details before submitting"
        if review_screen
        else ""
    )

    user = f"""
Generate a complete Meta instant form specification for:

ACCOUNT / BRAND: {account_name}
BUSINESS GOAL: {business_goal}
AUDIENCE: {audience.upper()}
WEBSITE: {website_url}

FORM CONFIGURATION:
- Form Type: {resolved_form_type}
- Flexible Delivery: {"Enabled (Optimised)" if flexible_delivery else "Manual"}
- Review Screen: {"Enabled" if review_screen else "Disabled"}

USER-PROVIDED COPY (enhance if provided, generate if empty — be specific to this brand/goal):
- Intro Headline: {intro_headline or "(generate — max 60 chars, specific to " + account_name + " and " + business_goal + ")"}
- Intro Description: {intro_description or "(generate — max 150 chars, specific to this business)"}
- Questions Description: {questions_description or "(generate — clear data-use statement for this business)"}
- Contact Fields: {contact_fields}
- Custom Questions (user-added): {custom_questions or "(none — AI may suggest 1-2 qualifying questions for this goal)"}
- Privacy URL: {privacy_policy_url or website_url + "/privacy"}
- Privacy Link Text: {privacy_link_text or "Visit " + account_name + "'s Privacy Policy."}
- User Campaign Requirements: {user_description if user_description else "(none — generate based on goal and audience)"}

IMPORTANT: If User Campaign Requirements are provided, treat them as the primary creative brief. All 5 options for every element (headlines, descriptions, CTAs) must directly reflect the user's stated campaign intent, tone, and specific requirements.

Rules:
- Intro headline MUST be max 60 chars
- Intro/thank-you description MUST be max 150 chars
- Contact fields ONLY from Meta native set: Email, Full name, Phone number, Website
- For B2B: use work email collection
- Be SPECIFIC to {account_name} — no generic answers

Return ONLY a valid JSON object with these exact keys:
{{
  "form_name": "specific descriptive name for {account_name} in Ads Manager",
  "form_type": "{resolved_form_type}",
  "flexible_delivery": {str(flexible_delivery).lower()},
  "intro_card": {{
    "headline": "compelling headline max 60 chars specific to {account_name}",
    "headline_options": ["option 1 max 60 chars", "option 2 max 60 chars", "option 3 max 60 chars", "option 4 max 60 chars", "option 5 max 60 chars"],
    "description": "persuasive description max 150 chars specific to this business",
    "description_options": ["option 1 max 150 chars", "option 2", "option 3", "option 4", "option 5"],
    "image_recommendation": "specific creative direction for {account_name} ads"
  }},
  "questions_section": {{
    "description": "data-use statement specific to {account_name}",
    "description_options": ["option 1", "option 2", "option 3", "option 4", "option 5"],
    "pre_fill_fields": {contact_fields},
    "work_email_mode": {"true" if is_b2b else "false"},
    "custom_questions": {custom_questions or []}
  }},
  "privacy_policy": {{
    "url": "{default_privacy_url}",
    "link_text": "{default_privacy_text}",
    "link_text_options": ["option 1", "option 2", "option 3", "option 4", "option 5"]
  }},
  "review_screen": {{
    "enabled": {"true" if review_screen else "false"},
    "note": "{review_note}"
  }},
  "thank_you_screen": {{
    "headline": "thank-you headline max 60 chars specific to {account_name}",
    "headline_options": ["option 1 max 60 chars", "option 2", "option 3", "option 4", "option 5"],
    "description": "next-step description max 150 chars",
    "description_options": ["option 1", "option 2", "option 3", "option 4", "option 5"],
    "cta_button_text": "action CTA max 30 chars",
    "cta_options": ["option 1", "option 2", "option 3", "option 4", "option 5"],
    "cta_url": "{website_url}"
  }},
  "email_validation": {{
    "tool_recommended": "{email_tool}",
    "setup_note": "specific setup instruction for post-submission webhook"
  }},
  "crm_sync_note": "specific CRM integration instruction for {account_name}",
  "optimisation_tips": [
    "tip 1 specific to {account_name} and {business_goal}",
    "tip 2 specific to this audience",
    "tip 3 specific to this form type",
    "tip 4 for maximising lead quality",
    "tip 5 for follow-up and conversion"
  ],
  "how_this_helps": [
    "benefit 1 of using this Meta form for {account_name}",
    "benefit 2 — impact on {business_goal}",
    "benefit 3 — audience targeting advantage",
    "benefit 4 — conversion rate expectation"
  ]
}}
"""
    raw = _call_claude(system, user, max_tokens=3000)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"raw_spec": raw, "error": "Could not parse JSON — see raw_spec"}


# ── Report Summary Generator ───────────────────────────────────────────────────

def generate_report_summary(
    diagnosis: dict,
    ux_results: dict,
    conversion_loss: dict,
    audience: str,
    business_goal: str,
) -> str:
    """Generate a clean executive summary paragraph for the PDF report."""

    system = "You are a senior CRO strategist writing a concise executive report for a marketing director."
    user = f"""
Write a 3-paragraph executive summary for this form audit report.

AUDIENCE: {audience.upper()}
GOAL: {business_goal}
UX SCORE: {ux_results.get('ux_score')}/100 (Grade {ux_results.get('ux_grade')})
CURRENT CONVERSION RATE: {conversion_loss.get('current_estimated_rate')}
PROJECTED RATE AFTER FIXES: {conversion_loss.get('projected_rate_after_fixes')}
ESTIMATED LIFT: {conversion_loss.get('estimated_lift')}
KEY ISSUES: {diagnosis.get('key_issues', diagnosis.get('root_causes', []))}
QUICK WINS: {diagnosis.get('quick_wins', [])}
UX OPTIMISATION PLAN: {diagnosis.get('ux_optimisation_plan', [])}

Write 3 flowing paragraphs. Be specific about: (1) current state and business impact, (2) the key UX and form problems found, (3) what to do next and the expected lift. No bullet points — flowing prose only.
"""
    return _call_claude(system, user, max_tokens=600)
