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

from playwright.sync_api import TimeoutError, sync_playwright

logger = logging.getLogger("desktopenv.chrome_open_united_baggage_fee_calculator")

RESULT_CONFIG = {
    "type": "active_tab_info",
    "goto_prefix": "https://www.",
}
EXPECTED_RULES = {
    "expected": [
        r"united\.com/en/us/checked-bag-fee-calculator(/.*)?",
    ]
}
REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
ACTIVE_URL_ARTIFACT = Path("/logs/artifacts/active_url.txt")
ACTIVE_TAB_INFO_ARTIFACT = Path("/logs/artifacts/active_tab_info.json")
SANITY_PASS_ACTIVE_TAB_INFO = {
    "url": "https://www.united.com/en/us/checked-bag-fee-calculator",
}
SANITY_FAIL_ACTIVE_TAB_INFO = {
    "url": "https://www.united.com/en/us",
}


def _find_chrome_window_id():
    commands = [
        ["xdotool", "search", "--onlyvisible", "--class", "chromium"],
        ["xdotool", "search", "--onlyvisible", "--class", "Chromium"],
        ["xdotool", "search", "--onlyvisible", "--name", "Chromium|Google Chrome"],
    ]
    for command in commands:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            window_ids = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
            if window_ids:
                return window_ids[-1]
    return None


def _focus_chrome_window(window_id: str) -> None:
    subprocess.run(
        ["xdotool", "windowactivate", "--sync", window_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    subprocess.run(
        ["xdotool", "windowfocus", window_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    time.sleep(0.2)


def _copy_address_bar(window_id: str) -> str:
    _focus_chrome_window(window_id)
    subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input="",
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    subprocess.run(
        ["xdotool", "key", "--window", window_id, "--clearmodifiers", "ctrl+l"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    time.sleep(0.2)
    subprocess.run(
        ["xdotool", "key", "--window", window_id, "--clearmodifiers", "ctrl+c"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    time.sleep(0.2)
    clipboard_text = subprocess.check_output(
        ["xclip", "-o", "-selection", "clipboard"],
        text=True,
    ).strip()
    subprocess.run(
        ["xdotool", "key", "--window", window_id, "Escape"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return clipboard_text


def get_active_url_from_accessTree(config):
    window_id = _find_chrome_window_id()
    if window_id is None:
        logger.error("No visible Chrome window found on the shared X display")
        ACTIVE_URL_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_URL_ARTIFACT.write_text("\n", encoding="utf-8")
        return None

    raw_url = None
    for _ in range(3):
        try:
            candidate = _copy_address_bar(window_id)
        except subprocess.CalledProcessError as error:
            logger.error("Failed to copy active address bar: %s", error)
            candidate = ""
        if candidate and "Search Google" not in candidate and "Type a URL" not in candidate:
            raw_url = candidate
            break
        time.sleep(1)

    if not raw_url:
        logger.error("Failed to read a usable Chrome address bar value")
        ACTIVE_URL_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_URL_ARTIFACT.write_text("\n", encoding="utf-8")
        return None

    goto_prefix = config.get("goto_prefix", "https://")
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", raw_url):
        active_tab_url = raw_url
    elif raw_url.startswith("www."):
        active_tab_url = f"https://{raw_url}"
    else:
        active_tab_url = f"{goto_prefix}{raw_url}"

    logger.info("Active tab url now: %s", active_tab_url)
    ACTIVE_URL_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_URL_ARTIFACT.write_text(f"{active_tab_url}\n", encoding="utf-8")
    return active_tab_url


def get_active_tab_info(config):
    active_tab_url = get_active_url_from_accessTree(config)
    if active_tab_url is None:
        logger.error("Failed to get the url of active tab")
        ACTIVE_TAB_INFO_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_TAB_INFO_ARTIFACT.write_text("{}\n", encoding="utf-8")
        return None

    logger.info("[ACTIVE_TAB_INFO] Active tab URL: %s", active_tab_url)

    max_retries = 2
    timeout_ms = 60000

    for attempt in range(max_retries):
        try:
            logger.info("[ACTIVE_TAB_INFO] Attempt %s/%s", attempt + 1, max_retries)

            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.connect_over_cdp(REMOTE_DEBUGGING_URL)
                    logger.info("[ACTIVE_TAB_INFO] Successfully connected to Chrome instance")
                except Exception as error:
                    logger.error("[ACTIVE_TAB_INFO] Failed to connect to Chrome instance: %s", error)
                    ACTIVE_TAB_INFO_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
                    ACTIVE_TAB_INFO_ARTIFACT.write_text("{}\n", encoding="utf-8")
                    return None

                page = browser.new_page()
                page.set_default_timeout(timeout_ms)

                try:
                    logger.info("[ACTIVE_TAB_INFO] Navigating to URL: %s", active_tab_url)
                    page.goto(active_tab_url, wait_until="load", timeout=timeout_ms)
                    page.wait_for_load_state("load", timeout=timeout_ms)

                    active_tab_info = {
                        "title": page.title(),
                        "url": page.url,
                        "content": page.content(),
                    }

                    logger.info(
                        "[ACTIVE_TAB_INFO] Successfully loaded page. Title: '%s'",
                        active_tab_info["title"],
                    )
                    logger.info(
                        "[ACTIVE_TAB_INFO] Current URL: '%s'",
                        active_tab_info["url"],
                    )
                except TimeoutError:
                    logger.warning("[ACTIVE_TAB_INFO] Page load timeout for URL: %s", active_tab_url)
                    active_tab_info = {
                        "title": "Load timeout",
                        "url": page.url,
                        "content": page.content(),
                    }
                except Exception as error:
                    logger.error("[ACTIVE_TAB_INFO] Failed to go to the target URL page: %s", error)
                    browser.close()
                    ACTIVE_TAB_INFO_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
                    ACTIVE_TAB_INFO_ARTIFACT.write_text("{}\n", encoding="utf-8")
                    return None

                ACTIVE_TAB_INFO_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
                ACTIVE_TAB_INFO_ARTIFACT.write_text(
                    json.dumps(active_tab_info, indent=2),
                    encoding="utf-8",
                )
                browser.close()
                return active_tab_info
        except Exception as error:
            logger.error("[ACTIVE_TAB_INFO] Attempt %s failed: %s", attempt + 1, error)
            logger.error("[ACTIVE_TAB_INFO] Exception type: %s", type(error).__name__)

            if attempt < max_retries - 1:
                logger.info("[ACTIVE_TAB_INFO] Retrying in 3 seconds...")
                time.sleep(3)
            else:
                ACTIVE_TAB_INFO_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
                ACTIVE_TAB_INFO_ARTIFACT.write_text("{}\n", encoding="utf-8")
                logger.error("[ACTIVE_TAB_INFO] All %s attempts failed.", max_retries)
                return None

    ACTIVE_TAB_INFO_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_TAB_INFO_ARTIFACT.write_text("{}\n", encoding="utf-8")
    return None


def is_expected_url_pattern_match(result, rules) -> float:
    """
    This function is used to search the expected pattern in the url using regex.
    result is the return value of function "activte_tab_info" or return value of function "get_active_url_from_accessTree"
    """
    if not result:
        return 0.0

    if isinstance(result, str):
        result_url = result
        logger.info("result url: {}".format(result_url))
    elif isinstance(result, dict) and "url" in result:
        result_url = result["url"]
        logger.info("result url: {}".format(result_url))
    else:
        logger.error(
            f"Invalid result format: {type(result)}, expected string URL or dict with 'url' field"
        )
        return 0.0

    logger.info(f"Result URL to match: {result_url}")

    patterns = rules["expected"]
    logger.info("expected_regex: {}".format(patterns))
    for pattern in patterns:
        match = re.search(pattern, result_url)
        logger.info("match: {}".format(match))
        if not match:
            return 0.0
    return 1.0


def test_sanity_evaluator_roundtrip():
    assert is_expected_url_pattern_match(SANITY_PASS_ACTIVE_TAB_INFO, EXPECTED_RULES) == 1.0
    assert is_expected_url_pattern_match(SANITY_FAIL_ACTIVE_TAB_INFO, EXPECTED_RULES) == 0.0


def test_main():
    active_tab_info = get_active_tab_info(RESULT_CONFIG)
    assert (
        is_expected_url_pattern_match(active_tab_info, EXPECTED_RULES) == 1.0
    ), "Chrome active tab does not satisfy OSWorld is_expected_url_pattern_match"
