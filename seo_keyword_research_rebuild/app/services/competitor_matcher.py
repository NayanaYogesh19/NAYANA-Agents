def match_competitor_products(

    metrics,

    competitor_products
):

    results = []

    for metric in metrics:

        keyword_lower = metric[
            "keyword"
        ].lower()

        matched_products = []

        matched_urls = []

        for product in competitor_products:

            product_name = product[
                "product"
            ].lower()

            if any(

                word in product_name

                for word in keyword_lower.split()
            ):

                matched_products.append(
                    product["product"]
                )

                matched_urls.append(
                    product["url"]
                )

        metric["competitor_usage"] = ", ".join(
            list(set(matched_products))
        )

        metric["competitor_product_url"] = ", ".join(
            list(set(matched_urls))
        )

        results.append(metric)

    return results