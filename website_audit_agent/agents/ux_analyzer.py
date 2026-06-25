"""
ux_analyzer.py — UX, accessibility, trust signal, and CTA analysis.

Uses Playwright (headless Chromium) for visual checks and screenshots.
Falls back gracefully to requests-based checks if Playwright is unavailable.
"""

from __future__ import annotations

import base64
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config import Config

logger = logging.getLogger(__name__)

# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class UXCheck:
    """A single UX / accessibility check result."""
    name: str
    status: str       # "pass" | "fail" | "warning" | "info"
    detail: str = ""


@dataclass
class UXResult:
    """All UX findings for one domain."""
    domain: str
    desktop_screenshot_path: Optional[str] = None
    mobile_screenshot_path: Optional[str] = None
    desktop_screenshot_b64: str = ""
    mobile_screenshot_b64: str = ""
    checks: List[UXCheck] = field(default_factory=list)
    trust_signals_present: List[str] = field(default_factory=list)
    trust_signals_missing: List[str] = field(default_factory=list)
    cta_count: int = 0
    cta_above_fold: bool = False
    playwright_available: bool = False


# ── Helpers ───────────────────────────────────────────────────────────────────

_CTA_KEYWORDS = re.compile(
    r'\b(get|start|try|buy|book|contact|learn|download|sign.?up|request|subscribe|register|order|shop|explore)\b',
    re.I,
)

_TRUST_SIGNALS = {
    "testimonials": re.compile(r'testimonial|review|rating|stars?', re.I),
    "phone_in_header": re.compile(r'tel:|(\+?1?\s*\(?\d{3}\)?\s*[\-.\s]?\d{3}[\-.\s]?\d{4})', re.I),
    "address_in_footer": re.compile(r'\d{1,5}\s+\w+\s+(st|street|ave|avenue|blvd|road|dr|drive|lane|way)\b', re.I),
    "privacy_policy": re.compile(r'privacy.?policy', re.I),
    "terms": re.compile(r'terms.?(of.?(service|use))?', re.I),
    "ssl_badge": re.compile(r'secure|ssl|https|padlock', re.I),
    "certification_badge": re.compile(r'certified|accredited|award|iso\s*\d+', re.I),
}

_ARIA_LANDMARKS = ["main", "nav", "footer", "header", "banner", "contentinfo", "navigation"]


def _encode_image(path: str) -> str:
    """Read an image file and return base64-encoded string."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def _check_trust_signals(html: str) -> tuple[List[str], List[str]]:
    """Return (present_signals, missing_signals) from homepage HTML."""
    soup = BeautifulSoup(html, "lxml")
    # Separate header and footer sections for context-aware checks
    header = str(soup.find("header") or "")
    footer = str(soup.find("footer") or "")
    full_text = soup.get_text(" ", strip=True)

    present, missing = [], []
    for name, pattern in _TRUST_SIGNALS.items():
        if name == "phone_in_header":
            target = header or full_text
        elif name == "address_in_footer":
            target = footer or full_text
        else:
            target = full_text

        if pattern.search(target):
            present.append(name)
        else:
            missing.append(name)

    return present, missing


def _check_aria_landmarks(html: str) -> UXCheck:
    """Detect ARIA landmark roles or semantic HTML5 elements."""
    soup = BeautifulSoup(html, "lxml")
    found = set()

    # Semantic HTML5
    for tag_name in ("main", "nav", "footer", "header"):
        if soup.find(tag_name):
            found.add(tag_name)

    # role attributes
    for tag in soup.find_all(role=True):
        role = tag.get("role", "").lower()
        if role in _ARIA_LANDMARKS:
            found.add(role)

    if len(found) >= 3:
        return UXCheck(
            name="ARIA Landmark Roles",
            status="pass",
            detail=f"Landmarks found: {', '.join(sorted(found))}",
        )
    return UXCheck(
        name="ARIA Landmark Roles",
        status="fail",
        detail=f"Only {len(found)} landmark(s) found: {', '.join(sorted(found))}",
    )


def _check_skip_nav(html: str) -> UXCheck:
    """Look for a skip navigation link."""
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        href = a["href"]
        if "skip" in text and href.startswith("#"):
            return UXCheck(name="Skip Navigation Link", status="pass", detail=f'Found: "{a.get_text(strip=True)}"')
    return UXCheck(name="Skip Navigation Link", status="fail", detail="No skip navigation link found")


def _check_form_labels(html: str) -> UXCheck:
    """Check that all form inputs have associated labels."""
    soup = BeautifulSoup(html, "lxml")
    inputs = soup.find_all("input", {"type": lambda t: t not in ("hidden", "submit", "button", "reset", None)})
    unlabelled = 0
    for inp in inputs:
        inp_id = inp.get("id")
        if inp_id and soup.find("label", {"for": inp_id}):
            continue
        if inp.get("aria-label") or inp.get("aria-labelledby") or inp.get("placeholder"):
            continue
        unlabelled += 1

    if unlabelled == 0:
        return UXCheck(name="Form Labels", status="pass", detail="All inputs have labels or aria-label")
    return UXCheck(
        name="Form Labels",
        status="fail",
        detail=f"{unlabelled} input(s) missing associated labels",
    )


def _check_all_images_alt(html: str) -> UXCheck:
    """Check that all images have non-empty alt text."""
    soup = BeautifulSoup(html, "lxml")
    imgs = soup.find_all("img")
    missing = [img.get("src", "") for img in imgs if not img.get("alt", "").strip()]
    if not missing:
        return UXCheck(name="Images Alt Text", status="pass", detail="All images have alt text")
    return UXCheck(
        name="Images Alt Text",
        status="fail",
        detail=f"{len(missing)} image(s) missing alt text: {missing[:3]}",
    )


def _check_nav_present(html: str) -> UXCheck:
    """Check for navigation menu in header or nav element."""
    soup = BeautifulSoup(html, "lxml")
    nav = soup.find("nav") or soup.find("header")
    if nav and nav.find_all("a"):
        return UXCheck(name="Navigation Menu Present", status="pass", detail="Nav menu found")
    return UXCheck(name="Navigation Menu Present", status="fail", detail="No navigation menu detected")


def _check_footer_contact(html: str) -> UXCheck:
    """Check footer for contact information."""
    soup = BeautifulSoup(html, "lxml")
    footer = soup.find("footer")
    if not footer:
        return UXCheck(name="Footer Contact Info", status="warning", detail="No <footer> element found")
    text = footer.get_text(" ", strip=True)
    has_email = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    has_phone = re.search(r'\+?[\d\s\-().]{7,}', text)
    if has_email or has_phone:
        return UXCheck(name="Footer Contact Info", status="pass", detail="Contact info found in footer")
    return UXCheck(name="Footer Contact Info", status="warning", detail="No email or phone in footer")


def _analyse_cta(html: str) -> tuple[int, bool]:
    """Return (total_cta_count, cta_above_fold_flag)."""
    soup = BeautifulSoup(html, "lxml")
    cta_elements = soup.find_all(["button", "a"], class_=re.compile(r'btn|cta|button', re.I))
    # Also look by text content
    for tag in soup.find_all(["button", "a"]):
        text = tag.get_text(strip=True)
        if _CTA_KEYWORDS.search(text):
            if tag not in cta_elements:
                cta_elements.append(tag)

    count = len(cta_elements)
    # Heuristic for "above fold": element appears in the first ~20% of HTML
    above_fold = False
    html_lower = html.lower()
    for el in cta_elements[:5]:
        el_str = str(el).lower()
        pos = html_lower.find(el_str[:50]) if len(el_str) >= 50 else html_lower.find(el_str)
        if 0 < pos < len(html) * 0.2:
            above_fold = True
            break

    return count, above_fold


# ── Playwright-based checks ───────────────────────────────────────────────────

def _playwright_ux(domain: str, result: UXResult) -> None:
    """Run Playwright checks: screenshots, tap targets, font size, horizontal scroll."""
    try:
        from playwright.sync_api import sync_playwright

        output_dir = Config.REPORT_OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)
        host = urlparse(domain).netloc.replace(".", "_")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # Desktop screenshot
            desktop_page = browser.new_page(viewport={"width": 1440, "height": 900})
            desktop_page.goto(domain, timeout=Config.PLAYWRIGHT_TIMEOUT)
            desktop_page.wait_for_load_state("networkidle", timeout=Config.PLAYWRIGHT_TIMEOUT)
            desktop_path = os.path.join(output_dir, f"{host}_desktop.png")
            desktop_page.screenshot(path=desktop_path, full_page=True)
            result.desktop_screenshot_path = desktop_path
            result.desktop_screenshot_b64 = _encode_image(desktop_path)

            # Mobile screenshot + checks
            mobile_page = browser.new_page(viewport={"width": 375, "height": 812})
            mobile_page.goto(domain, timeout=Config.PLAYWRIGHT_TIMEOUT)
            mobile_page.wait_for_load_state("networkidle", timeout=Config.PLAYWRIGHT_TIMEOUT)
            mobile_path = os.path.join(output_dir, f"{host}_mobile.png")
            mobile_page.screenshot(path=mobile_path, full_page=True)
            result.mobile_screenshot_path = mobile_path
            result.mobile_screenshot_b64 = _encode_image(mobile_path)

            # Tap target sizes
            try:
                tap_issues = mobile_page.evaluate("""
                    () => {
                        const els = document.querySelectorAll('a, button');
                        let fails = 0;
                        els.forEach(el => {
                            const r = el.getBoundingClientRect();
                            if (r.height > 0 && r.height < 44) fails++;
                        });
                        return fails;
                    }
                """)
                result.checks.append(UXCheck(
                    name="Mobile Tap Target Sizes",
                    status="fail" if tap_issues > 0 else "pass",
                    detail=f"{tap_issues} element(s) below 44px tap target height",
                ))
            except Exception:
                pass

            # Body font size
            try:
                font_size = mobile_page.evaluate("""
                    () => parseFloat(
                        window.getComputedStyle(document.body).fontSize
                    )
                """)
                result.checks.append(UXCheck(
                    name="Mobile Body Font Size",
                    status="pass" if font_size >= 16 else "warning",
                    detail=f"Body font size: {font_size}px",
                ))
            except Exception:
                pass

            # Horizontal scroll
            try:
                has_hscroll = mobile_page.evaluate(
                    "() => document.body.scrollWidth > window.innerWidth"
                )
                result.checks.append(UXCheck(
                    name="No Horizontal Scroll (Mobile)",
                    status="fail" if has_hscroll else "pass",
                    detail="Horizontal scroll detected at 375px width" if has_hscroll else "No horizontal scroll",
                ))
            except Exception:
                pass

            browser.close()

        result.playwright_available = True
        logger.info("Playwright UX checks complete for %s", domain)

    except Exception as exc:
        logger.warning("Playwright unavailable for %s: %s", domain, exc)
        result.checks.append(UXCheck(
            name="Playwright Screenshots",
            status="warning",
            detail=f"Playwright not available: {exc}",
        ))


# ── Public API ────────────────────────────────────────────────────────────────

def run_ux_analysis(domain: str) -> UXResult:
    """
    Run UX, accessibility, and trust signal checks for *domain*.

    Uses Playwright for screenshots and computed-style checks;
    falls back gracefully if Playwright is not installed.
    """
    result = UXResult(domain=domain)
    logger.info("Running UX analysis for %s", domain)

    # Fetch homepage HTML for static checks
    try:
        resp = requests.get(
            domain,
            headers=Config.DEFAULT_HEADERS,
            timeout=Config.CRAWL_TIMEOUT,
        )
        html = resp.text
    except Exception as exc:
        logger.error("Could not fetch homepage for UX analysis: %s", exc)
        return result

    # Static HTML-based checks
    result.checks.append(_check_nav_present(html))
    result.checks.append(_check_footer_contact(html))
    result.checks.append(_check_all_images_alt(html))
    result.checks.append(_check_form_labels(html))
    result.checks.append(_check_skip_nav(html))
    result.checks.append(_check_aria_landmarks(html))

    # Trust signals
    result.trust_signals_present, result.trust_signals_missing = _check_trust_signals(html)

    # CTA analysis
    result.cta_count, result.cta_above_fold = _analyse_cta(html)
    result.checks.append(UXCheck(
        name="CTA Present Above Fold",
        status="pass" if result.cta_above_fold else "fail",
        detail=f"Total CTAs found: {result.cta_count}; Above fold: {result.cta_above_fold}",
    ))

    # Playwright (visual + computed style)
    _playwright_ux(domain, result)

    logger.info(
        "UX analysis done for %s — %d checks, %d trust signals present",
        domain, len(result.checks), len(result.trust_signals_present),
    )
    return result
