def merge_data(keyword_data: dict, trends_data: dict) -> dict:
    """
    Equivalent to the n8n Merge node.

    Input 1:
        keyword_data

    Input 2:
        trends_data

    Output:
        Single merged dictionary
    """

    merged = {}

    # -----------------------------
    # Copy Keyword Extractor Output
    # -----------------------------
    merged.update(keyword_data)

    # -----------------------------
    # Copy Google Trends Output
    # -----------------------------
    merged.update(trends_data)

    return merged