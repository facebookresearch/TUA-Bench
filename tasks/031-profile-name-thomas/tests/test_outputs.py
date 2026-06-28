# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import json
import logging
from pathlib import Path

PREFERENCES_PATH = Path.home() / ".config/google-chrome/Default/Preferences"
RULE = {"expected": "Thomas"}


def get_profile_name():
    """
    Get the username from the Chrome browser.
    Assume the cookies are stored in the default location, not encrypted and not large in size.
    """
    try:
        content = PREFERENCES_PATH.read_text(encoding="utf-8")
        data = json.loads(content)

        profile_name = data.get("profile", {}).get("name", None)
        return profile_name
    except Exception as e:
        logging.error(f"Error: {e}")
        return None


def exact_match(result, rules) -> float:
    expect = rules["expected"]
    print(result, expect)

    if result == expect:
        return 1.0
    else:
        return 0.0


def test_main():
    assert (
        exact_match(get_profile_name(), RULE) == 1.0
    ), "Chrome preferences do not satisfy OSWorld exact_match for profile_name"
