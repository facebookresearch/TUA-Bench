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

logger = logging.getLogger("desktopenv.chrome_show_tamiflu_side_effects")

RESULT_CONFIG = {
    "type": "active_url_from_accessTree",
    "goto_prefix": "https://www.",
}
EXPECTED_RULES = [
    {
        "expected": [
            r"^https://(www\.)?drugs\.com/tamiflu\.html#side-effects",
        ]
    },
    {
        "expected": [
            r"^https://(www\.)?drugs\.com/sfx/tamiflu-side-effects\.html",
        ]
    },
    {
        "expected": [
            r"^https://(www\.)?drugs\.com/sfx/tamiflu-side-effects\.html#common-side-effects",
        ]
    },
]
SANITY_PASS_URLS = [
    "https://www.drugs.com/tamiflu.html#side-effects",
    "https://www.drugs.com/sfx/tamiflu-side-effects.html",
    "https://www.drugs.com/sfx/tamiflu-side-effects.html#common-side-effects",
]
SANITY_FAIL_URL = "https://www.drugs.com/"
ACTIVE_URL_ARTIFACT = Path("/logs/artifacts/active_url.txt")


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
    for expected_url, rules in zip(SANITY_PASS_URLS, EXPECTED_RULES):
        assert is_expected_url_pattern_match(expected_url, rules) == 1.0
    assert all(
        is_expected_url_pattern_match(SANITY_FAIL_URL, rules) == 0.0 for rules in EXPECTED_RULES
    )


def test_main():
    active_tab_url = get_active_url_from_accessTree(RESULT_CONFIG)
    assert any(
        is_expected_url_pattern_match(active_tab_url, rules) == 1.0 for rules in EXPECTED_RULES
    ), "Chrome active tab URL does not satisfy OSWorld is_expected_url_pattern_match"
