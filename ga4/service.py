from googleapiclient.discovery import build

from google.analytics.data_v1beta import (
    BetaAnalyticsDataClient
)

from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)


def list_ga4_accounts(creds):

    service = build(
        "analyticsadmin",
        "v1beta",
        credentials=creds
    )

    accounts = service.accounts().list().execute()

    return accounts.get(
        "accounts",
        []
    )


def list_ga4_properties(
    creds,
    account_name
):

    service = build(
        "analyticsadmin",
        "v1beta",
        credentials=creds
    )

    props = service.properties().list(
        filter=f"parent:{account_name}"
    ).execute()

    return props.get(
        "properties",
        []
    )


def get_ga4_metrics(

    creds,

    property_id,

    dimensions,

    metrics,

    start_date,

    end_date,

    limit
):

    client = BetaAnalyticsDataClient(
        credentials=creds
    )

    dimension_objects = [

        Dimension(name=d)

        for d in dimensions
    ]

    metric_objects = [

        Metric(name=m)

        for m in metrics
    ]

    request = RunReportRequest(

        property=f"properties/{property_id}",

        dimensions=dimension_objects,

        metrics=metric_objects,

        date_ranges=[
            DateRange(
                start_date=start_date,
                end_date=end_date
            )
        ],

        limit=limit
    )

    response = client.run_report(
        request
    )

    data = []

    for row in response.rows:

        row_data = {}

        for i, dim in enumerate(dimensions):

            row_data[dim] = (
                row.dimension_values[i].value
            )

        for i, met in enumerate(metrics):

            row_data[met] = (
                row.metric_values[i].value
            )

        data.append(row_data)

    return data