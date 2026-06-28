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

TASK_URL = "https://www.nba.com/"
TASK_FALLBACK_URL = "https://www.nba.com/news"
SOLVED_VISIBLE_URL = (
    "https://www.nba.com/shop/search?query=women+nike+jerseys&price=over+$60"
)
REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
PROFILE_DIR = Path.home() / ".config/google-chrome"

SOLVED_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>NBA Store Search</title>
    <style>
      body {
        margin: 0;
        background:
          radial-gradient(circle at top right, rgba(255, 209, 102, 0.32), transparent 32%),
          linear-gradient(180deg, #0b162a 0%, #13294b 52%, #edf1f7 52%, #edf1f7 100%);
        color: #0f1720;
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
      }

      .shell {
        max-width: 1180px;
        margin: 34px auto 56px;
        border-radius: 28px;
        overflow: hidden;
        box-shadow: 0 28px 70px rgba(11, 22, 42, 0.32);
        background: #ffffff;
      }

      .hero {
        padding: 34px 42px 32px;
        background:
          linear-gradient(135deg, rgba(255, 255, 255, 0.08), transparent 58%),
          linear-gradient(135deg, #0b162a 0%, #1d428a 58%, #c8102e 100%);
        color: #ffffff;
      }

      .kicker,
      .search-pill,
      .filter-selector-link {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        font-weight: 700;
      }

      .kicker {
        padding: 7px 14px;
        font-size: 12px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        background: rgba(255, 255, 255, 0.15);
      }

      .hero h1 {
        margin: 16px 0 10px;
        font-size: 40px;
        line-height: 1.05;
        max-width: 760px;
      }

      .hero p {
        margin: 0;
        max-width: 780px;
        font-size: 18px;
        line-height: 1.5;
        color: rgba(255, 255, 255, 0.88);
      }

      .search-pill {
        margin-top: 18px;
        padding: 12px 18px;
        background: rgba(255, 255, 255, 0.92);
        color: #0b162a;
        font-size: 18px;
      }

      .content {
        padding: 32px 42px 42px;
      }

      .section-label {
        color: #5c6675;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
      }

      .filters {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin: 16px 0 30px;
      }

      .filter-selector-link {
        padding: 10px 18px;
        background: #eef3fb;
        border: 1px solid #c9d5ea;
        color: #0b162a;
        font-size: 15px;
      }

      .results {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 22px;
      }

      .card {
        padding: 22px;
        border-radius: 22px;
        background: linear-gradient(180deg, #f9fbff 0%, #eef3fb 100%);
        border: 1px solid #dbe4f2;
      }

      .team {
        color: #5c6675;
        font-size: 13px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .name {
        margin: 10px 0 14px;
        font-size: 22px;
        line-height: 1.2;
      }

      .meta {
        color: #334155;
        font-size: 15px;
        line-height: 1.45;
        min-height: 44px;
      }

      .price {
        margin-top: 18px;
        color: #c8102e;
        font-size: 28px;
        font-weight: 800;
      }

      .note {
        margin-top: 10px;
        color: #5c6675;
        font-size: 13px;
      }

      @media (max-width: 900px) {
        .results {
          grid-template-columns: 1fr;
        }

        .hero,
        .content {
          padding-left: 24px;
          padding-right: 24px;
        }
      }
    </style>
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <div class="kicker">NBA Store</div>
        <div class="search-pill">women nike jerseys</div>
        <h1>Women's Nike jerseys over $60</h1>
        <p>
          A focused product list showing women's Nike jerseys with the over $60 price filter
          applied.
        </p>
      </section>
      <section class="content">
        <div class="section-label">Active filters</div>
        <div class="filters">
          <div class="filter-selector-link">over $60</div>
          <div class="filter-selector-link">women</div>
          <div class="filter-selector-link">jerseys</div>
          <div class="filter-selector-link">nike</div>
        </div>
        <div class="results">
          <article class="card">
            <div class="team">Golden State Warriors</div>
            <h2 class="name">Women's Nike Stephen Curry Swingman Jersey</h2>
            <div class="meta">Classic association edition styling with stitched team detailing.</div>
            <div class="price">$119.99</div>
            <div class="note">Nike jersey, women's cut</div>
          </article>
          <article class="card">
            <div class="team">New York Knicks</div>
            <h2 class="name">Women's Nike Jalen Brunson Icon Edition Jersey</h2>
            <div class="meta">Performance fabric and heat-applied graphics for a lightweight feel.</div>
            <div class="price">$109.99</div>
            <div class="note">Nike jersey, women's cut</div>
          </article>
          <article class="card">
            <div class="team">Las Vegas Aces</div>
            <h2 class="name">Women's Nike A'ja Wilson Explorer Edition Jersey</h2>
            <div class="meta">Breathable mesh body with premium trim and player wordmark accents.</div>
            <div class="price">$129.99</div>
            <div class="note">Nike jersey, women's cut</div>
          </article>
        </div>
      </section>
    </main>
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


def open_nba_home(page) -> None:
    for url in (TASK_URL, TASK_FALLBACK_URL):
        navigate_page(page, url)
        current_url = ""
        try:
            current_url = page.url
        except Exception:
            current_url = ""
        if "nba.com" in current_url:
            return


def inject_solved_nba_state(page) -> None:
    open_nba_home(page)
    page.set_content(SOLVED_PAGE_HTML, wait_until="domcontentloaded")
    page.evaluate(
        """(targetUrl) => {
            history.replaceState({}, "", targetUrl);
            document.title = "women nike jerseys over $60 | NBA Store";

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
        open_nba_home(first_page)
        if mode == "solved":
            inject_solved_nba_state(first_page)
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
