"""
keyword_research_agent.py — Tavily-only keyword/competitor research agent.

SE Ranking has been removed entirely from this project; all SEO metrics
(health score, organic traffic, organic keywords, etc.) are now entered
manually by the user in the UI. This agent instead uses Tavily web search and
the website parser to research the domain's actual site content, competitors
and commercial search intent, feeding that context into the later content
generation stage so recommendations stay grounded and company-specific
instead of generic.
"""

from __future__ import annotations

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agents.llm import get_llm
from tools.tavily_tool import tavily_search
from tools.website_parser_tool import website_parser

SYSTEM_MESSAGE = """# ROLE
Senior SEO/Market Research Analyst. Given a company's domain and industry,
research its actual site content, positioning, and market context using the
tools available, and produce a concise research brief that later stages will
use to generate a unique, company-specific digital audit.

# TOOLS
- website_parser: extract nav, headings, hero copy, product/service names.
- tavily_search: research competitors, industry trends, market positioning,
  and any public information about the company.

# WORKFLOW
1. Parse the target website to learn its actual products/services, tone, and
   navigation structure.
2. Use Tavily to identify 2-4 real named competitors in the same industry and
   general market trends relevant to this specific company.
3. Identify commercial/transactional search intent themes relevant to this
   business (not generic SEO advice).

# OUTPUT (plain text)
Company_Overview: <2-3 sentences on what this specific company actually does,
  grounded in the parsed site content — never generic industry boilerplate>
Named_Competitors: <comma-separated list of 2-4 real competitor names/domains>
Market_Context: <2-3 sentences of real, current context about this industry
  and this company's position in it>
Commercial_Keyword_Themes: <5-10 phrases specific to this company's actual
  offerings>

# RULES
- Never invent facts you could not have found via the tools. If a tool fails
  or returns nothing useful, say so plainly rather than fabricating detail.
- Keep the brief tight — this feeds into later prompts, it is not the final
  report.
"""


def run_keyword_research(domain: str, industry: str) -> str:
    llm = get_llm(temperature=0.3)
    tools = [tavily_search, website_parser]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_MESSAGE),
            ("human", "Domain: {domain}\nIndustry: {industry}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, max_iterations=12, handle_parsing_errors=True)

    result = executor.invoke({"domain": domain, "industry": industry})
    return result.get("output", "")
