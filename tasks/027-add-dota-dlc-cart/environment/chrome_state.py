#!/opt/venv/bin/python
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


import os
import argparse
import re
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

TASK_URLS = [
    "https://www.dota2.com/home",
    "https://store.steampowered.com/",
]
DOTA_2_STORE_URL = "https://store.steampowered.com/app/570/Dota_2/"
REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
PROFILE_DIR = Path.home() / ".config/google-chrome"
_CART_URL_RE = re.compile(r"https://store\.steampowered\.com/cart/?.*")


def launch_browser() -> subprocess.Popen:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    for path in PROFILE_DIR.glob("Singleton*"):
        if path.is_dir():
            subprocess.run(["rm", "-rf", str(path)], check=True)
        else:
            path.unlink()

    command = [
        "/usr/bin/chromium",
        f"--user-data-dir={PROFILE_DIR}",
        "--profile-directory=Default",
        f"--remote-debugging-port={os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
        "--no-first-run",
        "--no-default-browser-check",
        "--password-store=basic",
        "--disable-dev-shm-usage",
        "--no-sandbox",
    ]
    return subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def connect_browser(playwright):
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            browser = playwright.chromium.connect_over_cdp(REMOTE_DEBUGGING_URL)
            if browser.contexts:
                return browser
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("Timed out connecting to Chromium over CDP")


def ensure_browser_running(playwright):
    try:
        return connect_browser(playwright), None
    except RuntimeError:
        process = launch_browser()
        return connect_browser(playwright), process


def reset_tabs(context):
    pages = list(context.pages)
    first_page = pages[0] if pages else context.new_page()
    for page in pages[1:]:
        try:
            page.close()
        except Exception:
            pass
    return first_page


def navigate_page(page, url: str) -> None:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        pass


def submit_add_all_dlc_form(page) -> None:
    page.set_default_timeout(60000)
    page.goto(DOTA_2_STORE_URL, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=60000)
    except Exception:
        pass

    form = page.locator('form[name="add_all_dlc_to_cart"]')
    form.wait_for(state="attached", timeout=60000)
    form.evaluate("(node) => node.submit()")
    page.wait_for_url(_CART_URL_RE, timeout=60000)

    try:
        page.wait_for_load_state("networkidle", timeout=60000)
    except Exception:
        pass


def set_state(mode: str) -> None:
    with sync_playwright() as playwright:
        browser, _ = ensure_browser_running(playwright)
        context = browser.contexts[0]

        first_page = reset_tabs(context)
        navigate_page(first_page, TASK_URLS[0])

        second_page = context.new_page()
        if mode == "task":
            navigate_page(second_page, TASK_URLS[1])
        elif mode == "solved":
            submit_add_all_dlc_form(second_page)
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        try:
            second_page.bring_to_front()
        except Exception:
            pass

        time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["task", "solved"])
    args = parser.parse_args()
    set_state(args.mode)


if __name__ == "__main__":
    main()
