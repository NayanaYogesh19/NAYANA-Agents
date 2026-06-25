KEYWORD_MAPPINGS = {

    "allam pachadi": "ginger pickle",

    "allam": "ginger pickle",

    "gongura": "gongura pickle",

    "gongura pachadi": "gongura pickle",

    "tomato pachchadi": "tomato pickle",

    "tomato pachadi": "tomato pickle",

    "usiri": "amla pickle",

    "palla usiri": "amla pickle",

    "nimmakaya": "lemon pickle",

    "dabbakaya": "lemon pickle",

    "vellulli": "garlic pickle",

    "bellam avakaya": "sweet mango pickle",

    "avakaya": "mango pickle",

    "magaya": "mango pickle",

    "koora podi": "curry powder",

    "idli chutney": "idli chutney powder",

    "palli chutney": "peanut chutney powder",

    "tomato": "tomato pickle",

    "chintakaya": "tamarind pickle",

    "avakaya": "mango pickle"
}


def normalize_keyword(keyword):

    keyword = keyword.lower()

    for raw, normalized in KEYWORD_MAPPINGS.items():

        if raw in keyword:

            return normalized

    return keyword