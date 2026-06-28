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

SPEC = json.loads(Path("/usr/local/share/tua/task_spec.json").read_text(encoding="utf-8"))
REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
PROFILE_DIR = Path.home() / ".config" / "google-chrome"


def _require_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required for chrome startup state") from exc
    return sync_playwright


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
    sync_playwright = _require_playwright()
    with sync_playwright() as playwright:
        browser, _ = ensure_browser_running(playwright)
        context = browser.contexts[0]
        first = reset_tabs(context)
        navigate(first, urls[0])
        for url in urls[1:]:
            page = context.new_page()
            navigate(page, url)
        time.sleep(2)


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
    thunderbird = startup.get("thunderbird")
    if thunderbird:
        launch_thunderbird(thunderbird)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
