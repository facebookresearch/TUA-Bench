# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import os
import copy
import json
import logging
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, TypeVar
from urllib.parse import unquote

import pytz

logger = logging.getLogger("desktopenv.chrome_find_seattle_new_york_miles_flights")

RESULT_CONFIG = {
    "type": "active_tab_html_parse",
    "goto_prefix": "https://www.",
    "category": "class",
    "class_singleObject": {
        "mach-flight-context-info__wrapper--date": "time",
        "mach-global-tabs-small__wrapper__tab--active": "category",
    },
    "class_multiObject_child": {
        "mach-flight-context-info__wrapper__info--separator": {
            "0": "start",
            "1": "end",
        }
    },
}
EXPECTED = {
    "type": "rule_relativeTime",
    "rules": {
        "relativeTime": {
            "from": "5th next month",
        },
        "expected": {
            "start": "SEA",
            "end": "NYC",
            "time": "{DoW}, {Month} {Day0D}, {Year}",
            "category": "Miles",
        },
    },
}

REMOTE_DEBUGGING_URL = os.environ.get(
    "REMOTE_DEBUGGING_URL",
    f"http://127.0.0.1:{os.environ.get('TUA_CHROME_REMOTE_DEBUGGING_PORT', '1337')}",
)
ACTIVE_URL_ARTIFACT = Path("/logs/artifacts/active_url.txt")
PARSED_RESULT_ARTIFACT = Path("/logs/artifacts/parsed_result.json")
VERIFICATION_ARTIFACT = Path("/logs/artifacts/verification_summary.json")

R = TypeVar("Rule")


class _LocalController:
    def execute_python_command(self, command: str):
        del command
        return {"output": f"{datetime.now().astimezone().isoformat()}\n"}


class _LocalEnv:
    controller = _LocalController()


LOCAL_ENV = _LocalEnv()

day_of_week_mapping = {
    0: "Mon",
    1: "Tue",
    2: "Wed",
    3: "Thu",
    4: "Fri",
    5: "Sat",
    6: "Sun",
}

month_mapping = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

Month_Mapping_Full = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

month_mapping_full = {
    1: "january",
    2: "february",
    3: "march",
    4: "april",
    5: "may",
    6: "june",
    7: "july",
    8: "august",
    9: "september",
    10: "october",
    11: "november",
    12: "december",
}

relativeTime_to_IntDay = {
    "tomorrow": 1,
    "5th next month": "special",
    "10th next month": "special",
    "11th next month": "special",
    "this month": "special",
    "this Saturday": "special",
    "this Sunday": "special",
    "next Monday": "special",
    "next Friday": "special",
    "next Saturday": "special",
    "next Sunday": "special",
    "next week Friday": "special",
    "next week Saturday": "special",
    "next week Sunday": "special",
    "first monday four months later": "special",
    "first monday eight months later": "special",
    "next Monday split": "special",
    "next Friday split": "special",
}


def _write_text_artifact(path: Path, value: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
    except OSError as error:
        logger.debug("Skipping artifact write outside Harbor: %s", error)


def _write_json_artifact(path: Path, value) -> None:
    _write_text_artifact(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def get_rule(env, config: Dict[str, R]) -> R:
    del env
    return config["rules"]


def _build_datetime_like(reference_now: datetime, year: int, month: int, day: int) -> datetime:
    if reference_now.tzinfo is not None:
        return datetime(year, month, day, tzinfo=reference_now.tzinfo)
    return datetime(year, month, day)


def _get_vm_now_datetime(env) -> datetime | None:
    try:
        if env is None or not getattr(env, "controller", None):
            return None
        result = env.controller.execute_python_command(
            "from datetime import datetime; print(datetime.now().astimezone().isoformat())"
        )
        if not result:
            return None
        output = result.get("output", "").strip()
        if not output:
            return None
        return datetime.fromisoformat(output)
    except Exception as error:
        logger.warning("Failed to get VM datetime, falling back to host timezone flow: %s", error)
        return None


def get_timezone_from_ip() -> str:
    logger.info("Using UTC as fallback timezone")
    return "UTC"


def get_timezone_from_config(config: Dict, default_timezone: str = None) -> str:
    if "timezone" in config.get("rules", {}):
        timezone = config["rules"]["timezone"]
        logger.info(f"Using timezone from config: {timezone}")
        return timezone

    if default_timezone:
        logger.info(f"Using provided default timezone: {default_timezone}")
        return default_timezone

    return get_timezone_from_ip()


def get_rule_relativeTime(env, config: Dict[str, R]) -> R:
    logger.info(f"[DEBUG] get_rule_relativeTime called with config: {config}")

    relativeRules = config["rules"]
    relativeTime = relativeRules["relativeTime"]

    logger.info(f"[DEBUG] relativeTime: {relativeTime}")

    timezone_str = None
    explicit_timezone = config.get("rules", {}).get("timezone")
    if explicit_timezone:
        timezone_str = explicit_timezone
        try:
            timezone = pytz.timezone(timezone_str)
            now = datetime.now(timezone)
            logger.info(f"Using explicit config timezone: {timezone_str}")
            logger.info(f"Current time in {timezone_str}: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except pytz.exceptions.UnknownTimeZoneError:
            logger.error(f"Unknown timezone: {timezone_str}, falling back to UTC")
            timezone = pytz.UTC
            now = datetime.now(timezone)
            logger.info(f"Current time in UTC fallback: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    else:
        now = _get_vm_now_datetime(env)
        if now is not None:
            logger.info(f"Using VM local datetime: {now.isoformat()}")
        else:
            timezone_str = get_timezone_from_config(config)
            try:
                timezone = pytz.timezone(timezone_str)
                now = datetime.now(timezone)
                logger.info(f"Falling back to host timezone flow: {timezone_str}")
                logger.info(f"Current time in {timezone_str}: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            except pytz.exceptions.UnknownTimeZoneError:
                logger.error(f"Unknown timezone: {timezone_str}, falling back to UTC")
                timezone = pytz.UTC
                now = datetime.now(timezone)
                logger.info(f"Current time in UTC fallback: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    if "to" not in relativeTime.keys():
        start_relative_time = relativeTime["from"]
        logger.info(f"Processing single time: '{start_relative_time}'")

        if relativeTime_to_IntDay[start_relative_time] != "special":
            start_relative_time_IntDat = relativeTime_to_IntDay[start_relative_time]
            timediff = timedelta(days=start_relative_time_IntDat)
            absoluteDay = now + timediff
            logger.info(
                f"Simple calculation: {start_relative_time} = {start_relative_time_IntDat} days -> {absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )
        else:
            if start_relative_time == "5th next month":
                next_year = now.year + 1 if now.month == 12 else now.year
                next_month = now.month + 1 if now.month < 12 else 1
                next_day = 5
                absoluteDay = _build_datetime_like(now, next_year, next_month, next_day)
                logger.info(f"5th next month: {absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            elif start_relative_time == "10th next month":
                next_year = now.year + 1 if now.month == 12 else now.year
                next_month = now.month + 1 if now.month < 12 else 1
                next_day = 10
                absoluteDay = _build_datetime_like(now, next_year, next_month, next_day)
                logger.info(f"10th next month: {absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            elif start_relative_time == "this month":
                absoluteDay = now
                logger.info(f"This month: {absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            elif start_relative_time == "next Monday":
                days_until_monday = (6 - now.weekday()) + 1
                absoluteDay = now + timedelta(days=days_until_monday)
                logger.info(
                    f"Next Monday: current weekday={now.weekday()}, days to add={days_until_monday} -> {absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            elif start_relative_time == "first monday four months later":
                next_year = now.year + 1 if now.month >= 9 else now.year
                next_month = (now.month + 4) % 12
                temp_date = _build_datetime_like(now, next_year, next_month, 1)
                days_to_monday = ((6 - temp_date.weekday()) + 1) % 7
                absoluteDay = temp_date + timedelta(days=days_to_monday)
                logger.info(
                    f"First Monday 4 months later: {next_year}-{next_month:02d} -> {absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            elif start_relative_time == "first monday eight months later":
                next_year = now.year + 1 if now.month >= 5 else now.year
                next_month = (now.month + 8) % 12
                temp_date = _build_datetime_like(now, next_year, next_month, 1)
                days_to_monday = ((6 - temp_date.weekday()) + 1) % 7
                absoluteDay = temp_date + timedelta(days=days_to_monday)
                logger.info(
                    f"First Monday 8 months later: {next_year}-{next_month:02d} -> {absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            else:
                absoluteDay = now
        time_value = relativeRules["expected"]["time"]
        if isinstance(time_value, list):
            regular_time = [apply_rules_to_timeFormat(t, absoluteDay) for t in time_value]
        else:
            regular_time = apply_rules_to_timeFormat(time_value, absoluteDay)
        logger.info(f"Final formatted time: {regular_time}")
        config["rules"]["expected"]["time"] = regular_time

    logger.info(f"[DEBUG] Final config rules: {config['rules']}")
    return config["rules"]


def apply_rules_to_timeFormat(timeFormat: str, absoluteDay: datetime):
    timeFormat = timeFormat.replace("{DoW}", day_of_week_mapping[absoluteDay.weekday()], 1)
    timeFormat = timeFormat.replace("{Month}", month_mapping[absoluteDay.month], 1)
    timeFormat = timeFormat.replace("{DayD}", str(absoluteDay.day), 1)
    timeFormat = timeFormat.replace("{Year}", str(absoluteDay.year), 1)
    timeFormat = timeFormat.replace(
        "{Month0D}",
        "0" + str(absoluteDay.month) if absoluteDay.month < 10 else str(absoluteDay.month),
        1,
    )
    timeFormat = timeFormat.replace("{month}", month_mapping_full[absoluteDay.month], 1)
    timeFormat = timeFormat.replace("{MonthFull}", Month_Mapping_Full[absoluteDay.month], 1)
    timeFormat = timeFormat.replace(
        "{Day0D}",
        "0" + str(absoluteDay.day) if absoluteDay.day < 10 else str(absoluteDay.day),
        1,
    )
    timeFormat = timeFormat.replace("{MonthD}", str(absoluteDay.month), 1)
    return timeFormat


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

        def safely_get_direct_text_nodes_playwright(selector: str):
            try:
                elements = target_page.query_selector_all(selector)
                results = []
                for element in elements:
                    texts = element.evaluate(
                        """
                        (node) => Array.from(node.childNodes)
                            .filter((child) => child.nodeType === Node.TEXT_NODE)
                            .map((child) => child.textContent.trim())
                            .filter(Boolean)
                        """
                    )
                    results.append(texts)
                return results[0] if results else []
            except Exception as error:
                logger.warning("Error getting direct text nodes for selector '%s': %s", selector, error)
                return []

        if config["category"] == "class":
            class_multiObject_child = config.get("class_multiObject_child", {})
            for class_name, object_dict in class_multiObject_child.items():
                elements_texts = safely_get_direct_text_nodes_playwright("." + class_name)
                for order_key, key in object_dict.items():
                    index = int(order_key)
                    if len(elements_texts) > index:
                        return_json[key] = elements_texts[index]
                    else:
                        return_json[key] = ""

            class_singleObject = config.get("class_singleObject", {})
            for class_name, key in class_singleObject.items():
                element_text = safely_get_text_content("." + class_name)
                return_json[key] = element_text[0] if element_text else ""

        return return_json


def build_expected_rules():
    return get_rule_relativeTime(LOCAL_ENV, copy.deepcopy(EXPECTED))


def _elements_with_class(root: ET.Element, class_name: str):
    return [
        element
        for element in root.iter()
        if class_name in element.attrib.get("class", "").split()
    ]


def _text_content(element: ET.Element) -> str:
    return "".join(element.itertext()).strip()


def _direct_text_nodes(element: ET.Element):
    values = []
    if element.text and element.text.strip():
        values.append(element.text.strip())
    for child in element:
        if child.tail and child.tail.strip():
            values.append(child.tail.strip())
    return values


def extract_result_from_static_html(html: str, config: Dict[str, Any]):
    root = ET.fromstring(html)
    result = {}

    class_multiObject_child = config.get("class_multiObject_child", {})
    for class_name, object_dict in class_multiObject_child.items():
        elements = _elements_with_class(root, class_name)
        texts = _direct_text_nodes(elements[0]) if elements else []
        for order_key, key in object_dict.items():
            index = int(order_key)
            result[key] = texts[index] if len(texts) > index else ""

    class_singleObject = config.get("class_singleObject", {})
    for class_name, key in class_singleObject.items():
        elements = _elements_with_class(root, class_name)
        result[key] = _text_content(elements[0]) if elements else ""

    return result


def build_static_html(start: str, end: str, time_value: str, category: str) -> str:
    return f"""<html>
  <body>
    <div class="mach-flight-context-info__wrapper__info mach-flight-context-info__wrapper__info--separator">{start}<span class="route-separator">to</span>{end}</div>
    <div class="mach-flight-context-info__wrapper--date">{time_value}</div>
    <div class="mach-global-tabs-small__wrapper__tab mach-global-tabs-small__wrapper__tab--active">{category}</div>
  </body>
</html>"""


def test_sanity_static_html_roundtrip():
    expected_rules = build_expected_rules()
    expected_values = expected_rules["expected"]

    good_html = build_static_html(
        expected_values["start"],
        expected_values["end"],
        expected_values["time"],
        expected_values["category"],
    )
    bad_html = build_static_html(
        expected_values["start"],
        "BOS",
        expected_values["time"],
        "Cash",
    )

    assert (
        check_direct_json_object(extract_result_from_static_html(good_html, RESULT_CONFIG), expected_rules)
        == 1.0
    )
    assert (
        check_direct_json_object(extract_result_from_static_html(bad_html, RESULT_CONFIG), expected_rules)
        == 0.0
    )


def test_main():
    parsed_result = get_active_tab_html_parse(None, RESULT_CONFIG)
    expected_rules = build_expected_rules()
    score = check_direct_json_object(parsed_result, expected_rules)

    _write_json_artifact(PARSED_RESULT_ARTIFACT, parsed_result)
    _write_json_artifact(
        VERIFICATION_ARTIFACT,
        {
            "active_url": ACTIVE_URL_ARTIFACT.read_text(encoding="utf-8").strip()
            if ACTIVE_URL_ARTIFACT.exists()
            else "",
            "expected": expected_rules,
            "parsed_result": parsed_result,
            "score": score,
        },
    )

    assert score == 1.0, (
        "Delta flight result HTML does not satisfy OSWorld check_direct_json_object"
    )
