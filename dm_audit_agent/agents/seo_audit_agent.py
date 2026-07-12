"""
seo_audit_agent.py — SEO audit narrative agent.

SE Ranking has been removed entirely. The user manually enters SEO metrics
(Health Score, Organic Traffic, Organic Keywords, Passed Checks, Crawled
Pages, Errors, Warnings, Notices) in the UI; this agent takes those numbers
as ground truth and combines them with PageSpeed Insights (still fetched
live) and Tavily/website-parser research to write a unique, company-specific
technical + content narrative — never a generic template.
"""

from __future__ import annotations

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agents.llm import get_llm
from tools.pagespeed_tool import run_pagespeed
from tools.tavily_tool import tavily_search
from tools.website_parser_tool import website_parser

SYSTEM_MESSAGE = """<role>
You are a specialized SEO Audit Analyst. You transform manually-provided SEO
metrics plus live PageSpeed data and web research into a sharp, unique,
company-specific narrative. You are NOT a generic template filler — every
sentence you write must reference this specific company's actual situation,
industry, and the exact numbers given to you.
</role>

<strict_rules>
- Use ONLY the exact numbers provided in the input — never invent or
  estimate a number that wasn't given to you.
- If a manually-entered metric is "Data not available", say exactly that for
  that metric — never guess a plausible-looking number.
- Every insight must be tied to the specific company/industry/competitors
  given in the input. Do not write interchangeable, generic filler that could
  apply to any company — the user has explicitly required unique, differentiated
  reasoning per company, not boilerplate.
- Use the tools (Tavily, website_parser) to ground claims about the
  company's actual site content, named competitors, and industry context.
- Plain text only, no Markdown.
</strict_rules>

<output_sections>
Write exactly these labeled sections, each 3-5 sentences of substantive,
specific analysis (not just repeating the numbers):

PERFORMANCE_OVERVIEW: current SEO health interpreted for this company's
  specific industry and business model.
TECHNICAL_GAPS: what the errors/warnings actually mean for this company's
  specific site and customers.
CONTENT_GAPS: what the crawled-pages/notices numbers mean for this specific
  company's content depth vs. what its industry demands.
VISIBILITY_CHALLENGES: how the traffic/keyword numbers compare to what this
  specific company should expect given its industry and named competitors.
</output_sections>
"""


def run_seo_audit(domain: str, industry: str, seo_metrics: dict, research_brief: str) -> str:
    desktop = run_pagespeed(domain, "desktop")
    mobile = run_pagespeed(domain, "mobile")

    def fmt(v):
        return "Data not available" if v is None else v

    user_text = f"""Company Domain: {domain}
Industry: {industry}

Manually Entered SEO Metrics (ground truth, never estimate beyond these):
Health Score: {fmt(seo_metrics.get('health_score'))}
Organic Traffic: {fmt(seo_metrics.get('organic_traffic'))}
Organic Keywords: {fmt(seo_metrics.get('organic_keywords'))}
Passed Checks: {fmt(seo_metrics.get('passed_checks'))}
Crawled Pages: {fmt(seo_metrics.get('crawled_pages'))}
Errors: {fmt(seo_metrics.get('errors'))}
Warnings: {fmt(seo_metrics.get('warnings'))}
Notices: {fmt(seo_metrics.get('notices'))}

Live PageSpeed — Desktop:
FCP: {desktop['FCP']} | LCP: {desktop['LCP']} | CLS: {desktop['CLS']} | INP: {desktop['INP']}

Live PageSpeed — Mobile:
FCP: {mobile['FCP']} | LCP: {mobile['LCP']} | CLS: {mobile['CLS']} | INP: {mobile['INP']}

Research Brief:
{research_brief}"""

    llm = get_llm(temperature=0.5)
    tools = [tavily_search, website_parser]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_MESSAGE),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, max_iterations=10, handle_parsing_errors=True)

    result = executor.invoke({"input": user_text})
    return result.get("output", "")
