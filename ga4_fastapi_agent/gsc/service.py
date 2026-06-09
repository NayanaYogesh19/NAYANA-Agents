from urllib import response

from ga4 import service
from googleapiclient.discovery import build
import requests
import os
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import json



def get_search_console_data(
    creds,
    site_url,
    dimensions,
    start_date,
    end_date,
    row_limit
):

    service = build(
        "searchconsole",
        "v1",
        credentials=creds
    )

    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": row_limit
    }

    if not site_url.startswith("sc-domain:"):
        site_url = f"sc-domain:{site_url}"

    response = service.searchanalytics().query(
    siteUrl=site_url,
    body=request
).execute()

    rows = []

    for row in response.get("rows", []):

        item = {}

        for i, dim in enumerate(dimensions):
            item[dim] = row["keys"][i]

        item["clicks"] = int(row.get("clicks", 0) or 0)
        item["impressions"] = int(row.get("impressions", 0) or 0)

        ctr = row.get("ctr", 0)
        position = row.get("position", 0)

        if isinstance(ctr, (int, float)):
            item["ctr"] = f"{round(ctr * 100)}%"
        else:
            item["ctr"] = ctr

        if isinstance(position, (int, float)):
            item["position"] = round(position)
        else:
            item["position"] = position

        rows.append(item)

    return rows

def inspect_url(
    creds,
    site_url,
    page_url
):

    service = build(
        "searchconsole",
        "v1",
        credentials=creds
    )

    if not site_url.startswith(
        "sc-domain:"
    ):
        site_url = (
            f"sc-domain:{site_url}"
        )

    request = {
        "inspectionUrl": page_url,
        "siteUrl": site_url
    }

    response = service.urlInspection().index().inspect(
        body=request
    ).execute()

    return response

def get_pages_report(
    creds,
    site_url
):

    service = build(
        "searchconsole",
        "v1",
        credentials=creds
    )

    if not site_url.startswith(
        "sc-domain:"
    ):
        site_url = (
            f"sc-domain:{site_url}"
        )

    sitemap_response = (
        service.sitemaps().list(
            siteUrl=site_url
        ).execute()
    )

    sitemaps = sitemap_response.get(
        "sitemap",
        []
    )

    indexed_pages = 0
    not_indexed_pages = 0

    for sitemap in sitemaps:

        sitemap_url = sitemap["path"]

        try:

            xml_text = requests.get(
                sitemap_url
            ).text

            root = ET.fromstring(
                xml_text
            )

            namespace = {
                "ns":
                "http://www.sitemaps.org/schemas/sitemap/0.9"
            }

            urls = root.findall(
                ".//ns:loc",
                namespace
            )

            for url_tag in urls:

                page_url = (
                    url_tag.text
                )

                try:

                    inspection = (
                        inspect_url(
                            creds,
                            site_url,
                            page_url
                        )
                    )

                    status = (
                        inspection[
                            "inspectionResult"
                        ][
                            "indexStatusResult"
                        ][
                            "coverageState"
                        ]
                    )

                    if (
                        "indexed"
                        in status.lower()
                    ):

                        indexed_pages += 1

                    else:

                        not_indexed_pages += 1

                except Exception:

                    not_indexed_pages += 1

        except Exception:

            continue

    total = (
        indexed_pages +
        not_indexed_pages
    )

    coverage = 0

    if total > 0:

        coverage = round(
            (
                indexed_pages /
                total
            ) * 100,
            2
        )

    return {
        "indexed_pages":
            indexed_pages,

        "not_indexed_pages":
            not_indexed_pages,

        "index_coverage":
            coverage
    }

def get_videos_report(
    creds,
    site_url
):

    service = build(
        "searchconsole",
        "v1",
        credentials=creds
    )

    if not site_url.startswith("sc-domain:"):
        site_url = f"sc-domain:{site_url}"

    response = service.sitemaps().list(
        siteUrl=site_url
    ).execute()

    sitemaps = response.get(
        "sitemap",
        []
    )

    pages_with_video = 0
    pages_without_video = 0

    for sitemap in sitemaps:

        sitemap_url = sitemap["path"]

        try:

            xml_text = requests.get(
                sitemap_url,
                timeout=20
            ).text

            root = ET.fromstring(
                xml_text
            )

            namespace = {
                "ns":
                "http://www.sitemaps.org/schemas/sitemap/0.9"
            }

            urls = root.findall(
                ".//ns:loc",
                namespace
            )

            for url_tag in urls:

                page_url = url_tag.text

                try:

                    page = requests.get(
                        page_url,
                        timeout=20
                    )

                    soup = BeautifulSoup(
                        page.text,
                        "html.parser"
                    )

                    has_video = False

                    # Check HTML video tag
                    if soup.find("video"):
                        has_video = True

                    # Check VideoObject schema
                    for script in soup.find_all(
                        "script",
                        type="application/ld+json"
                    ):

                        try:

                            data = json.loads(
                                script.string
                            )

                            text = json.dumps(
                                data
                            )

                            if (
                                "VideoObject"
                                in text
                            ):

                                has_video = True

                        except Exception:
                            continue

                    if has_video:

                        pages_with_video += 1

                    else:

                        pages_without_video += 1

                except Exception:

                    pages_without_video += 1

        except Exception as e:

            print(
                f"Error reading {sitemap_url}: {e}"
            )

    total_pages = (
        pages_with_video +
        pages_without_video
    )

    coverage = 0

    if total_pages > 0:

        coverage = round(
            (
                pages_with_video /
                total_pages
            ) * 100,
            2
        )

    return {
        "pages_with_video":
            pages_with_video,

        "pages_without_video":
            pages_without_video,

        "video_coverage":
            coverage
    }


def get_sitemaps(
    creds,
    site_url
):

    service = build(
        "searchconsole",
        "v1",
        credentials=creds
    )

    if not site_url.startswith("sc-domain:"):
        site_url = f"sc-domain:{site_url}"

    response = service.sitemaps().list(
        siteUrl=site_url
    ).execute()

    return response.get("sitemap", [])


def get_core_web_vitals(url):

    api_key = os.getenv("PAGESPEED_API_KEY")

    endpoint = (
        "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    )

    response = requests.get(
        endpoint,
        params={
            "url": url,
            "key": api_key
        }
    )

    data = response.json()

    if "error" in data:
        return {
            "error": data["error"]["message"]
        }

    audits = data["lighthouseResult"]["audits"]

    return {
        "largest_contentful_paint":
            audits["largest-contentful-paint"]["displayValue"],

        "cumulative_layout_shift":
            audits["cumulative-layout-shift"]["displayValue"],

        "speed_index":
            audits["speed-index"]["displayValue"],

        "total_blocking_time":
            audits["total-blocking-time"]["displayValue"]
    }

def get_https_status(url):

    return {
        "url": url,
        "https_enabled": url.startswith(
            "https://"
        )
    }

def get_breadcrumbs(url):

    response = requests.get(url)

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    breadcrumbs = []

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):

        try:

            data = json.loads(
                script.string
            )

            if "@graph" in data:

                for item in data["@graph"]:

                    if item.get("@type") == "BreadcrumbList":

                        for crumb in item.get(
                            "itemListElement",
                            []
                        ):

                            breadcrumbs.append({
                                "position":
                                    crumb.get(
                                        "position"
                                    ),
                                "name":
                                    crumb.get(
                                        "name"
                                    )
                            })

        except Exception:
            continue

    return breadcrumbs

def get_https_report(
    creds,
    site_url
):

    service = build(
        "searchconsole",
        "v1",
        credentials=creds
    )

    if not site_url.startswith("sc-domain:"):
        site_url = f"sc-domain:{site_url}"

    response = service.sitemaps().list(
        siteUrl=site_url
    ).execute()

    sitemaps = response.get("sitemap", [])

    https_urls = 0
    non_https_urls = 0

    for sitemap in sitemaps:

        sitemap_url = sitemap["path"]

        try:

            xml_text = requests.get(
                sitemap_url,
                timeout=20
            ).text

            root = ET.fromstring(xml_text)

            namespace = {
                "ns": "http://www.sitemaps.org/schemas/sitemap/0.9"
            }

            urls = root.findall(
                ".//ns:loc",
                namespace
            )

            for url_tag in urls:

                page_url = url_tag.text

                if page_url.startswith(
                    "https://"
                ):
                    https_urls += 1

                else:
                    non_https_urls += 1

        except Exception as e:

            print(
                f"Error reading {sitemap_url}: {e}"
            )

    total_urls = (
        https_urls +
        non_https_urls
    )

    percentage = 0

    if total_urls > 0:

        percentage = round(
            (https_urls / total_urls) * 100,
            2
        )

    return {
        "total_urls": total_urls,
        "https_urls": https_urls,
        "non_https_urls": non_https_urls,
        "https_percentage": percentage
    }
def get_breadcrumbs_report(
    creds,
    site_url
):

    service = build(
        "searchconsole",
        "v1",
        credentials=creds
    )

    if not site_url.startswith("sc-domain:"):
        site_url = f"sc-domain:{site_url}"

    response = service.sitemaps().list(
        siteUrl=site_url
    ).execute()

    sitemaps = response.get("sitemap", [])

    valid_pages = 0
    invalid_pages = 0

    for sitemap in sitemaps:

        sitemap_url = sitemap["path"]

        try:

            xml_text = requests.get(
                sitemap_url,
                timeout=20
            ).text

            root = ET.fromstring(xml_text)

            namespace = {
                "ns": "http://www.sitemaps.org/schemas/sitemap/0.9"
            }

            urls = root.findall(
                ".//ns:loc",
                namespace
            )

            for url_tag in urls:

                page_url = url_tag.text

                breadcrumbs = get_breadcrumbs(
                    page_url
                )

                if breadcrumbs:
                    valid_pages += 1
                else:
                    invalid_pages += 1

        except Exception as e:

            print(
                f"Error reading {sitemap_url}: {e}"
            )

    total_pages = (
        valid_pages +
        invalid_pages
    )

    coverage = 0

    if total_pages > 0:

        coverage = round(
            (valid_pages / total_pages) * 100,
            2
        )

    return {
        "valid_pages": valid_pages,
        "invalid_pages": invalid_pages,
        "breadcrumb_coverage": coverage
    }