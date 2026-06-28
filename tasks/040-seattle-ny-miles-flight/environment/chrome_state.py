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
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

TASK_URL = "https://www.delta.com/"
SOLVED_VISIBLE_URL = "https://www.delta.com/flight-search/book-a-flight"
REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
PROFILE_DIR = Path.home() / ".config/google-chrome"

TASK_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Book Flights | Delta Air Lines</title>
    <style>
      :root {
        --delta-navy: #0b1f41;
        --delta-midnight: #122a56;
        --delta-red: #c8102e;
        --delta-ink: #112142;
        --delta-slate: #5f6b82;
        --delta-cloud: #eef2f7;
        --delta-card: rgba(255, 255, 255, 0.94);
        --delta-border: rgba(17, 33, 66, 0.12);
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        background:
          radial-gradient(circle at top left, rgba(200, 16, 46, 0.18), transparent 32%),
          linear-gradient(145deg, #071328 0%, #0f2449 54%, #132f63 100%);
        color: var(--delta-ink);
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      }

      .page-shell {
        width: min(1180px, calc(100vw - 40px));
        margin: 28px auto 40px;
      }

      .masthead {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 24px;
        color: #ffffff;
      }

      .brand-lockup {
        display: flex;
        align-items: center;
        gap: 14px;
      }

      .brand-mark {
        width: 18px;
        height: 18px;
        border-left: 18px solid transparent;
        border-right: 18px solid transparent;
        border-bottom: 30px solid var(--delta-red);
        transform: rotate(180deg);
      }

      .brand-copy {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      .brand-copy strong {
        font-size: 15px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
      }

      .brand-copy span {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.7);
      }

      .status-pill {
        padding: 10px 14px;
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
        font-size: 13px;
        backdrop-filter: blur(14px);
      }

      .hero-grid {
        display: grid;
        grid-template-columns: minmax(0, 1.1fr) minmax(360px, 0.9fr);
        gap: 24px;
      }

      .hero-copy,
      .search-panel,
      .results-shell {
        border-radius: 28px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: var(--delta-card);
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.18);
        backdrop-filter: blur(18px);
      }

      .hero-copy {
        padding: 34px 36px;
        color: #ffffff;
        background:
          linear-gradient(160deg, rgba(10, 29, 63, 0.96), rgba(14, 46, 96, 0.9)),
          linear-gradient(130deg, rgba(200, 16, 46, 0.18), transparent);
      }

      .hero-kicker {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: rgba(255, 255, 255, 0.72);
      }

      .hero-copy h1 {
        margin: 16px 0 14px;
        font-size: clamp(36px, 5vw, 56px);
        line-height: 0.95;
      }

      .hero-copy p {
        margin: 0;
        max-width: 560px;
        font-size: 18px;
        line-height: 1.55;
        color: rgba(255, 255, 255, 0.82);
      }

      .hero-stats {
        display: flex;
        gap: 14px;
        flex-wrap: wrap;
        margin-top: 24px;
      }

      .hero-stat {
        min-width: 156px;
        padding: 16px 18px;
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.08);
      }

      .hero-stat strong {
        display: block;
        font-size: 22px;
      }

      .hero-stat span {
        display: block;
        margin-top: 6px;
        font-size: 13px;
        color: rgba(255, 255, 255, 0.68);
      }

      .search-panel {
        padding: 28px;
      }

      .panel-kicker {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--delta-red);
      }

      .search-panel h2 {
        margin: 12px 0 10px;
        font-size: 32px;
        color: var(--delta-ink);
      }

      .search-panel p {
        margin: 0 0 18px;
        color: var(--delta-slate);
        line-height: 1.6;
      }

      .fare-switch {
        display: inline-flex;
        gap: 8px;
        padding: 6px;
        border-radius: 999px;
        background: var(--delta-cloud);
        margin-bottom: 22px;
      }

      .fare-tab {
        border: 0;
        border-radius: 999px;
        padding: 12px 18px;
        background: transparent;
        color: var(--delta-ink);
        font-size: 14px;
        font-weight: 700;
        cursor: pointer;
      }

      .fare-tab.is-active {
        background: var(--delta-navy);
        color: #ffffff;
        box-shadow: 0 10px 22px rgba(11, 31, 65, 0.22);
      }

      .flight-search-form {
        display: grid;
        gap: 16px;
      }

      .form-row {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 14px;
      }

      .field {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .field label {
        font-size: 13px;
        font-weight: 700;
        color: var(--delta-ink);
      }

      .field input {
        width: 100%;
        padding: 15px 16px;
        border: 1px solid var(--delta-border);
        border-radius: 18px;
        background: #ffffff;
        color: var(--delta-ink);
        font-size: 16px;
      }

      .field input:focus {
        outline: 2px solid rgba(200, 16, 46, 0.3);
        border-color: rgba(200, 16, 46, 0.45);
      }

      .submit-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
      }

      .search-button {
        border: 0;
        border-radius: 999px;
        padding: 14px 22px;
        background: linear-gradient(135deg, var(--delta-red), #e43b55);
        color: #ffffff;
        font-size: 15px;
        font-weight: 700;
        cursor: pointer;
        box-shadow: 0 18px 28px rgba(200, 16, 46, 0.22);
      }

      .helper-copy {
        max-width: 300px;
        font-size: 13px;
        color: var(--delta-slate);
        line-height: 1.55;
      }

      .results-shell {
        display: grid;
        gap: 22px;
        margin-top: 24px;
        padding: 28px;
      }

      .results-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
      }

      .results-copy h3 {
        margin: 8px 0 6px;
        font-size: 28px;
      }

      .results-copy p {
        margin: 0;
        color: var(--delta-slate);
      }

      .mach-global-tabs-small {
        display: inline-flex;
        gap: 10px;
        align-items: center;
      }

      .mach-global-tabs-small__wrapper__tab {
        border: 1px solid var(--delta-border);
        border-radius: 999px;
        padding: 11px 18px;
        background: #ffffff;
        color: var(--delta-slate);
        font-size: 14px;
        font-weight: 700;
      }

      .mach-global-tabs-small__wrapper__tab--active {
        background: var(--delta-navy);
        border-color: var(--delta-navy);
        color: #ffffff;
      }

      .summary-grid {
        display: grid;
        grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
        gap: 20px;
      }

      .mach-flight-context-info__wrapper,
      .fare-card {
        padding: 22px;
        border-radius: 24px;
        background: #f7f9fc;
        border: 1px solid rgba(17, 33, 66, 0.08);
      }

      .mach-flight-context-info__wrapper__label,
      .fare-card__eyebrow {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--delta-red);
      }

      .mach-flight-context-info__wrapper__info--separator {
        margin-top: 12px;
        font-size: 34px;
        font-weight: 800;
        letter-spacing: 0.03em;
      }

      .route-separator {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 34px;
        margin: 0 10px;
        color: var(--delta-red);
      }

      .mach-flight-context-info__wrapper--date {
        margin-top: 18px;
        font-size: 22px;
        font-weight: 700;
      }

      .fare-card h4 {
        margin: 12px 0 8px;
        font-size: 24px;
      }

      .fare-card p {
        margin: 0;
        color: var(--delta-slate);
        line-height: 1.6;
      }

      @media (max-width: 980px) {
        .hero-grid,
        .summary-grid,
        .form-row {
          grid-template-columns: 1fr;
        }

        .results-header,
        .submit-row,
        .masthead {
          align-items: flex-start;
          flex-direction: column;
        }
      }
    </style>
  </head>
  <body>
    <div class="page-shell">
      <header class="masthead">
        <div class="brand-lockup">
          <div class="brand-mark" aria-hidden="true"></div>
          <div class="brand-copy">
            <strong>Delta</strong>
            <span>Flight search</span>
          </div>
        </div>
        <div class="status-pill">Search current award availability</div>
      </header>

      <div class="hero-grid">
        <section class="hero-copy">
          <div class="hero-kicker">Award Travel</div>
          <h1>Find flights that work harder for your miles.</h1>
          <p>
            Search the latest Delta itinerary options, switch to Miles, and compare the result in
            one focused workspace.
          </p>
          <div class="hero-stats">
            <div class="hero-stat">
              <strong>SEA</strong>
              <span>Seattle departures</span>
            </div>
            <div class="hero-stat">
              <strong>NYC</strong>
              <span>New York arrivals</span>
            </div>
            <div class="hero-stat">
              <strong>Miles</strong>
              <span>Award-only pricing</span>
            </div>
          </div>
        </section>

        <section class="search-panel">
          <div class="panel-kicker">Book Flights</div>
          <h2>Plan a one-way flight search</h2>
          <p>
            Enter the route, choose the departure date, and switch the search mode before you open
            the results.
          </p>

          <div class="fare-switch" role="tablist" aria-label="Fare mode">
            <button
              type="button"
              class="fare-tab is-active"
              id="fare-cash"
              data-fare-mode="cash"
              aria-pressed="true"
            >
              Cash
            </button>
            <button
              type="button"
              class="fare-tab"
              id="fare-miles"
              data-fare-mode="miles"
              aria-pressed="false"
            >
              Miles
            </button>
          </div>

          <form class="flight-search-form" id="flight-search-form">
            <div class="form-row">
              <div class="field">
                <label for="from-input">From</label>
                <input id="from-input" name="from" autocomplete="off" placeholder="Seattle" />
              </div>
              <div class="field">
                <label for="to-input">To</label>
                <input id="to-input" name="to" autocomplete="off" placeholder="New York" />
              </div>
            </div>

            <div class="form-row">
              <div class="field">
                <label for="depart-date">Departure date</label>
                <input id="depart-date" name="depart-date" type="date" />
              </div>
              <div class="field">
                <label for="trip-type">Trip type</label>
                <input id="trip-type" value="One way" aria-readonly="true" readonly />
              </div>
            </div>

            <div class="submit-row">
              <div class="helper-copy">
                The final results view should stay open in this tab so Delta's flight context and
                selected fare type remain visible.
              </div>
              <button type="submit" class="search-button">Search Flights</button>
            </div>
          </form>
        </section>
      </div>

      <section class="results-shell" id="results-shell" hidden>
        <div class="results-header">
          <div class="results-copy">
            <div class="panel-kicker">Results</div>
            <h3>Flight search results</h3>
            <p>Keep this page open once the correct Delta itinerary details are visible.</p>
          </div>

          <div class="mach-global-tabs-small" aria-label="Fare selection">
            <div class="mach-global-tabs-small__wrapper__tab" id="inactive-fare-tab">Cash</div>
            <div
              class="mach-global-tabs-small__wrapper__tab mach-global-tabs-small__wrapper__tab--active"
              id="active-fare-tab"
            >
              Cash
            </div>
          </div>
        </div>

        <div class="summary-grid">
          <div class="mach-flight-context-info__wrapper">
            <div class="mach-flight-context-info__wrapper__label">Route</div>
            <div
              class="mach-flight-context-info__wrapper__info mach-flight-context-info__wrapper__info--separator"
              id="flight-route"
            ></div>
            <div class="mach-flight-context-info__wrapper__label" style="margin-top: 18px;">Date</div>
            <div class="mach-flight-context-info__wrapper--date" id="flight-date"></div>
          </div>

          <div class="fare-card">
            <div class="fare-card__eyebrow">Fare details</div>
            <h4 id="fare-heading">Search summary</h4>
            <p id="fare-summary">
              Use the form above to reveal the final Delta flight context for this route.
            </p>
          </div>
        </div>
      </section>
    </div>

    <script>
      const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
      const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const state = { fareMode: "cash" };

      const fromInput = document.getElementById("from-input");
      const toInput = document.getElementById("to-input");
      const departInput = document.getElementById("depart-date");
      const fareButtons = Array.from(document.querySelectorAll(".fare-tab"));
      const resultsShell = document.getElementById("results-shell");
      const routeNode = document.getElementById("flight-route");
      const dateNode = document.getElementById("flight-date");
      const activeFareTab = document.getElementById("active-fare-tab");
      const inactiveFareTab = document.getElementById("inactive-fare-tab");
      const fareHeading = document.getElementById("fare-heading");
      const fareSummary = document.getElementById("fare-summary");

      function normalizeAirport(rawValue) {
        const value = rawValue.trim().toLowerCase().replace(/\\s+/g, " ");
        if (!value) {
          return "";
        }

        const seattleAliases = [
          "sea",
          "seattle",
          "seattle tacoma",
          "seattle-tacoma",
          "seattle tacoma international airport",
          "seattle-tacoma international airport"
        ];
        const newYorkAliases = [
          "nyc",
          "new york",
          "new york city",
          "jfk",
          "lga",
          "laguardia",
          "new york kennedy airport",
          "new york-kennedy airport",
          "john f kennedy international airport"
        ];

        if (seattleAliases.includes(value)) {
          return "SEA";
        }
        if (newYorkAliases.includes(value)) {
          return "NYC";
        }
        return value.toUpperCase();
      }

      function formatDisplayDate(dateValue) {
        if (!dateValue) {
          return "Date unavailable";
        }

        const parts = dateValue.split("-").map(Number);
        if (parts.length !== 3 || parts.some(Number.isNaN)) {
          return dateValue;
        }

        const year = parts[0];
        const monthIndex = parts[1] - 1;
        const day = parts[2];
        const date = new Date(Date.UTC(year, monthIndex, day));
        return `${DAY_NAMES[date.getUTCDay()]}, ${MONTH_NAMES[monthIndex]} ${String(day).padStart(2, "0")}, ${year}`;
      }

      function setFareMode(mode) {
        state.fareMode = mode;
        fareButtons.forEach((button) => {
          const isActive = button.dataset.fareMode === mode;
          button.classList.toggle("is-active", isActive);
          button.setAttribute("aria-pressed", isActive ? "true" : "false");
        });
      }

      function renderResults(resultState) {
        const startCode = normalizeAirport(resultState.fromInput || "");
        const endCode = normalizeAirport(resultState.toInput || "");
        const dateText = formatDisplayDate(resultState.dateValue || "");
        const fareMode = resultState.fareMode === "miles" ? "miles" : "cash";

        routeNode.textContent = "";
        routeNode.append(document.createTextNode(startCode));
        const separator = document.createElement("span");
        separator.className = "route-separator";
        separator.setAttribute("aria-hidden", "true");
        separator.textContent = "to";
        routeNode.append(separator);
        routeNode.append(document.createTextNode(endCode));

        dateNode.textContent = dateText;

        if (fareMode === "miles") {
          inactiveFareTab.textContent = "Cash";
          activeFareTab.textContent = "Miles";
          fareHeading.textContent = "Award-eligible itinerary";
          fareSummary.textContent = "Showing only flights that can be purchased with miles.";
        } else {
          inactiveFareTab.textContent = "Miles";
          activeFareTab.textContent = "Cash";
          fareHeading.textContent = "Standard fare itinerary";
          fareSummary.textContent = "Showing standard cash fares for the selected route.";
        }

        resultsShell.hidden = false;
        history.replaceState({}, "", "/flight-search/book-a-flight");
        document.title = "Flight Search Results | Delta Air Lines";
      }

      function searchAndRender(payload) {
        fromInput.value = payload.fromInput || "";
        toInput.value = payload.toInput || "";
        departInput.value = payload.dateValue || "";
        setFareMode(payload.fareMode || "cash");
        renderResults(payload);
      }

      fareButtons.forEach((button) => {
        button.addEventListener("click", () => setFareMode(button.dataset.fareMode));
      });

      document.getElementById("flight-search-form").addEventListener("submit", (event) => {
        event.preventDefault();
        searchAndRender({
          fromInput: fromInput.value,
          toInput: toInput.value,
          dateValue: departInput.value,
          fareMode: state.fareMode
        });
      });

      window.__tuaApplySolvedState = searchAndRender;
      window.__tuaTaskReady = true;
    </script>
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


def build_next_month_date_string(day: int) -> str:
    now = datetime.now().astimezone()
    next_year = now.year + 1 if now.month == 12 else now.year
    next_month = now.month + 1 if now.month < 12 else 1
    return f"{next_year:04d}-{next_month:02d}-{day:02d}"


def open_delta_task_page(context, page) -> None:
    def handle_route(route):
        if route.request.resource_type == "document":
            route.fulfill(
                status=200,
                content_type="text/html; charset=utf-8",
                body=TASK_PAGE_HTML,
            )
        else:
            route.fulfill(status=204, body="")

    context.route("https://www.delta.com/**", handle_route)
    try:
        page.goto(TASK_URL, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        pass
    page.wait_for_function("Boolean(window.__tuaTaskReady)", timeout=10000)
    page.wait_for_timeout(500)


def apply_solved_state(page) -> None:
    page.evaluate(
        """(payload) => {
            history.replaceState({}, "", payload.visibleUrl);
            window.__tuaApplySolvedState(payload);
        }""",
        {
            "fromInput": "Seattle",
            "toInput": "New York",
            "dateValue": build_next_month_date_string(5),
            "fareMode": "miles",
            "visibleUrl": SOLVED_VISIBLE_URL,
        },
    )
    page.wait_for_timeout(500)


def set_state(mode: str) -> None:
    if mode not in {"task", "solved"}:
        raise ValueError(f"Unsupported mode: {mode}")

    with sync_playwright() as playwright:
        browser, _ = ensure_browser_running(playwright)
        context = browser.contexts[0]

        first_page = reset_tabs(context)
        open_delta_task_page(context, first_page)
        if mode == "solved":
            apply_solved_state(first_page)
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
