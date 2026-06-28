# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import logging
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger("desktopenv.chrome_open_saved_passwords")

RULE = {
    "type": "url",
    "url": "chrome://password-manager/passwords",
}
RESULT_CONFIG = {"goto_prefix": ""}
ACTIVE_URL_ARTIFACT = Path("/logs/artifacts/active_url.txt")


def is_expected_active_tab_approximate(active_tab_info, rule):
    if not active_tab_info:
        return 0.0

    match_type = rule["type"]

    if match_type == "url":
        expected_url = rule["url"]
        if isinstance(active_tab_info, dict):
            actual_url = active_tab_info.get("url", None)
        else:
            actual_url = active_tab_info

        def strip_query(url):
            parsed = urlparse(url)
            return urlunparse(parsed._replace(query=""))

        if strip_query(expected_url) == strip_query(actual_url):
            return 1.0
        else:
            return 0.0

    logger.error("Unknown type: %s", match_type)
    return 0.0


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


def test_main():
    active_tab_url = get_active_url_from_accessTree(RESULT_CONFIG)
    assert (
        is_expected_active_tab_approximate(active_tab_url, RULE) == 1.0
    ), "Chrome active tab URL does not satisfy OSWorld is_expected_active_tab_approximate"
