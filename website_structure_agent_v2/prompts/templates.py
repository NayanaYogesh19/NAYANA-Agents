"""
prompts/templates.py
All prompt templates — site-specific, dynamic, no hardcoded recommendations.
"""

# ── 1. General site analysis (competitor OR target) ───────────────────────────
SITE_ANALYSIS_PROMPT = """You are an expert website architecture analyst.

Analyse the raw scraped content from this website and extract structural data. Return ONLY a valid JSON object.

Website URL   : {url}
Website label : {label}

Raw scraped content:
{raw_content}

Return ONLY this JSON structure (no markdown, no explanation):
{{
  "nav_labels":        ["exact navigation item labels found on the page"],
  "url_patterns":      ["URL path patterns discovered e.g. /blog/*, /services/category/item"],
  "url_endpoints":     ["every distinct URL path found in the content e.g. /about, /services/seo, /contact"],
  "content_depth":     <integer — max URL nesting depth, e.g. 3 for /a/b/c>,
  "page_count":        <integer — estimated total distinct pages on the site>,
  "top_pages":         ["most prominent page names or types found e.g. Homepage, Blog, Pricing, Demo"],
  "structural_notes":  ["3–5 specific observations about THIS site's structure, navigation, or URL organisation"]
}}

Rules:
- Extract REAL data from the scraped content — do not invent or guess
- url_endpoints must be actual paths found in links or href attributes
- structural_notes must be specific to THIS site, not generic web advice
- If data cannot be found, use empty arrays or 0
"""

# ── 2. Audit notes extraction ─────────────────────────────────────────────────
AUDIT_EXTRACTION_PROMPT = """You are an expert SEO and website structure auditor.

Extract structural issues from the audit notes below. Return ONLY a valid JSON object.

{{
  "crawl_errors":        ["exact page URLs or descriptions with 404s, blocks, or crawl failures from the notes"],
  "orphan_pages":        ["exact page URLs identified as having no internal links pointing to them"],
  "redirect_chains":     ["exact URL chains involved in 301/302 redirect sequences"],
  "thin_content_pages":  ["exact page URLs flagged for very little or low-quality content, with word counts if given"],
  "missing_pages":       ["pages that should logically exist but are absent based on the audit notes"],
  "structural_issues":   ["broader structural problems explicitly mentioned e.g. flat hierarchy, duplicate nav, broken breadcrumbs"],
  "severity_summary":    "High | Medium | Low"
}}

Audit notes:
{audit_text}

Rules:
- Only extract what is explicitly stated in the audit notes — do not invent issues
- Use the exact URLs and descriptions from the notes
- If a category has no issues mentioned, return an empty array
"""

# ── 3. Audit existing site — AI fixes the structure ──────────────────────────
TARGET_SITE_AUDIT_PROMPT = """You are an expert website architect, SEO strategist, and UX designer.

The user wants to AUDIT their existing website and receive a specific, data-driven plan to fix its structural problems.

=== BUSINESS CONTEXT ===
Target site URL  : {target_url}
Business type    : {business_type}
Business goal    : {business_goal}
Business context : {business_desc}

=== TARGET SITE — CURRENT STRUCTURE (scraped live) ===
{target_summary}

=== COMPETITOR BENCHMARKS (scraped live) ===
{competitor_summary}

=== USER-PROVIDED AUDIT FINDINGS ===
{audit_section}

=== YOUR TASK ===
Produce a comprehensive structural audit and correction plan. Every recommendation must directly reference actual data from the scrape above — specific URLs, actual nav labels, discovered pages. Never give generic advice.

Return ONLY this JSON (no markdown, no preamble):
{{
  "pages": [
    {{
      "page_name":         "Home",
      "tier":              1,
      "url_slug":          "/",
      "page_type":         "hub",
      "parent_page":       null,
      "priority":          "High",
      "cta_type":          "specific CTA action e.g. Book a Free Audit",
      "wireframe_pattern": "Hero with value prop + key services grid + trust signals + CTA"
    }}
  ],
  "navigation": {{
    "primary_nav":            ["nav items based on what this site actually needs"],
    "secondary_nav":          ["utility nav items"],
    "breadcrumb_example":     ["Home", "Category", "Specific Page"],
    "internal_linking_rules": [
      "Specific rule referencing this site's actual pages e.g. Every /services/* page must link to /contact and the relevant /case-studies/* entry",
      "..."
    ]
  }},
  "conversion_paths": [
    {{
      "goal":              "{business_goal}",
      "funnel_steps":      ["Specific awareness page on this site", "Specific consideration page", "Specific decision page", "Conversion page"],
      "cta_per_tier":      {{
        "Tier 1 — Home / Hub":         "Specific CTA text e.g. Get a Free Website Audit",
        "Tier 2 — Category / Service": "Specific CTA text e.g. See Our Work in [Their Industry]",
        "Tier 3 — Detail / Product":   "Specific CTA text e.g. Request a Proposal for This Service"
      }},
      "key_landing_pages": ["/actual-slug-from-site", "/another-real-slug"]
    }}
  ],
  "recommendations": [
    "Specific fix #1 referencing an actual page, URL or issue found in the scraped data",
    "Specific fix #2 ...",
    "Specific fix #3 ...",
    "Specific fix #4 ...",
    "Specific fix #5 ...",
    "Specific fix #6 ...",
    "Specific fix #7 ...",
    "Specific fix #8 ...",
    "Specific fix #9 ...",
    "Specific fix #10 ..."
  ],
  "implementation_strategy": [
    "Phase 1 — [specific phase name]: [what to do, referencing actual site pages and issues]",
    "Phase 2 — ...",
    "Phase 3 — ...",
    "Phase 4 — ...",
    "Phase 5 — ...",
    "Phase 6 — ..."
  ]
}}

Critical rules:
- ALL recommendations must reference specific pages, URLs, or issues found in the scraped data above
- Pages list must be comprehensive — include ALL pages this business needs (aim for 20–35 pages minimum)
- For {business_type} with goal "{business_goal}": tailor page types, CTAs, and funnel steps accordingly
- B2B: hub pages, solution/service pages, case studies, resources, demo/consultation, industry pages
- B2C: category pages, product listing, product detail, reviews, cart/checkout flow, support
- URL slugs: lowercase, hyphen-separated, no stop words, logically nested
- Do NOT hardcode competitor names or fake URLs — use only what was actually scraped
"""

# ── 4. New website structure — how to build it correctly ─────────────────────
NEW_STRUCTURE_PROMPT = """You are an expert website architect, SEO strategist, and UX designer.

The user wants to PLAN A NEW WEBSITE. You have scraped their target URL to understand what currently exists there, and now you will design the ideal new structure.

=== BUSINESS CONTEXT ===
Target domain    : {target_url}
Business type    : {business_type}
Business goal    : {business_goal}
Business context : {business_desc}

=== TARGET SITE — CURRENT STATE (scraped live) ===
{target_summary}

=== YOUR TASK ===
Based on what currently exists at the target URL above, design the IDEAL new website structure.
- Reference what's there now (existing pages, nav, URLs) when relevant
- Identify what is MISSING that this business needs
- Design a complete, comprehensive new structure
- Every recommendation must be specific to THIS domain and business context — not generic

Return ONLY this JSON (no markdown, no preamble):
{{
  "pages": [
    {{
      "page_name":         "Home",
      "tier":              1,
      "url_slug":          "/",
      "page_type":         "hub",
      "parent_page":       null,
      "priority":          "High",
      "cta_type":          "specific CTA e.g. Get a Free Consultation",
      "wireframe_pattern": "Hero + value proposition + service highlights + social proof + CTA"
    }}
  ],
  "navigation": {{
    "primary_nav":            ["specific nav items this business needs"],
    "secondary_nav":          ["utility nav e.g. Login, Get Quote, Contact"],
    "breadcrumb_example":     ["Home", "Specific Section", "Specific Page"],
    "internal_linking_rules": [
      "Specific rule for this site e.g. Each /services/* page links to 2 related case studies",
      "..."
    ]
  }},
  "conversion_paths": [
    {{
      "goal":              "{business_goal}",
      "funnel_steps":      ["Specific awareness entry point", "Specific consideration step", "Specific decision step", "Conversion action"],
      "cta_per_tier":      {{
        "Tier 1 — Home / Hub":         "Specific CTA text",
        "Tier 2 — Category / Service": "Specific CTA text",
        "Tier 3 — Detail / Product":   "Specific CTA text"
      }},
      "key_landing_pages": ["/specific-slug", "/another-slug"]
    }}
  ],
  "recommendations": [
    "Specific recommendation #1 referencing what was found (or missing) in the current site scrape",
    "Specific recommendation #2 ...",
    "Specific recommendation #3 ...",
    "Specific recommendation #4 ...",
    "Specific recommendation #5 ...",
    "Specific recommendation #6 ...",
    "Specific recommendation #7 ...",
    "Specific recommendation #8 ...",
    "Specific recommendation #9 ...",
    "Specific recommendation #10 ...",
    "Specific recommendation #11 ...",
    "Specific recommendation #12 ..."
  ],
  "implementation_strategy": [
    "Phase 1 — Foundation (Weeks 1-3): [Specific pages to build first based on business goal]",
    "Phase 2 — Core Content (Weeks 4-6): [Specific sections with page names]",
    "Phase 3 — Conversion (Weeks 7-9): [Specific conversion pages and forms]",
    "Phase 4 — Social Proof (Weeks 10-12): [Specific trust-building pages]",
    "Phase 5 — Resources & SEO (Weeks 13-15): [Specific content hub pages]",
    "Phase 6 — Optimisation (Weeks 16-18): [Specific testing and performance tasks]",
    "Phase 7 — Automation (Weeks 19-21): [Specific CRM, email, tracking integrations]",
    "Phase 8 — Ongoing Growth (Month 6+): [Specific ongoing tasks]"
  ]
}}

Critical rules:
- Pages list must be COMPREHENSIVE — aim for 25–40 pages covering all sections this business needs
- Reference what currently exists vs what needs to be added based on the scraped data
- For {business_type} with goal "{business_goal}": tailor every page type, CTA, and funnel step
- B2B: hub pages, solution pages, industry verticals, case studies, resources, demo/consultation pages
- B2C: category hierarchy, product pages, reviews, cart/checkout, loyalty/returns pages
- URL slugs: lowercase, hyphen-separated, logically nested — no stop words
- Recommendations must reference the specific domain, industry and goal — zero generic statements
"""
