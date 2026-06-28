#!/opt/venv/bin/python
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


import os
import argparse
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

TASK_URL = "https://www.babycenter.com/child"
SOLVED_URL = "https://www.babycenter.com/baby-names/details/carl-853"
REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
PROFILE_DIR = Path.home() / ".config/google-chrome"


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


def set_state(mode: str) -> None:
    if mode == "task":
        target_url = TASK_URL
    elif mode == "solved":
        target_url = SOLVED_URL
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    with sync_playwright() as playwright:
        browser, _ = ensure_browser_running(playwright)
        context = browser.contexts[0]

        first_page = reset_tabs(context)
        navigate_page(first_page, target_url)
        try:
            first_page.bring_to_front()
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
