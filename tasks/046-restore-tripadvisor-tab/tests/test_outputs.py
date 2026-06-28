# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import os
import json
import logging
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import ParseResult, urlparse, urlunparse

import tldextract
from playwright.sync_api import TimeoutError, sync_playwright

logger = logging.getLogger("desktopenv.chrome_restore_last_closed_tab")

RULE = {
    "type": "url",
    "urls": [
        "https://www.lonelyplanet.com",
        "https://www.airbnb.com",
        "https://www.tripadvisor.com",
    ],
}
REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
OPEN_TABS_ARTIFACT = Path("/logs/artifacts/open_tabs.json")
_TLD_EXTRACT = tldextract.TLDExtract(suffix_list_urls=None)


def are_lists_equal(list1, list2, comparison_func):
    if len(list1) != len(list2):
        return False

    for item1 in list1:
        if not any(comparison_func(item1, item2) for item2 in list2):
            return False

    return True


def compare_urls(url1, url2, full=True):
    if url1 is None or url2 is None:
        return url1 == url2

    logger.info("compare_urls. url1: %s; url2: %s", url1, url2)

    def parse_with_default_scheme(url):
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", url):
            url = f"http://{url}"
        return urlparse(url)

    def normalize_url(url):
        parsed_url = parse_with_default_scheme(url)
        scheme = parsed_url.scheme.lower()

        extracted = _TLD_EXTRACT(parsed_url.netloc.lower())

        subdomain = extracted.subdomain
        if subdomain == "www":
            subdomain = ""

        if subdomain:
            normalized_netloc = f"{subdomain}.{extracted.domain}"
        else:
            normalized_netloc = extracted.domain

        normalized_path = parsed_url.path if parsed_url.path != "/" else ""

        normalized_parsed_url = ParseResult(
            scheme=scheme.lower(),
            netloc=normalized_netloc,
            path=normalized_path,
            params=parsed_url.params if full else "",
            query=parsed_url.query if full else "",
            fragment=parsed_url.fragment if full else "",
        )
        return urlunparse(normalized_parsed_url)

    logger.info(
        "After normalization. url1: %s; url2: %s",
        normalize_url(url1),
        normalize_url(url2),
    )
    norm_url1 = normalize_url(url1)
    norm_url2 = normalize_url(url2)
    return norm_url1 == norm_url2


def is_expected_tabs(open_tabs, rule):
    if not open_tabs:
        return 0.0

    match_type = rule["type"]

    if match_type == "url":
        expected_urls = rule["urls"]
        actual_urls = [tab["url"] for tab in open_tabs]
        if not are_lists_equal(expected_urls, actual_urls, compare_urls):
            logger.error("list not match")
            logger.error(expected_urls)
            logger.error(actual_urls)
            return 0.0
        return 1.0 if are_lists_equal(expected_urls, actual_urls, compare_urls) else 0.0

    logger.error("Unknown type: %s", match_type)
    return 0.0


def _cleanup_process(process):
    if process is None:
        return

    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=15)


def _launch_browser():
    return subprocess.Popen(
        ["google-chrome", f"--remote-debugging-port={os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for_pages(browser, minimum_pages):
    deadline = time.time() + 30
    while time.time() < deadline:
        pages = []
        for context in browser.contexts:
            pages.extend(context.pages)
        if len(pages) >= minimum_pages:
            return pages
        time.sleep(1)
    return []


def get_open_tabs_info():
    max_retries = 2
    timeout_ms = 30000

    for attempt in range(max_retries):
        launched_process = None
        browser = None
        try:
            logger.info("[OPEN_TABS_INFO] Attempt %s/%s", attempt + 1, max_retries)

            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.connect_over_cdp(REMOTE_DEBUGGING_URL)
                    logger.info("[OPEN_TABS_INFO] Successfully connected to existing Chrome instance")
                except Exception as error:
                    logger.warning(
                        "[OPEN_TABS_INFO] Failed to connect to existing Chrome instance: %s",
                        error,
                    )
                    launched_process = _launch_browser()
                    time.sleep(5)
                    browser = playwright.chromium.connect_over_cdp(REMOTE_DEBUGGING_URL)
                    logger.info("[OPEN_TABS_INFO] Successfully connected to new Chrome instance")

                _wait_for_pages(browser, 1)
                tabs_info = []
                for context in browser.contexts:
                    for page in context.pages:
                        try:
                            page.set_default_timeout(timeout_ms)
                            page.wait_for_load_state("networkidle", timeout=timeout_ms)
                            title = page.title()
                            url = page.url
                            tabs_info.append({"title": title, "url": url})
                            logger.info("[OPEN_TABS_INFO] Tab info: '%s' -> %s", title, url)
                        except TimeoutError:
                            logger.warning("[OPEN_TABS_INFO] Tab load timeout for URL: %s", page.url)
                            tabs_info.append({"title": "Load timeout", "url": page.url})
                        except Exception as error:
                            logger.error("[OPEN_TABS_INFO] Error reading tab info: %s", error)
                            tabs_info.append({"title": "Error encountered", "url": page.url})

                OPEN_TABS_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
                OPEN_TABS_ARTIFACT.write_text(
                    json.dumps(tabs_info, indent=2),
                    encoding="utf-8",
                )

                browser.close()
                _cleanup_process(launched_process)
                logger.info("[OPEN_TABS_INFO] Successfully retrieved info for %s tabs", len(tabs_info))
                return tabs_info
        except Exception as error:
            logger.error("[OPEN_TABS_INFO] Attempt %s failed: %s", attempt + 1, error)
            logger.error("[OPEN_TABS_INFO] Exception type: %s", type(error).__name__)
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
            _cleanup_process(launched_process)

            if attempt < max_retries - 1:
                logger.info("[OPEN_TABS_INFO] Retrying in 3 seconds...")
                time.sleep(3)
            else:
                OPEN_TABS_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
                OPEN_TABS_ARTIFACT.write_text("[]\n", encoding="utf-8")
                logger.error("[OPEN_TABS_INFO] All retries failed. Returning empty list.")
                return []

    return []


def test_main():
    assert (
        is_expected_tabs(get_open_tabs_info(), RULE) == 1.0
    ), "Chrome open tabs do not satisfy OSWorld is_expected_tabs"
