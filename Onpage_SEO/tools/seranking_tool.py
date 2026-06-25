import os

from dotenv import load_dotenv

load_dotenv()


async def get_keyword_data(keyword):

    return {

        "keyword": keyword,

        "volume": "",

        "competition": "",

        "cpc": "",

        "keyword_difficulty": "",

        "intent": ""
    }


async def get_keyword_rank(
    keyword,
    domain
):

    return ""