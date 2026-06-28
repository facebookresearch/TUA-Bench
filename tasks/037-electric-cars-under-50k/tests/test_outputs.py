# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(
    "desktopenv.chrome_find_electric_cars_under_50000_within_50_miles_10001"
)

RESULT_CONFIG = {
    "type": "active_tab_url_parse",
    "goto_prefix": "https://www.",
    "parse_keys": [
        "list_price_max",
        "maximum_distance",
        "zip",
        "fuel_slugs[]",
    ],
}
EXPECTED = {
    "type": "rule",
    "rules": {
        "expected": {
            "list_price_max": "50000",
            "maximum_distance": "50",
            "zip": "10001",
            "fuel_slugs[]": "electric",
        }
    },
}
SANITY_PASS_URL = (
    "https://www.cars.com/shopping/results/"
    "?list_price_max=50000&maximum_distance=50&zip=10001&fuel_slugs%5B%5D=electric"
)
SANITY_FAIL_URL = (
    "https://www.cars.com/shopping/results/"
    "?list_price_max=40000&maximum_distance=25&zip=10001&fuel_slugs%5B%5D=hybrid"
)
ACTIVE_URL_OVERRIDE_ENV = "ACTIVE_URL_OVERRIDE"
ACTIVE_URL_ARTIFACT = Path("/logs/artifacts/active_url.txt")
PARSED_RESULT_ARTIFACT = Path("/logs/artifacts/parsed_result.json")
VERIFICATION_ARTIFACT = Path("/logs/artifacts/verification_summary.json")


def _write_text_artifact(path: Path, value: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
    except OSError as error:
        logger.debug("Skipping artifact write outside Harbor: %s", error)


def _write_json_artifact(path: Path, value) -> None:
    _write_text_artifact(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


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


def get_active_url_from_accessTree(env, config):
    del env

    active_url_override = os.environ.get(ACTIVE_URL_OVERRIDE_ENV)
    if active_url_override:
        _write_text_artifact(ACTIVE_URL_ARTIFACT, f"{active_url_override}\n")
        return active_url_override

    window_id = _find_chrome_window_id()
    if window_id is None:
        logger.error("No visible Chrome window found on the shared X display")
        _write_text_artifact(ACTIVE_URL_ARTIFACT, "\n")
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
        _write_text_artifact(ACTIVE_URL_ARTIFACT, "\n")
        return None

    goto_prefix = config.get("goto_prefix", "https://")
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", raw_url):
        active_tab_url = raw_url
    elif raw_url.startswith("www."):
        active_tab_url = f"https://{raw_url}"
    else:
        active_tab_url = f"{goto_prefix}{raw_url}"

    logger.info("Active tab url now: %s", active_tab_url)
    _write_text_artifact(ACTIVE_URL_ARTIFACT, f"{active_tab_url}\n")
    return active_tab_url


def get_active_tab_url_parse(env, config: Dict[str, Any]):
    active_tab_url = get_active_url_from_accessTree(env, config)
    if active_tab_url is None:
        return None

    parsed_url = urlparse(active_tab_url)
    query_params = parse_qs(parsed_url.query)
    keys_of_interest = [key for key in config["parse_keys"]]
    extracted_params = {key: query_params.get(key, [""])[0] for key in keys_of_interest}
    if "replace" in config:
        for key in config["replace"].keys():
            value = extracted_params.pop(key)
            extracted_params[config["replace"][key]] = value
    if config.get("split_list", False):
        extracted_params = {key: extracted_params[key].split(",") for key in extracted_params.keys()}
    return extracted_params


def check_direct_json_object(result, rules) -> float:
    logger.info(f"[DEBUG] check_direct_json_object called with result: {result}")
    logger.info(f"[DEBUG] check_direct_json_object called with rules: {rules}")

    if isinstance(result, str):
        result = result.strip()
        result = result.replace("'", '"')
        result = json.loads(result)

    logger.info(f"[DEBUG] Processed result: {result}")

    if result is None:
        logger.info("[DEBUG] Result is None, returning 0.0")
        return 0.0

    try:
        expected_json = rules.get("expected", {})
        if expected_json:
            for key, value in expected_json.items():
                if value == "__EVALUATION_FAILED__":
                    logger.error(
                        f"[DEBUG] Expected value for key '{key}' indicates evaluation failure, returning 0.0"
                    )
                    return 0.0
    except Exception as e:
        logger.error(f"[DEBUG] Error checking for evaluation failure indicator: {e}")
        return 0.0
    try:
        expect_in_result = rules.get("expect_in_result", False)
        logger.info(f"[DEBUG] expect_in_result: {expect_in_result}")

        if not expect_in_result:
            expected_json = rules["expected"]
            logger.info(f"[DEBUG] Expected JSON: {expected_json}")

            for key in expected_json.keys():
                expected_value = expected_json.get(key)
                actual_value = result.get(key)
                logger.info(
                    f"[DEBUG] Checking key '{key}': expected='{expected_value}', actual='{actual_value}'"
                )

                if expected_json.get("ignore_list_order", False):
                    expected_value = sorted(expected_value)
                    result_value = sorted(result.get(key))
                    logger.info(
                        f"[DEBUG] Comparing lists (sorted): expected={expected_value}, actual={result_value}"
                    )
                    if expected_value != result_value:
                        logger.info(f"[DEBUG] List comparison failed for key '{key}', returning 0.0")
                        return 0.0
                else:
                    if expected_value != actual_value:
                        logger.info(
                            f"[DEBUG] Value comparison failed for key '{key}': expected='{expected_value}', "
                            f"actual='{actual_value}', returning 0.0"
                        )
                        return 0.0
                    else:
                        logger.info(f"[DEBUG] Value comparison passed for key '{key}'")

            logger.info("[DEBUG] All comparisons passed, returning 1.0")
            return 1.0
        else:
            expected_json = rules["expected"]
            logger.info(f"[DEBUG] Expected JSON (expect_in_result mode): {expected_json}")

            for key in expected_json.keys():
                if isinstance(expected_json.get(key), list):
                    flag = 0
                    expected_value_list = expected_json.get(key)
                    logger.info(
                        f"[DEBUG] Checking list key '{key}': expected_list={expected_value_list}, "
                        f"actual='{result.get(key)}'"
                    )
                    for each_expected_value in expected_value_list:
                        if isinstance(result.get(key), list) and each_expected_value in result.get(key):
                            flag = 1
                            logger.info(
                                f"[DEBUG] Found expected value '{each_expected_value}' in result list for key '{key}'"
                            )
                            break
                        elif isinstance(result.get(key), str) and each_expected_value == result.get(key):
                            flag = 1
                            logger.info(
                                f"[DEBUG] Found expected value '{each_expected_value}' matches result string for key '{key}'"
                            )
                            break
                    if flag == 0:
                        logger.info(
                            f"[DEBUG] No expected values found in result for key '{key}', returning 0.0"
                        )
                        return 0.0
                elif isinstance(expected_json.get(key), str):
                    expected_str = expected_json.get(key)
                    actual_str = result.get(key)
                    logger.info(
                        f"[DEBUG] Checking string key '{key}': expected='{expected_str}', actual='{actual_str}'"
                    )
                    if expected_str not in actual_str:
                        logger.info(
                            f"[DEBUG] Expected string '{expected_str}' not found in actual string "
                            f"'{actual_str}' for key '{key}', returning 0.0"
                        )
                        return 0.0
                else:
                    logger.debug("check_direct_json_object: expected value type not supported")
                    return 0.0
            logger.info("[DEBUG] All expect_in_result comparisons passed, returning 1.0")
            return 1.0
    except Exception as e:
        logger.debug(f"check_direct_json_object: result is not a valid json object, error: {e}")
        return 0.0


def evaluate_osworld_conditions():
    result = get_active_tab_url_parse(None, RESULT_CONFIG)
    score = check_direct_json_object(result, EXPECTED["rules"])
    return result, score


def evaluate_osworld_conditions_with_url(url: str):
    previous_url = os.environ.get(ACTIVE_URL_OVERRIDE_ENV)
    os.environ[ACTIVE_URL_OVERRIDE_ENV] = url
    try:
        return evaluate_osworld_conditions()
    finally:
        if previous_url is None:
            os.environ.pop(ACTIVE_URL_OVERRIDE_ENV, None)
        else:
            os.environ[ACTIVE_URL_OVERRIDE_ENV] = previous_url


def test_sanity_url_roundtrip():
    pass_result, pass_score = evaluate_osworld_conditions_with_url(SANITY_PASS_URL)
    fail_result, fail_score = evaluate_osworld_conditions_with_url(SANITY_FAIL_URL)

    assert check_direct_json_object(pass_result, EXPECTED["rules"]) == 1.0
    assert pass_score == 1.0
    assert check_direct_json_object(fail_result, EXPECTED["rules"]) == 0.0
    assert fail_score == 0.0


def test_main():
    result, score = evaluate_osworld_conditions()

    _write_json_artifact(PARSED_RESULT_ARTIFACT, result)
    _write_json_artifact(
        VERIFICATION_ARTIFACT,
        {
            "result": result,
            "expected": EXPECTED["rules"],
            "score": score,
        },
    )

    assert score == 1.0, (
        "Chrome active tab URL does not satisfy the exact OSWorld active_tab_url_parse "
        "check_direct_json_object rule"
    )
