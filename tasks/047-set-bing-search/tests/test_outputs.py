# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import json
import logging
import os
from pathlib import Path

PREFERENCES_PATH = Path(
    os.environ.get(
        "PREFERENCES_PATH",
        str(Path.home() / ".config/google-chrome/Default/Preferences"),
    )
)
RULE = {"expected": ["Microsoft Bing", "Bing"]}


def get_default_search_engine():
    try:
        content = PREFERENCES_PATH.read_text(encoding="utf-8")
        data = json.loads(content)

        # The path within the JSON data to the default search engine might vary.
        search_engine = (
            data.get("default_search_provider_data", {})
            .get("template_url_data", {})
            .get("short_name", "Google")
        )
        return search_engine
    except Exception as e:
        logging.error(f"Error: {e}")
        return "Google"


def match_in_list(result, rules) -> float:
    expect = rules["expected"]
    print(result, expect)

    if result in expect:
        return 1.0
    else:
        return 0.0


def test_main():
    assert (
        match_in_list(get_default_search_engine(), RULE) == 1.0
    ), "Chrome preferences do not satisfy OSWorld match_in_list for default_search_engine"
