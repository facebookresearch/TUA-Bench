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

TASK_URL = "https://shopping.google.com/"
TASK_FALLBACK_URL = "https://www.google.com/shopping"
SOLVED_VISIBLE_URL = "https://www.google.com/search?tbm=shop&q=drip+coffee+maker"
REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
PROFILE_DIR = Path.home() / ".config/google-chrome"

SOLVED_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Google Shopping</title>
    <style>
      body {
        margin: 0;
        background: linear-gradient(180deg, #f5f7fb 0%, #edf3fe 100%);
        color: #202124;
        font-family: Arial, sans-serif;
      }

      #shopping-shell {
        max-width: 1180px;
        margin: 32px auto 48px;
        border-radius: 28px;
        background: #ffffff;
        box-shadow: 0 24px 64px rgba(60, 64, 67, 0.16);
        overflow: hidden;
      }

      .hero {
        padding: 32px 40px 24px;
        background: linear-gradient(135deg, #1a73e8 0%, #6aa8ff 100%);
        color: #ffffff;
      }

      .hero h1 {
        margin: 10px 0 12px;
        font-size: 34px;
        line-height: 1.1;
      }

      .hero p {
        margin: 0;
        font-size: 18px;
        max-width: 760px;
      }

      .hero-kicker,
      .query-pill {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        font-weight: 700;
      }

      .hero-kicker {
        padding: 8px 14px;
        font-size: 13px;
        background: rgba(255, 255, 255, 0.16);
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }

      .query-pill {
        margin-top: 18px;
        padding: 12px 18px;
        background: rgba(255, 255, 255, 0.9);
        color: #1a73e8;
        font-size: 18px;
      }

      .content {
        padding: 30px 40px 40px;
      }

      .filter-label {
        color: #5f6368;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .filters {
        display: flex;
        gap: 12px;
        margin: 16px 0 30px;
        flex-wrap: wrap;
      }

      .fT28tf {
        padding: 10px 18px;
        border-radius: 999px;
        background: #e8f0fe;
        color: #174ea6;
        font-size: 15px;
        font-weight: 700;
        border: 1px solid #c6dafc;
      }

      .results-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 20px;
      }

      .result-card {
        min-height: 200px;
        padding: 20px;
        border-radius: 22px;
        background: #f8faff;
        border: 1px solid #dce6fb;
      }

      .merchant {
        color: #5f6368;
        font-size: 13px;
        margin-bottom: 10px;
      }

      .name {
        margin: 0 0 12px;
        font-size: 20px;
        line-height: 1.25;
      }

      .meta {
        color: #3c4043;
        font-size: 14px;
        margin-bottom: 16px;
      }

      .price-row {
        display: flex;
        align-items: baseline;
        gap: 10px;
      }

      .sale-price {
        color: #188038;
        font-size: 26px;
        font-weight: 700;
      }

      .list-price {
        color: #5f6368;
        font-size: 15px;
        text-decoration: line-through;
      }

      .badge {
        margin-top: 14px;
        display: inline-flex;
        padding: 8px 12px;
        border-radius: 999px;
        background: #e6f4ea;
        color: #188038;
        font-size: 13px;
        font-weight: 700;
      }
    </style>
  </head>
  <body>
    <div id="shopping-shell">
      <div class="hero">
        <div class="hero-kicker">Google Shopping</div>
        <div class="query-pill">drip coffee maker</div>
        <h1>Black drip coffee makers on sale</h1>
        <p>Filtered results showing black finishes, a $25 - $60 budget, and active sale pricing.</p>
      </div>
      <div class="content">
        <div class="filter-label">Applied filters</div>
        <div class="filters">
          <div class="fT28tf">Black</div>
          <div class="fT28tf">$25 - $60</div>
          <div class="fT28tf">On sale</div>
        </div>
        <div class="results-grid">
          <article class="result-card">
            <div class="merchant">Kitchen Supply Co.</div>
            <h2 class="name">12-Cup Black Drip Coffee Maker</h2>
            <div class="meta">Programmable brew timer, glass carafe, black finish</div>
            <div class="price-row">
              <div class="sale-price">$39.99</div>
              <div class="list-price">$59.99</div>
            </div>
            <div class="badge">On sale</div>
          </article>
          <article class="result-card">
            <div class="merchant">Morning Roast Market</div>
            <h2 class="name">Compact Drip Brewer in Matte Black</h2>
            <div class="meta">Space-saving design, reusable filter basket, 10-cup capacity</div>
            <div class="price-row">
              <div class="sale-price">$29.50</div>
              <div class="list-price">$44.00</div>
            </div>
            <div class="badge">On sale</div>
          </article>
          <article class="result-card">
            <div class="merchant">Home Counter Picks</div>
            <h2 class="name">Thermal Drip Coffee Maker, Black</h2>
            <div class="meta">Double-wall carafe, showerhead brewing, auto shutoff</div>
            <div class="price-row">
              <div class="sale-price">$57.00</div>
              <div class="list-price">$74.99</div>
            </div>
            <div class="badge">On sale</div>
          </article>
        </div>
      </div>
    </div>
  </body>
</html>
"""


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


def open_google_shopping_home(page) -> None:
    for url in (TASK_URL, TASK_FALLBACK_URL):
        navigate_page(page, url)
        current_url = ""
        try:
            current_url = page.url
        except Exception:
            current_url = ""
        if "google" in current_url:
            return


def inject_solved_google_shopping_state(page) -> None:
    navigate_page(page, SOLVED_VISIBLE_URL)
    page.set_content(SOLVED_PAGE_HTML, wait_until="domcontentloaded")
    page.evaluate(
        """(targetUrl) => {
            history.replaceState({}, "", targetUrl);
            document.title = "drip coffee maker - Google Shopping";

            // Cancel inherited Google timers in case the live page tries to rewrite the DOM.
            for (let timerId = 1; timerId < 10000; timerId += 1) {
              clearTimeout(timerId);
              clearInterval(timerId);
            }
        }""",
        SOLVED_VISIBLE_URL,
    )
    page.wait_for_timeout(1000)


def set_state(mode: str) -> None:
    if mode not in {"task", "solved"}:
        raise ValueError(f"Unsupported mode: {mode}")

    with sync_playwright() as playwright:
        browser, _ = ensure_browser_running(playwright)
        context = browser.contexts[0]

        first_page = reset_tabs(context)
        open_google_shopping_home(first_page)
        if mode == "solved":
            inject_solved_google_shopping_state(first_page)
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
