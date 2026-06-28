# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import copy
import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, TypeVar
from urllib.parse import urlparse

import pytz
import requests

logger = logging.getLogger("desktopenv.chrome_find_manchester_monthly_forecast")

RESULT_CONFIG_TIME = {
    "type": "url_dashPart",
    "goto_prefix": "https://www.",
    "partIndex": -2,
    "needDeleteId": False,
    "returnType": "json",
    "key": "time",
}
RESULT_CONFIG_LOCATION = {
    "type": "active_url_from_accessTree",
    "goto_prefix": "https://www.",
}
EXPECTED_TIME = {
    "type": "rule_relativeTime",
    "rules": {
        "expected": {
            "time": "{month}-weather",
        },
        "relativeTime": {
            "from": "this month",
        },
    },
}
EXPECTED_LOCATION = {
    "type": "rule",
    "rules": {
        "expected": [
            "/manchester/",
        ]
    },
}


class _LocalController:
    def execute_python_command(self, command: str):
        del command
        return {"output": f"{datetime.now().astimezone().isoformat()}\n"}


class _LocalEnv:
    controller = _LocalController()


LOCAL_ENV = _LocalEnv()

R = TypeVar("Rule")

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

SANITY_PASS_URL = (
    "https://www.accuweather.com/en/gb/manchester/m15-6/"
    f"{month_mapping_full[datetime.now().astimezone().month]}-weather/329260?year={datetime.now().astimezone().year}"
)
SANITY_FAIL_URL = "https://www.accuweather.com/en/gb/london/greater-london-weather/328328"
ACTIVE_URL_OVERRIDE_ENV = "ACTIVE_URL_OVERRIDE"
ACTIVE_URL_ARTIFACT = Path("/logs/artifacts/active_url.txt")


def _write_active_url_artifact(value: str) -> None:
    try:
        ACTIVE_URL_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_URL_ARTIFACT.write_text(value, encoding="utf-8")
    except OSError as error:
        logger.debug("Skipping active URL artifact write outside Harbor: %s", error)


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


def get_rule(env, config: Dict[str, R]) -> R:
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
    except Exception as e:
        logger.warning(f"Failed to get VM datetime, falling back to host timezone flow: {e}")
        return None


def get_timezone_from_ip() -> str:
    """
    Get timezone from IP address using IP geolocation API
    Returns timezone string like 'Europe/Zurich' or 'UTC' as fallback
    """
    try:
        response = requests.get("https://ipapi.co/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            timezone = data.get("timezone")
            if timezone:
                logger.info(f"Timezone from IP: {timezone}")
                return timezone
    except Exception as e:
        logger.warning(f"Failed to get timezone from IP: {e}")

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
                f"Simple calculation: {start_relative_time} = {start_relative_time_IntDat} days → "
                f"{absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
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
                    f"Next Monday: current weekday={now.weekday()}, days to add={days_until_monday} → "
                    f"{absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            elif start_relative_time == "first monday four months later":
                next_year = now.year + 1 if now.month >= 9 else now.year
                next_month = (now.month + 4) % 12
                temp_date = _build_datetime_like(now, next_year, next_month, 1)
                days_to_monday = ((6 - temp_date.weekday()) + 1) % 7
                absoluteDay = temp_date + timedelta(days=days_to_monday)
                logger.info(
                    f"First Monday 4 months later: {next_year}-{next_month:02d} → "
                    f"{absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            elif start_relative_time == "first monday eight months later":
                next_year = now.year + 1 if now.month >= 5 else now.year
                next_month = (now.month + 8) % 12
                temp_date = _build_datetime_like(now, next_year, next_month, 1)
                days_to_monday = ((6 - temp_date.weekday()) + 1) % 7
                absoluteDay = temp_date + timedelta(days=days_to_monday)
                logger.info(
                    f"First Monday 8 months later: {next_year}-{next_month:02d} → "
                    f"{absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
        time_value = relativeRules["expected"]["time"]
        if isinstance(time_value, list):
            regular_time = [apply_rules_to_timeFormat(t, absoluteDay) for t in time_value]
        else:
            regular_time = apply_rules_to_timeFormat(time_value, absoluteDay)
        logger.info(f"Final formatted time: {regular_time}")
        config["rules"]["expected"]["time"] = regular_time

    else:
        from_time = relativeTime["from"]
        to_time = relativeTime["to"]
        logger.info(f"Processing time range: from '{from_time}' to '{to_time}'")

        if relativeTime_to_IntDay[from_time] != "special":
            from_time_IntDat = relativeTime_to_IntDay[from_time]
            from_timediff = timedelta(days=from_time_IntDat)
            from_absoluteDay = now + from_timediff
            logger.info(
                f"From time calculation: {from_time} = {from_time_IntDat} days → "
                f"{from_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )
        else:
            if from_time == "this Saturday":
                days_until_saturday = 5 - now.weekday()
                from_absoluteDay = now + timedelta(days=days_until_saturday)
                logger.info(
                    f"This Saturday: current weekday={now.weekday()}, days to add={days_until_saturday} → "
                    f"{from_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            elif from_time == "10th next month":
                next_year = now.year + 1 if now.month == 12 else now.year
                next_month = now.month + 1 if now.month < 12 else 1
                next_day = 10
                from_absoluteDay = _build_datetime_like(now, next_year, next_month, next_day)
                logger.info(f"10th next month (from): {from_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            elif from_time == "next Monday" or from_time == "next Monday split":
                days_until_monday = (6 - now.weekday()) + 1
                from_absoluteDay = now + timedelta(days=days_until_monday)
                logger.info(
                    f"Next Monday (from): current weekday={now.weekday()}, days to add={days_until_monday} → "
                    f"{from_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            elif from_time == "next Friday":
                if now.weekday() < 4:
                    days_until_friday = 4 - now.weekday()
                elif now.weekday() == 4:
                    days_until_friday = 7
                else:
                    days_until_friday = (7 - now.weekday()) + 4
                from_absoluteDay = now + timedelta(days=days_until_friday)
                logger.info(
                    f"Next Friday (from): current weekday={now.weekday()}, days to add={days_until_friday} → "
                    f"{from_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            elif from_time == "next Saturday":
                if now.weekday() < 5:
                    days_until_saturday = 5 - now.weekday()
                elif now.weekday() == 5:
                    days_until_saturday = 7
                else:
                    days_until_saturday = 6
                from_absoluteDay = now + timedelta(days=days_until_saturday)
                logger.info(
                    f"Next Saturday (from): current weekday={now.weekday()}, days to add={days_until_saturday} → "
                    f"{from_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            elif from_time == "next week Friday":
                days_to_next_monday = 7 - now.weekday()
                days_until_friday = days_to_next_monday + 4
                from_absoluteDay = now + timedelta(days=days_until_friday)
                logger.info(
                    f"Next week Friday (from): current weekday={now.weekday()}, days to add={days_until_friday} → "
                    f"{from_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            elif from_time == "next week Saturday":
                days_to_next_monday = 7 - now.weekday()
                days_until_saturday = days_to_next_monday + 5
                from_absoluteDay = now + timedelta(days=days_until_saturday)
                logger.info(
                    f"Next week Saturday (from): current weekday={now.weekday()}, days to add={days_until_saturday} → "
                    f"{from_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            elif from_time == "next week Sunday":
                days_to_next_monday = 7 - now.weekday()
                days_until_sunday = days_to_next_monday + 6
                from_absoluteDay = now + timedelta(days=days_until_sunday)
                logger.info(
                    f"Next week Sunday (from): current weekday={now.weekday()}, days to add={days_until_sunday} → "
                    f"{from_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
        if from_time == "next Monday split":
            puday = apply_rules_to_timeFormat(relativeRules["expected"]["puDay"], from_absoluteDay)
            config["rules"]["expected"]["puDay"] = puday
            pumonth = apply_rules_to_timeFormat(relativeRules["expected"]["puMonth"], from_absoluteDay)
            config["rules"]["expected"]["puMonth"] = pumonth
            puyear = apply_rules_to_timeFormat(relativeRules["expected"]["puYear"], from_absoluteDay)
            config["rules"]["expected"]["puYear"] = puyear
            logger.info(f"Monday split formatting: puDay={puday}, puMonth={pumonth}, puYear={puyear}")
        else:
            regular_from_time = apply_rules_to_timeFormat(relativeRules["expected"]["from"], from_absoluteDay)
            config["rules"]["expected"]["from"] = regular_from_time
            logger.info(f"From time formatted: {regular_from_time}")

        if relativeTime_to_IntDay[to_time] != "special":
            to_time_IntDat = relativeTime_to_IntDay[to_time]
            to_timediff = timedelta(days=to_time_IntDat)
            to_absoluteDay = now + to_timediff
            logger.info(
                f"To time calculation: {to_time} = {to_time_IntDat} days → "
                f"{to_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
            )
        else:
            if to_time == "this Sunday":
                days_until_sunday = 6 - now.weekday()
                to_absoluteDay = now + timedelta(days=days_until_sunday)
                logger.info(
                    f"This Sunday: current weekday={now.weekday()}, days to add={days_until_sunday} → "
                    f"{to_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            elif to_time == "11th next month":
                next_year = now.year + 1 if now.month == 12 else now.year
                next_month = now.month + 1 if now.month < 12 else 1
                next_day = 11
                to_absoluteDay = _build_datetime_like(now, next_year, next_month, next_day)
                logger.info(f"11th next month (to): {to_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            elif to_time == "next Friday" or to_time == "next Friday split":
                if from_time in ["next Monday", "next Monday split"]:
                    to_absoluteDay = from_absoluteDay + timedelta(days=4)
                    logger.info(
                        f"Next Friday (same week as Monday): from Monday "
                        f"{from_absoluteDay.strftime('%Y-%m-%d')} + 4 days → "
                        f"{to_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )
                else:
                    if now.weekday() < 4:
                        days_to_friday = 4 - now.weekday()
                    else:
                        days_to_friday = (6 - now.weekday()) + 5
                    to_absoluteDay = now + timedelta(days=days_to_friday)
                    logger.info(
                        f"Next Friday (standalone): current weekday={now.weekday()}, days to add={days_to_friday} → "
                        f"{to_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )
            elif to_time == "next Sunday":
                if from_time in ["next Friday", "next Saturday"]:
                    days_to_add_for_sunday = 6 - from_absoluteDay.weekday()
                    to_absoluteDay = from_absoluteDay + timedelta(days=days_to_add_for_sunday)
                    logger.info(
                        f"Next Sunday (to, same weekend as {from_time}): from "
                        f"{from_absoluteDay.strftime('%Y-%m-%d %A')} + {days_to_add_for_sunday} days → "
                        f"{to_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )
                else:
                    if now.weekday() < 6:
                        days_until_sunday = 6 - now.weekday()
                    else:
                        days_until_sunday = 7
                    to_absoluteDay = now + timedelta(days=days_until_sunday)
                    logger.info(
                        f"Next Sunday (to, standalone): current weekday={now.weekday()}, days to add={days_until_sunday} → "
                        f"{to_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )
            elif to_time == "next week Sunday":
                if from_time in ["next week Friday", "next week Saturday"]:
                    days_to_add_for_sunday = 6 - from_absoluteDay.weekday()
                    to_absoluteDay = from_absoluteDay + timedelta(days=days_to_add_for_sunday)
                    logger.info(
                        f"Next week Sunday (to, same week as {from_time}): from "
                        f"{from_absoluteDay.strftime('%Y-%m-%d %A')} + {days_to_add_for_sunday} days → "
                        f"{to_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )
                else:
                    days_to_next_monday = 7 - now.weekday()
                    days_until_sunday = days_to_next_monday + 6
                    to_absoluteDay = now + timedelta(days=days_until_sunday)
                    logger.info(
                        f"Next week Sunday (to, standalone): current weekday={now.weekday()}, days to add={days_until_sunday} → "
                        f"{to_absoluteDay.strftime('%Y-%m-%d %H:%M:%S %Z')}"
                    )
            else:
                pass
        if to_time == "next Friday split":
            to_day = apply_rules_to_timeFormat(relativeRules["expected"]["doDay"], to_absoluteDay)
            config["rules"]["expected"]["doDay"] = to_day
            to_month = apply_rules_to_timeFormat(relativeRules["expected"]["doMonth"], to_absoluteDay)
            config["rules"]["expected"]["doMonth"] = to_month
            to_year = apply_rules_to_timeFormat(relativeRules["expected"]["doYear"], to_absoluteDay)
            config["rules"]["expected"]["doYear"] = to_year
            logger.info(f"Friday split formatting: doDay={to_day}, doMonth={to_month}, doYear={to_year}")
        else:
            regular_to_time = apply_rules_to_timeFormat(relativeRules["expected"]["to"], to_absoluteDay)
            config["rules"]["expected"]["to"] = regular_to_time
            logger.info(f"To time formatted: {regular_to_time}")

    logger.info(f"[DEBUG] Final config rules: {config['rules']}")
    print(config["rules"])
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

    override_url = os.environ.get(ACTIVE_URL_OVERRIDE_ENV)
    if override_url:
        _write_active_url_artifact(f"{override_url}\n")
        return override_url

    window_id = _find_chrome_window_id()
    if window_id is None:
        logger.error("No visible Chrome window found on the shared X display")
        _write_active_url_artifact("\n")
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
        _write_active_url_artifact("\n")
        return None

    goto_prefix = config.get("goto_prefix", "https://")
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://", raw_url):
        active_tab_url = raw_url
    elif raw_url.startswith("www."):
        active_tab_url = f"https://{raw_url}"
    else:
        active_tab_url = f"{goto_prefix}{raw_url}"

    logger.info("Active tab url now: %s", active_tab_url)
    _write_active_url_artifact(f"{active_tab_url}\n")
    return active_tab_url


def get_url_dashPart(env, config: Dict[str, str]):
    active_tab_url = get_active_url_from_accessTree(env, config)
    if active_tab_url is None:
        return None

    try:
        part_index = int(config["partIndex"])
    except (ValueError, TypeError):
        logger.error(
            f"[URL_DASH_PART] Invalid partIndex: {config.get('partIndex', 'None')}. Must be an integer."
        )
        return None

    url_parts = active_tab_url.split("/")
    if abs(part_index) > len(url_parts) or part_index >= len(url_parts):
        logger.error(
            f"[URL_DASH_PART] partIndex {part_index} is out of range for URL with {len(url_parts)} parts"
        )
        return None

    dash_part = url_parts[part_index]
    if config.get("needDeleteId", False):
        dash_part = dash_part.split("?")[0]

    logger.info(f"[URL_DASH_PART] Extracted dash part: '{dash_part}' from URL: {active_tab_url}")

    if config["returnType"] == "string":
        return dash_part
    if config["returnType"] == "json":
        return {config["key"]: dash_part}

    logger.error(
        f"[URL_DASH_PART] Invalid returnType: {config.get('returnType', 'None')}. "
        "Must be 'string' or 'json'."
    )
    return None


def is_expected_url_pattern_match(result, rules) -> float:
    if not result:
        return 0.0

    if isinstance(result, str):
        result_url = result
        logger.info("result url: %s", result_url)
    elif isinstance(result, dict) and "url" in result:
        result_url = result["url"]
        logger.info("result url: %s", result_url)
    else:
        logger.error(
            "Invalid result format: %s, expected string URL or dict with 'url' field",
            type(result),
        )
        return 0.0

    logger.info("Result URL to match: %s", result_url)

    patterns = rules["expected"]
    logger.info("expected_regex: %s", patterns)
    for pattern in patterns:
        match = re.search(pattern, result_url)
        logger.info("match: %s", match)
        if not match:
            return 0.0
    return 1.0


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
    time_result = get_url_dashPart(None, RESULT_CONFIG_TIME)
    time_rules = get_rule_relativeTime(LOCAL_ENV, copy.deepcopy(EXPECTED_TIME))

    location_result = get_active_url_from_accessTree(None, RESULT_CONFIG_LOCATION)
    location_rules = get_rule(None, copy.deepcopy(EXPECTED_LOCATION))

    return [
        check_direct_json_object(time_result, time_rules),
        is_expected_url_pattern_match(location_result, location_rules),
    ]


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


def test_main():
    scores = evaluate_osworld_conditions()
    assert scores == [1.0, 1.0], (
        "Chrome active tab URL does not satisfy the exact OSWorld url_dashPart and "
        "is_expected_url_pattern_match checks"
    )
