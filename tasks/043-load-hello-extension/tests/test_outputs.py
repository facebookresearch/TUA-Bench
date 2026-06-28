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
RULE = {
    "expected": os.environ.get(
        "EXPECTED_EXTENSION_PATH",
        str(Path.home() / "Desktop/helloExtension"),
    )
}


def get_find_unpacked_extension_path():
    try:
        content = PREFERENCES_PATH.read_text(encoding="utf-8")
        data = json.loads(content)
        all_extensions_path = []
        all_extensions = data.get("extensions", {}).get("settings", {})
        for extension_id in all_extensions.keys():
            path = all_extensions[extension_id]["path"]
            all_extensions_path.append(path)
        return all_extensions_path
    except Exception as e:
        logging.error(f"Error: {e}")
        return "Google"


def is_in_list(result, rules) -> float:
    expect = rules["expected"]
    if expect in result:
        return 1.0
    else:
        return 0.0


def test_main():
    assert (
        is_in_list(get_find_unpacked_extension_path(), RULE) == 1.0
    ), "Chrome preferences do not satisfy OSWorld is_in_list for find_unpacked_extension_path"
