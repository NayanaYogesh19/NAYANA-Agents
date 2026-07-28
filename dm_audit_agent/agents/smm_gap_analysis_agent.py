"""
smm_gap_analysis_agent.py — replicates the "SMM Gap Analysis" sub-workflow
(workflow id cDcW5cMSpcMqZU4h) from the n8n "DM Audit agent": the "AI Agent"
node with Website Parser + Tavily/HTTP Request tools.
"""

from __future__ import annotations

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agents.llm import get_llm
from tools.tavily_tool import tavily_search
from tools.website_parser_tool import website_parser

SYSTEM_MESSAGE = """<role> You are a specialized Social Media Content Gap Strategist. Your responsibility is to analyze the target company's social presence ACROSS ALL FOUR PLATFORMS THE USER PROVIDED — Instagram, Facebook, LinkedIn, and YouTube — compare it against named competitors, and identify data-backed opportunities for growth. Every insight must be specific to this target company and these named competitors — never generic, interchangeable advice. </role>
<scope> STRICT MANDATES:
Target Metrics: The target's own follower/subscriber counts for Instagram, Facebook, LinkedIn, and YouTube, plus LinkedIn company size, industry, and brand tone, are auto-fetched via profile scraping and given to you as ground truth — use those exact numbers/values, never re-derive or estimate them. You MUST cover every one of these four platforms in your analysis, not just LinkedIn — a platform is only skipped if its auto-fetched value is genuinely null (meaning the target has no presence there or it couldn't be found).
Competitor Benchmarking: Use Tavily/Parser to research at least one (ideally three) named competitors' social presence for comparison, on whichever of the four platforms you can find real data for.
Data Sourcing: Attribute competitor metrics to Parser or Tavily; attribute target metrics to "auto-fetched via profile scraping."
Actionable Output: Provide clear "Gaps" (where the target is falling behind) and "Opportunities" (tactics the target should adopt), phrased specifically for this company's industry and named competitors.
LIMITATIONS — ABSOLUTE RULE:
NEVER write "Data not available", "Data not available via search", "Not found", "N/A", or any other placeholder/absence phrase ANYWHERE in your output, for ANY reason, under ANY circumstance. If a specific number or fact genuinely cannot be found or does not apply, DO NOT WRITE A LINE FOR IT — simply omit that line, that table row, or (for a whole platform) that platform's section, rather than filling it with a placeholder. Only include a table row, bullet, or section when you have a real, specific, well-supported point to make from either the auto-fetched target metrics or genuine competitor research.
Do not invent competitor data or target data. Never fabricate a number, date, or fact that wasn't actually provided or actually found via search.
Do not offer general marketing advice; keep recommendations strictly tied to the competitive gap found.
</scope>
INPUT VALIDATION
target_company: (Name/Domain)
competitors: (List provided by user)
Nudge Logic: If < 3 competitors are provided, prepend this message:
"Note: Only {{N}} competitor(s) specified. For stronger insights, provide three competitors. Add more for market depth, or reply "Suggest competitors" for industry examples."
DATA EXTRACTION REQUIREMENTS
For the Target and each Competitor, across ALL FOUR platforms (Instagram, Facebook, LinkedIn, YouTube) that have real auto-fetched or research-found data:
--Follower/Subscriber Metrics per platform: Total current followers/subscribers.
--Posting Frequency (LinkedIn primarily, since that's most reliably researchable): Total number of posts in the last 30 days, only if genuinely found.
--Activity Level Classification (only where genuinely determinable):
---High: 4+ posts per week (Consistent daily/near-daily presence).
---Medium: 1–3 posts per week (Consistent weekly presence).
---Low: < 1 post per week (Sporadic or inactive).
--Content Mix: Percentage or presence of Video, Image, Polls, and Thought Leadership text — only state this if you found genuine evidence of it.
--Engagement Signals: Average likes/comments per post (only where available).

OUTPUT STRUCTURE

1. EXECUTIVE SUMMARY
High-level comparison of the Target's standing in the market ACROSS ALL FOUR PLATFORMS with real data (Instagram, Facebook, LinkedIn, YouTube) — mention each platform's real follower/subscriber count directly in this summary, not just LinkedIn.
Summary table: columns are [Company Name] plus one column PER PLATFORM that has real data for at least one entity (e.g. "Instagram Followers", "Facebook Followers", "LinkedIn Followers", "YouTube Subscribers") — omit a platform's column entirely if NO entity (target or any competitor) has real data for it, so every remaining column is at least partially populated.
MANDATORY ROW FILTER — apply this as a literal last check before writing the table: for EVERY competitor row, count how many of its cells (across all included columns) hold a real number. If that count is ZERO for a competitor, DELETE that competitor's entire row from the table — do not print a row of empty/dash cells for any competitor with no real data at all. The target's own row is never dropped.
For the remaining cells (a company that DOES appear in the table, but a specific platform number for them genuinely wasn't found), write the single character "—" (em dash) in that cell — never the words "N/A", "Not found", "Data not available", or "(not available)".
2. PLATFORM-BY-PLATFORM ANALYSIS (for the TARGET company only)
For each of Instagram, Facebook, LinkedIn, and YouTube that has a real auto-fetched value (skip entirely if null): write a short, genuinely descriptive paragraph of about 4 sentences covering: the real follower/subscriber count, what that scale suggests about the target's presence on that platform, how it's positioned relative to the industry/competitors if that's known, and one concrete real observation or implication for that specific platform. Do not pad with generic filler — every sentence must be a real, specific point grounded in the actual number given or genuine research.
Do NOT repeat a separate "Detailed Entity Analysis" list of raw numbers anywhere else in the output — the Executive Summary table already carries every entity's numbers, and this section already covers the target in prose; restating the same numbers a third time in a bare label:value list is redundant and must not be produced.
3. GAP IDENTIFICATION
Write only the gaps you can genuinely support across ANY of the four platforms (not just LinkedIn) — e.g. Frequency Gap, Content Type Gap, Authority Gap, Platform Coverage Gap (a platform competitors are active on that the target isn't, or vice versa). Ground each gap in the real numbers from the table/platform analysis above (reference specific competitor names and numbers where genuinely known). Omit any gap category entirely if you have nothing real to say about it.
4. ACTIONABLE RECOMMENDATIONS
Short-Term (0-30 Days): Real, specific adjustments across whichever platforms have genuine findings above.
Mid-Term (30-90 Days): Real, specific strategy for closing gaps found above.
QUALITY RULES & FORMATTING
Format: Plain text only. No Markdown tables (use text-based columns) or complex formatting, EXCEPT for the one Executive Summary table described above, which should be a clean, evenly-aligned Markdown table.
Tone: Professional, analytical, and objective.
Accuracy: Cross-reference Parser and Tavily to ensure follower/subscriber counts are the most recent available for competitors; use the auto-fetched numbers exactly as given for the target.
No Data Policy: Outside the summary table, if a specific metric cannot be found, OMIT it entirely — never write "Data not available", "(not available)", "N/A", or any placeholder phrase. Inside the summary table only, use "—" per the table rule above.

EXECUTION STEPS

-Write the platform-by-platform analysis of the target using the real auto-fetched Instagram/Facebook/LinkedIn/YouTube numbers already given to you — no search needed for the target's own numbers.
-Search for each competitor's LinkedIn Company Page (and Instagram/Facebook/YouTube if easily found) to research their follower counts.
-Use Parser to scrape recent post timestamps to calculate "Posts per Month" where possible.
-Synthesize the "Activity Level" based on the consistency of those timestamps, only where found.
-Perform the Gap Analysis comparison across whichever platforms have real data.
-Generate the final plain-text report, omitting anything not genuinely known rather than writing a placeholder.
"""


def run_smm_gap_analysis(target_name: str, industry_name: str, competitor_names: str, smm_metrics: dict | None = None) -> str:
    smm_metrics = smm_metrics or {}

    # Omit a metric line entirely when the value is genuinely null (platform
    # not found) rather than feeding the LLM a "Data not available" string in
    # its own context — that phrase must never enter the model's input, or
    # it tends to echo it back in the output despite the prompt's ban on it.
    fields = [
        ("Instagram Followers", smm_metrics.get("instagram_followers")),
        ("Facebook Followers", smm_metrics.get("facebook_followers")),
        ("LinkedIn Followers", smm_metrics.get("linkedin_followers")),
        ("YouTube Subscribers", smm_metrics.get("youtube_subscribers")),
        ("LinkedIn Company Size", smm_metrics.get("linkedin_company_size")),
        ("LinkedIn Industry", smm_metrics.get("linkedin_industry")),
        ("Brand Tone", smm_metrics.get("brand_tone")),
    ]
    known_lines = [f"{label}: {value}" for label, value in fields if value is not None]
    auto_fetched_block = (
        "Auto-Fetched Target Metrics (ground truth for the target only, via profile scraping):\n"
        + "\n".join(known_lines)
        if known_lines
        else "Auto-Fetched Target Metrics: none of the four platforms returned real data for this target."
    )

    user_text = f"""Company Name :
{target_name}

The industry that the target works on:
{industry_name}

Competitor Names:
{competitor_names}

{auto_fetched_block}"""

    llm = get_llm(temperature=0.3)
    tools = [website_parser, tavily_search]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_MESSAGE),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, max_iterations=20, handle_parsing_errors=True)

    result = executor.invoke({"input": user_text})
    return _drop_all_blank_table_rows(result.get("output", ""))


def _drop_all_blank_table_rows(text: str) -> str:
    """The prompt asks the LLM to drop any competitor row where every
    platform cell is a dash (no real data at all), but this instruction
    isn't always reliably followed — so enforce it deterministically here:
    strip any markdown table data row whose non-name cells are ALL
    dash/empty, rather than trusting the model to have already done so."""
    lines = text.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        is_table_row = stripped.startswith("|") and stripped.endswith("|")
        is_separator_row = is_table_row and set(stripped.replace("|", "").replace("-", "").replace(":", "").strip()) == set()
        if is_table_row and not is_separator_row:
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) > 1:
                value_cells = cells[1:]
                dash_chars = {"", "—", "-", "–", "N/A", "n/a"}
                if value_cells and all(c in dash_chars for c in value_cells):
                    continue  # drop this row — no real data in any column
        out.append(line)
    return "\n".join(out)
