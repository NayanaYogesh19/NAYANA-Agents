import re


STOPWORDS = {

    "buy",
    "online",
    "best",
    "quality",
    "authentic",
    "homemade",
    "foods",
    "food",
    "store",
    "india",
    "jandhyala",
    "order"
}


async def extract_keywords(title, url):

    title = title.lower()

    # REMOVE SPECIAL CHARACTERS

    title = re.sub(

        r"[^a-zA-Z0-9\s]",

        " ",

        title
    )

    words = title.split()

    # REMOVE STOPWORDS

    filtered = [

        word

        for word in words

        if word not in STOPWORDS
    ]

    # PRODUCT PAGE LOGIC

    if "/product/" in url:

        # TRY 2-WORD PHRASE

        keyword = " ".join(
            filtered[:2]
        )

    else:

        keyword = " ".join(
            filtered[:3]
        )

    keyword = keyword.strip()

    # CLEAN DOUBLE WORDS

    parts = []

    for word in keyword.split():

        if word not in parts:

            parts.append(word)

    keyword = " ".join(parts)

    return {

        "primary": [keyword]
    }