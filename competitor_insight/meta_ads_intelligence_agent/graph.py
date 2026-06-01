from typing import TypedDict, List, Dict, Any

from langgraph.graph import StateGraph, END

from scrapers.meta_scraper import AdsLibraryBrowser
from llm_extract import analyze_ads


class GraphState(TypedDict):

    business_name: str

    country: str

    category: str

    max_ads: int

    raw_ads: List[Dict[str, Any]]

    final_output: dict

    errors: List[str]


browser = None


# ---------------------------------------------------
# STEP 1 - Open Browser ONLY
# ---------------------------------------------------

def open_library_node(state: GraphState):

    global browser

    browser = AdsLibraryBrowser(
        headless=False
    )

    browser.open()

    browser.accept_cookies_if_present()

    print(
        "Meta Ads Library opened successfully."
    )

    return state


# ---------------------------------------------------
# STEP 2 - Collect Ads ONLY
# ---------------------------------------------------

def collect_ads_node(state: GraphState):

    raw_ads = browser.collect_ads(
        max_ads=state["max_ads"]
    )

    print(
        f"Collected {len(raw_ads)} ads"
    )

    return {
        **state,
        "raw_ads": raw_ads
    }


# ---------------------------------------------------
# STEP 3 - Analyze Ads
# ---------------------------------------------------

def summarize_node(state: GraphState):

    result = analyze_ads(

        business_name=state["business_name"],

        country=state["country"],

        category=state["category"],

        raw_ads=state["raw_ads"]
    )

    browser.close()

    return {

        **state,

        "final_output": result.model_dump()
    }


# ---------------------------------------------------
# Build Graph
# ---------------------------------------------------

graph = StateGraph(GraphState)

graph.add_node(
    "open_library",
    open_library_node
)

graph.add_node(
    "collect_ads",
    collect_ads_node
)

graph.add_node(
    "summarize",
    summarize_node
)

graph.set_entry_point(
    "open_library"
)

graph.add_edge(
    "open_library",
    "collect_ads"
)

graph.add_edge(
    "collect_ads",
    "summarize"
)

graph.add_edge(
    "summarize",
    END
)

app = graph.compile()