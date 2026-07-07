"""Shared HTTP GET helper with a fallback for sites that serve an
incomplete TLS certificate chain (missing intermediate cert) — a real,
fairly common server misconfiguration that isn't specific to any one
company. Browsers often still show a green padlock because they cache
or pre-trust the missing intermediate; Python's strict chain-building
does not, so a plain `requests.get` silently fails for that class of
site. This retries once, unverified, only after a verified attempt
fails with an SSLError — and always logs it clearly, since it does
mean that response's authenticity wasn't fully confirmed.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
import urllib3

from config import settings

logger = logging.getLogger(__name__)

# We only ever disable verification after our own explicit SSLError
# retry below, and we already log our own clear warning when that
# happens — this just suppresses urllib3's duplicate warning for it.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Once a domain is known to need the unverified fallback, skip straight
# to it for every later call instead of repeating a failing verified
# attempt on every single URL on that domain.
_no_ssl_domains: set[str] = set()


def get(url: str, **kwargs) -> requests.Response | None:
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", settings.USER_AGENT)
    timeout = kwargs.pop("timeout", settings.REQUEST_TIMEOUT)
    domain = urlparse(url).netloc

    if domain in _no_ssl_domains:
        try:
            return requests.get(url, headers=headers, timeout=timeout, verify=False, **kwargs)
        except requests.RequestException as exc:
            logger.debug("GET failed for %s: %s", url, exc)
            return None

    try:
        return requests.get(url, headers=headers, timeout=timeout, **kwargs)
    except requests.exceptions.SSLError:
        logger.warning(
            "TLS certificate chain for %s could not be verified; retrying without "
            "verification (the site's server appears to be missing an intermediate "
            "certificate). Will skip straight to this for the rest of %s.", url, domain,
        )
        try:
            resp = requests.get(url, headers=headers, timeout=timeout, verify=False, **kwargs)
            _no_ssl_domains.add(domain)
            return resp
        except requests.RequestException as exc:
            logger.debug("GET (unverified retry) failed for %s: %s", url, exc)
            return None
    except requests.RequestException as exc:
        logger.debug("GET failed for %s: %s", url, exc)
        return None
