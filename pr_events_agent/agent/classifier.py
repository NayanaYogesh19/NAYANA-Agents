"""Uses LangChain's ChatOpenAI (pointed at OpenRouter) with structured
output to turn a raw candidate page into a clean ReportItem — or reject
it if it doesn't actually belong in the report.

This is the only place an LLM is used. Discovery, fetching, date
extraction, and dedup are all deterministic code on purpose: an LLM
deciding "is this page relevant" from a URL alone is exactly the kind
of step that produces confident-sounding wrong answers, so we only
hand it a page once we already have clean extracted text + a URL to
ground the summary in.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Optional
from urllib.parse import urlparse

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config import settings
from agent.models import Category, CandidatePage, Confidence, ReportItem

logger = logging.getLogger(__name__)

# Maps a word found in the page's own URL path to the category the SITE
# ITSELF is telling us this page belongs to (e.g. a URL segment like
# "/press-releases/" or "/newsroom/events/"). This is real information
# published by the site's own taxonomy/navigation structure, not a
# guess — passed to the LLM as a hint it can still override if the
# actual page content clearly disagrees (e.g. a mis-filed page).
_SECTION_HINTS: tuple[tuple[re.Pattern, Category], ...] = (
    (re.compile(r"press.?releases?|/news/|newsroom", re.I), "press_release"),
    (re.compile(r"webinars?", re.I), "webinar"),
    (re.compile(r"events?|exhibitions?|conferences?|tradeshows?", re.I), "event"),
    (re.compile(r"awards?|recognitions?", re.I), "award"),
)


def _section_hint(url: str) -> Optional[Category]:
    """Best-effort guess at the site's own section for this URL, based
    on path segments — e.g. "/newsroom/press-releases/post/x" hints
    press_release, "/newsroom/events/post/y" hints event. Checks the
    LAST matching segment so a more specific section (closer to the
    actual page) wins over a more general parent one.
    """
    segments = [s for s in urlparse(url).path.split("/") if s]
    hint: Optional[Category] = None
    for segment in segments:
        for pattern, category in _SECTION_HINTS:
            if pattern.search(segment):
                hint = category
                break
    return hint


class _Verdict(BaseModel):
    """What we ask the model to return. `relevant=False` lets the model
    reject noise (nav pages, unrelated articles, off-topic search hits)
    instead of forcing a category on everything.
    """

    is_single_story: bool = Field(
        description="False if this page is an index/listing/archive page that "
                     "aggregates MULTIPLE separate stories, headlines, or dated "
                     "entries (e.g. a newsroom homepage, a 'Press Releases' list, "
                     "a tag/category page, a blog roll) rather than being ABOUT one "
                     "single announcement itself. True only if the page's main "
                     "content is one specific story."
    )
    relevant: bool = Field(description="True only if this page is genuinely a press "
                                        "release, webinar, event/exhibition mention, "
                                        "or award/win for the target company")
    category: Optional[Category] = Field(
        default=None, description="Required if relevant=True"
    )
    title: Optional[str] = Field(
        default=None, description="Short headline, report-table style, one sentence"
    )


_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You classify a single web page for a monthly competitor PR/events report. "
            "The report has exactly 4 categories: press_release, webinar, event, award. "
            "The target company is '{company}'. The reporting window is {start} to {end}. "
            "\n\n"
            "First decide is_single_story: many pages on a newsroom/blog section are "
            "actually LISTING pages that aggregate several different stories with "
            "different dates (e.g. a 'Press Releases' index, a newsroom homepage, a "
            "tag or category page) — these must be marked is_single_story=False even "
            "if the first headline on the page happens to look relevant. The decisive "
            "test is the body text: if it reads as a sequence of several different "
            "headlines/teasers, each about a different specific topic, it is a listing "
            "page. Only if the body text is entirely about ONE specific announcement, "
            "post, or event — one continuous narrative — is is_single_story=True. "
            "\n\n"
            "Only mark relevant=True if is_single_story=True AND it is genuinely about "
            "{company} and fits one of the 4 categories. Ignore generic navigation, "
            "unrelated companies, and opinion pieces that merely mention the company "
            "in passing. "
            "\n\n"
            "Category hint: {section_hint}. This comes from the site's own URL "
            "structure (its own navigation/taxonomy), so treat it as a strong default "
            "— but override it if the page's actual content clearly belongs to a "
            "different one of the 4 categories instead. "
            "Write the title the way a terse business report would: factual, one sentence, "
            "no marketing language, no emoji.",
        ),
        (
            "human",
            "URL: {url}\nPage title: {page_title}\nExtracted text (truncated):\n{text}",
        ),
    ]
)


def _build_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        temperature=0,
        max_tokens=400,
    )


def classify(
    candidate: CandidatePage, company_name: str, start: date, end: date
) -> Optional[ReportItem]:
    """Returns a ReportItem, or None if the model judged it irrelevant
    or the call failed.
    """
    model = _build_model().with_structured_output(_Verdict)
    chain = _PROMPT | model

    hint = _section_hint(candidate.url)
    hint_text = (
        f"the site's own URL structure suggests this is a '{hint}' page"
        if hint else "the URL gives no clear signal — decide from content alone"
    )

    try:
        verdict: _Verdict = chain.invoke(
            {
                "company": company_name,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "url": candidate.url,
                "page_title": candidate.title or "(none)",
                "text": candidate.text or "(no text extracted)",
                "section_hint": hint_text,
            }
        )
    except Exception as exc:
        logger.warning("Classification failed for %s: %s", candidate.url, exc)
        return None

    if not verdict.is_single_story:
        logger.debug("Rejecting %s: looks like a listing/index page, not a single story", candidate.url)
        return None

    if not verdict.relevant or not verdict.category:
        return None

    # "verified" means the date is trustworthy: a real on-page publish
    # date, not a sitemap lastmod fallback and not a blank guess. Being
    # from the company's own site says nothing about whether we found
    # a real date on the specific page — those are independent facts.
    confidence: Confidence = "verified" if candidate.date_is_exact else "unverified"

    return ReportItem(
        category=verdict.category,
        title=verdict.title or (candidate.title or candidate.url),
        url=candidate.url,
        published_date=candidate.published_date,
        source_type=candidate.source_type,
        confidence=confidence,
    )
