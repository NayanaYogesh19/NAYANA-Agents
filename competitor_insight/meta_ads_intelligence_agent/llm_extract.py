import os

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from schemas import AdLibraryResult


load_dotenv()


# ---------------------------------------------------
# OPENROUTER CONFIG
# ---------------------------------------------------

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)


llm = ChatOpenAI(

    model="openai/gpt-4o-mini",

    temperature=0,

    api_key=OPENROUTER_API_KEY,

    base_url="https://openrouter.ai/api/v1"
)


# ---------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------

SYSTEM_PROMPT = '''
You are a Meta Ads Library intelligence analyst.

Your job:
1. Analyze raw ad card text.
2. Extract structured ad insights.
3. Detect recurring messaging themes.
4. Infer positioning conservatively.
5. Do NOT invent missing details.
6. Return structured output only.
'''


# ---------------------------------------------------
# PROMPT TEMPLATE
# ---------------------------------------------------

prompt = ChatPromptTemplate.from_messages([

    ("system", SYSTEM_PROMPT),

    (
        "human",

        '''
        Business Name: {business_name}

        Country: {country}

        Category: {category}

        Raw Ads:
        {raw_ads}
        '''
    )
])


# ---------------------------------------------------
# STRUCTURED OUTPUT
# ---------------------------------------------------

structured_llm = llm.with_structured_output(
    AdLibraryResult
)


chain = prompt | structured_llm


# ---------------------------------------------------
# MAIN ANALYSIS FUNCTION
# ---------------------------------------------------

def analyze_ads(

    business_name: str,

    country: str,

    category: str,

    raw_ads: list
):

    result = chain.invoke({

        "business_name": business_name,

        "country": country,

        "category": category,

        "raw_ads": raw_ads
    })

    return result