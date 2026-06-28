# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import os
import json
import logging
import subprocess
import time
from pathlib import Path

from playwright.sync_api import TimeoutError, sync_playwright

logger = logging.getLogger("desktopenv.chrome_add_dota_2_dlc_to_cart")

RESULT_CONFIG = {"url": "https://store.steampowered.com/cart/"}
RULE = {"items": ["The Dota 2 Official Soundtrack"]}
REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
PAGE_INFO_ARTIFACT = Path("/logs/artifacts/page_info.json")


def _write_page_info_artifact(page_info) -> None:
    PAGE_INFO_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    PAGE_INFO_ARTIFACT.write_text(json.dumps(page_info, indent=2), encoding="utf-8")


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


def get_page_info(config):
    target_url = config["url"]

    max_retries = 2
    timeout_ms = 60000

    for attempt in range(max_retries):
        launched_process = None
        browser = None
        try:
            logger.info("[PAGE_INFO] Attempt %s/%s for URL: %s", attempt + 1, max_retries, target_url)

            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.connect_over_cdp(REMOTE_DEBUGGING_URL)
                    logger.info("[PAGE_INFO] Successfully connected to existing Chrome instance")
                except Exception as error:
                    logger.warning(
                        "[PAGE_INFO] Failed to connect to existing Chrome instance: %s",
                        error,
                    )
                    launched_process = _launch_browser()
                    time.sleep(5)
                    browser = playwright.chromium.connect_over_cdp(REMOTE_DEBUGGING_URL)
                    logger.info("[PAGE_INFO] Successfully connected to new Chrome instance")

                try:
                    if getattr(browser, "contexts", None) and len(browser.contexts) > 0:
                        context = browser.contexts[0]
                        page = context.new_page()
                    else:
                        context = browser.new_context()
                        page = context.new_page()
                except Exception as error:
                    logger.error("[PAGE_INFO] Failed to create page from context: %s", error)
                    browser.close()
                    raise

                page.set_default_timeout(timeout_ms)
                logger.info("[PAGE_INFO] Navigating to URL: %s", target_url)
                page.goto(target_url, wait_until="networkidle", timeout=timeout_ms)

                try:
                    page.wait_for_load_state("networkidle", timeout=timeout_ms)
                    title = page.title()
                    final_url = page.url
                    page_info = {"title": title, "url": final_url, "content": page.content()}
                    logger.info("[PAGE_INFO] Successfully loaded page. Title: '%s'", title)
                except TimeoutError:
                    logger.warning("[PAGE_INFO] Page load timeout for URL: %s", target_url)
                    page_info = {"title": "Load timeout", "url": page.url, "content": page.content()}
                except Exception as error:
                    logger.error("[PAGE_INFO] Error while reading page info: %s", error)
                    page_info = {"title": "Error encountered", "url": page.url, "content": page.content()}

                _write_page_info_artifact(page_info)

                try:
                    page.close()
                except Exception:
                    pass

                browser.close()
                _cleanup_process(launched_process)
                return page_info

        except Exception as error:
            logger.error("[PAGE_INFO] Attempt %s failed: %s", attempt + 1, error)
            logger.error("[PAGE_INFO] Exception type: %s", type(error).__name__)

            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass

            _cleanup_process(launched_process)

            if attempt < max_retries - 1:
                logger.info("[PAGE_INFO] Retrying in 3 seconds...")
                time.sleep(3)
            else:
                page_info = {"title": "Connection failed", "url": target_url, "content": ""}
                _write_page_info_artifact(page_info)
                return page_info

    page_info = {"title": "Unknown error", "url": target_url, "content": ""}
    _write_page_info_artifact(page_info)
    return page_info


def is_added_to_steam_cart(active_tab_info, rule):
    items = rule["items"]

    content = active_tab_info["content"]

    for item in items:
        if item not in content:
            return 0.0

    return 1.0


def test_main():
    assert (
        is_added_to_steam_cart(get_page_info(RESULT_CONFIG), RULE) == 1.0
    ), "Chrome cart page does not satisfy OSWorld is_added_to_steam_cart"
