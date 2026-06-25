
from urllib.parse import urlparse

# =========================================
# INVALID URL PARTS
# =========================================

INVALID_PATTERNS = [

    ".xml",

    "/tag/",
    "/author/",
    "/page/",
    "/privacy",
    "/refund",
    "/terms",
    "/policy",
    "/checkout",
    "/cart",
    "/account",
    "/track",
    "/login",
    "/register"
]

# =========================================
# INVALID SLUGS
# =========================================

INVALID_SLUGS = [

    "home",
    "shop",
    "blog",
    "contact",
    "about"
]

# =========================================
# VALID PRODUCT URL
# =========================================

def is_product_url(url):

    url_lower = url.lower()

    # =====================================
    # REJECT INVALID PATTERNS
    # =====================================

    for pattern in INVALID_PATTERNS:

        if pattern in url_lower:
            return False

    # =====================================
    # GET SLUG
    # =====================================

    slug = urlparse(url).path.split("/")[-1]

    slug = slug.strip().lower()

    # =====================================
    # EMPTY SLUG
    # =====================================

    if not slug:
        return False

    # =====================================
    # INVALID SLUG
    # =====================================

    if slug in INVALID_SLUGS:
        return False

    # =====================================
    # SHORT SLUG
    # =====================================

    if len(slug) < 5:
        return False

    return True

# =========================================
# EXTRACT PRODUCT NAME
# =========================================

def extract_product_name(url):

    slug = urlparse(url).path.split("/")[-1]

    slug = slug.replace("-", " ")

    slug = slug.replace("_", " ")

    return slug.title().strip()

# =========================================
# CLASSIFY PRODUCT
# =========================================

def classify_product(url):

    if not is_product_url(url):
        return None

    product_name = extract_product_name(
        url
    )

    return {

        "product":
        product_name,

        "url":
        url
    }

