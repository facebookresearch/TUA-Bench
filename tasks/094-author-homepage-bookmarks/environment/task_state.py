#!/opt/venv/bin/python
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


SPEC = json.loads(Path("/usr/local/share/tua/task_spec.json").read_text(encoding="utf-8"))
REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
PROFILE_DIR = Path.home() / ".config" / "google-chrome"


def launch_browser() -> subprocess.Popen:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    for path in PROFILE_DIR.glob("Singleton*"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    command = [
        "/usr/local/bin/google-chrome",
        f"--user-data-dir={PROFILE_DIR}",
        "--profile-directory=Default",
        f"--remote-debugging-port={os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
    ]
    return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


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
    raise RuntimeError("Timed out connecting to Chromium")


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


def navigate(page, url: str) -> None:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception:
        pass


def set_chrome_urls(urls: list[str]) -> None:
    if not urls:
        return
    with sync_playwright() as playwright:
        browser, _ = ensure_browser_running(playwright)
        context = browser.contexts[0]
        first = reset_tabs(context)
        navigate(first, urls[0])
        for url in urls[1:]:
            page = context.new_page()
            navigate(page, url)
        time.sleep(2)


def run_best_effort(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return subprocess.CompletedProcess(command, 1, "", "")


def open_path(path: str) -> None:
    opener = shutil.which("xdg-open")
    if opener is None:
        return
    try:
        subprocess.Popen([opener, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return


def find_window_id(window_name: str, timeout_sec: float = 10.0) -> str | None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        result = run_best_effort(["xdotool", "search", "--onlyvisible", "--name", window_name])
        window_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if window_ids:
            return window_ids[-1]
        time.sleep(0.5)
    return None


def get_window_size(window_id: str) -> tuple[int, int] | None:
    result = run_best_effort(["xdotool", "getwindowgeometry", "--shell", window_id])
    width = None
    height = None
    for line in result.stdout.splitlines():
        if line.startswith("WIDTH="):
            width = int(line.split("=", 1)[1])
        elif line.startswith("HEIGHT="):
            height = int(line.split("=", 1)[1])
    if width is None or height is None:
        return None
    return width, height


def prime_pdf_view(path: str, actions: dict[str, object]) -> None:
    pdf_path = Path(path)
    if not pdf_path.exists():
        return

    open_path(str(pdf_path))
    time.sleep(2)

    window_id = find_window_id(pdf_path.name)
    if window_id is None:
        return

    run_best_effort(["xdotool", "windowactivate", "--sync", window_id])

    if actions.get("fullscreen"):
        run_best_effort(["xdotool", "key", "--window", window_id, "F11"])
        time.sleep(0.5)

    if actions.get("click_center"):
        size = get_window_size(window_id)
        if size is not None:
            width, height = size
            run_best_effort(
                ["xdotool", "mousemove", "--window", window_id, str(width // 2), str(height // 2)]
            )
            run_best_effort(["xdotool", "click", "--window", window_id, "1"])
            time.sleep(0.5)

    try:
        scroll_clicks = int(actions.get("scroll_down_clicks", 0) or 0)
    except (TypeError, ValueError):
        scroll_clicks = 0
    for _ in range(max(scroll_clicks, 0)):
        run_best_effort(["xdotool", "click", "--window", window_id, "5"])


def resolve_profile_dir() -> Path:
    thunderbird_root = Path.home() / ".thunderbird"
    profiles_ini = thunderbird_root / "profiles.ini"
    if not profiles_ini.exists():
        raise RuntimeError("Missing Thunderbird profiles.ini")
    import configparser
    config = configparser.ConfigParser(interpolation=None)
    config.read(profiles_ini, encoding="utf-8")
    for section_name in config.sections():
        if section_name.startswith("Install"):
            default_path = config[section_name].get("Default")
            if default_path:
                return thunderbird_root / default_path
    for section_name in config.sections():
        if section_name.startswith("Profile") and config[section_name].get("Default") == "1":
            return thunderbird_root / config[section_name]["Path"]
    raise RuntimeError("Could not resolve Thunderbird profile")


def launch_thunderbird(mode_config: dict[str, object]) -> None:
    profile_dir = resolve_profile_dir()
    for filename in ("lock", ".parentlock"):
        (profile_dir / filename).unlink(missing_ok=True)
    command = ["/usr/bin/thunderbird", "-profile", str(profile_dir)]
    if mode_config.get("mode") == "compose":
        compose_bits = []
        for key in ("from", "to", "subject", "body", "attachment"):
            value = mode_config.get(key)
            if value:
                escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
                compose_bits.append(f"{key}='{escaped}'")
        command.extend(["-compose", ",".join(compose_bits)])
    with open("/tmp/thunderbird.log", "a", encoding="utf-8") as log_file:
        subprocess.Popen(command, stdout=log_file, stderr=log_file)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["task"])
    parser.parse_args()
    startup = SPEC.get("startup", {})
    chrome_urls = startup.get("chrome_urls", [])
    if chrome_urls:
        set_chrome_urls(chrome_urls)
    pdf_open_path = startup.get("pdf_open_path")
    if isinstance(pdf_open_path, str) and pdf_open_path:
        pdf_view_setup = startup.get("pdf_view_setup")
        prime_pdf_view(pdf_open_path, pdf_view_setup if isinstance(pdf_view_setup, dict) else {})
    thunderbird = startup.get("thunderbird")
    if thunderbird:
        launch_thunderbird(thunderbird)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
