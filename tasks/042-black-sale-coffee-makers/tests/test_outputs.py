# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import os
import json
import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, unquote, urlparse

logger = logging.getLogger("desktopenv.chrome_list_black_sale_drip_coffee_makers")

RESULT_CONFIG_URL = {
    "type": "active_tab_url_parse",
    "goto_prefix": "https://www.",
    "parse_keys": [
        "q",
    ],
}
RESULT_CONFIG_FILTERS = {
    "type": "active_tab_html_parse",
    "goto_prefix": "https://www.",
    "category": "class",
    "class_multiObject_search_exist": {
        "fT28tf": [
            "Black",
            "$25 - $60",
            "On sale",
            "is_other_exist",
        ]
    },
}
EXPECTED_URL = {
    "type": "rule",
    "rules": {
        "expected": {
            "q": "drip coffee maker",
        },
        "expect_in_result": True,
    },
}
EXPECTED_FILTERS = {
    "type": "rule",
    "rules": {
        "expected": {
            "Black": True,
            "$25 - $60": True,
            "On sale": True,
            "is_other_exist": False,
        }
    },
}

REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
ACTIVE_URL_ARTIFACT = Path("/logs/artifacts/active_url.txt")
URL_RESULT_ARTIFACT = Path("/logs/artifacts/url_result.json")
CLASS_RESULT_ARTIFACT = Path("/logs/artifacts/class_result.json")
VERIFICATION_ARTIFACT = Path("/logs/artifacts/verification_summary.json")


def _write_text_artifact(path: Path, value: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
    except OSError as error:
        logger.debug("Skipping artifact write outside Harbor: %s", error)


def _write_json_artifact(path: Path, value) -> None:
    _write_text_artifact(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def check_direct_json_object(result, rules) -> float:
    """
    One of the most commonly used function to evalute.
    Compare two json objects directly.
    """
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
                        "[DEBUG] Expected value for key '%s' indicates evaluation failure, returning 0.0",
                        key,
                    )
                    return 0.0
    except Exception as error:
        logger.error(f"[DEBUG] Error checking for evaluation failure indicator: {error}")
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
                            "[DEBUG] Value comparison failed for key '%s': expected='%s', actual='%s', returning 0.0",
                            key,
                            expected_value,
                            actual_value,
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
                        f"[DEBUG] Checking list key '{key}': expected_list={expected_value_list}, actual='{result.get(key)}'"
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
                            "[DEBUG] Expected string '%s' not found in actual string '%s' for key '%s', returning 0.0",
                            expected_str,
                            actual_str,
                            key,
                        )
                        return 0.0
                else:
                    logger.debug("check_direct_json_object: expected value type not supported")
                    return 0.0
            logger.info("[DEBUG] All expect_in_result comparisons passed, returning 1.0")
            return 1.0
    except Exception as error:
        logger.debug(f"check_direct_json_object: result is not a valid json object, error: {error}")
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


def get_active_url_from_accessTree(env, config):
    del env

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
    _write_text_artifact(ACTIVE_URL_ARTIFACT, f"{active_tab_url}\n")
    return active_tab_url


def get_active_tab_url_parse(env, config: Dict[str, Any]):
    del env

    active_tab_url = get_active_url_from_accessTree(None, config)
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


def get_active_tab_html_parse(env, config: Dict[str, Any]):
    del env

    active_tab_url = get_active_url_from_accessTree(None, config)
    logger.info(f"[DEBUG] get_active_url_from_accessTree returned: {active_tab_url}")
    if not isinstance(active_tab_url, str):
        return None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright is not available for active tab HTML parsing")
        return None

    def normalize_url(url: str) -> str:
        return unquote(url).rstrip("/")

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.connect_over_cdp(REMOTE_DEBUGGING_URL)
        except Exception as error:
            logger.error("Failed to connect to Chrome over CDP: %s", error)
            return {}

        target_page = None
        for context in browser.contexts:
            for page in context.pages:
                try:
                    if normalize_url(page.url) == normalize_url(active_tab_url):
                        target_page = page
                        break
                except Exception:
                    continue
            if target_page is not None:
                break

        if target_page is None:
            logger.error("Could not find target tab matching URL: %s", active_tab_url)
            return {}

        return_json = {}

        def safely_get_text_content(selector: str):
            try:
                elements = target_page.query_selector_all(selector)
                values = []
                for element in elements:
                    if not element:
                        continue
                    text = element.text_content()
                    if text is None:
                        continue
                    values.append(text.strip())
                return values
            except Exception as error:
                logger.warning("Error getting text content for selector '%s': %s", selector, error)
                return []

        if config["category"] == "class":
            class_multiObject_search_exist = config.get("class_multiObject_search_exist", {})
            for class_name, object_list in class_multiObject_search_exist.items():
                elements_texts = safely_get_text_content("." + class_name)
                logger.info(f"[DEBUG] Found elements with class '{class_name}': {elements_texts}")
                logger.info(
                    f"[DEBUG] Expected elements: {[obj for obj in object_list if obj != 'is_other_exist']}"
                )

                for each_object in object_list:
                    if each_object == "is_other_exist":
                        continue
                    if each_object in elements_texts:
                        return_json[each_object] = True
                    else:
                        return_json[each_object] = False
                if "is_other_exist" in object_list:
                    extra_elements = []
                    for each_element in elements_texts:
                        if each_element not in object_list:
                            extra_elements.append(each_element)
                            return_json["is_other_exist"] = True
                    if extra_elements:
                        logger.warning(
                            f"[DEBUG] Found unexpected elements not in expected list: {extra_elements}"
                        )
                    else:
                        logger.info("[DEBUG] No unexpected elements found")
                    if "is_other_exist" not in return_json.keys():
                        return_json["is_other_exist"] = False

        logger.info(f"[DEBUG] get_active_tab_html_parse final result: {return_json}")
        return return_json


def evaluate_results(url_result, class_result):
    return {
        "url_score": check_direct_json_object(url_result, EXPECTED_URL["rules"]),
        "class_score": check_direct_json_object(class_result, EXPECTED_FILTERS["rules"]),
    }


def test_main():
    url_result = get_active_tab_url_parse(None, RESULT_CONFIG_URL)
    class_result = get_active_tab_html_parse(None, RESULT_CONFIG_FILTERS)
    verification_summary = evaluate_results(url_result, class_result)

    _write_json_artifact(URL_RESULT_ARTIFACT, url_result)
    _write_json_artifact(CLASS_RESULT_ARTIFACT, class_result)
    _write_json_artifact(
        VERIFICATION_ARTIFACT,
        {
            "url_result": url_result,
            "class_result": class_result,
            "expected_url": EXPECTED_URL["rules"],
            "expected_filters": EXPECTED_FILTERS["rules"],
            "scores": verification_summary,
        },
    )

    assert verification_summary["url_score"] == 1.0, (
        "Google Shopping query does not satisfy OSWorld check_direct_json_object"
    )
    assert verification_summary["class_score"] == 1.0, (
        "Google Shopping filter chips do not satisfy OSWorld check_direct_json_object"
    )
