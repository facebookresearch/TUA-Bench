# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path
from typing import Dict, List

ACTION_HISTORY_PATH = Path.home() / ".config/GIMP/2.10/action-history"
RULES = {"exclude": ["error", "failed", "not found"], "include": ["filters-vignette"]}


def check_include_exclude(result: str, rules: Dict[str, List[str]]) -> float:
    if result is None:
        return 0.

    print(result, rules)
    include = rules.get("include", [])
    exclude = rules.get("exclude", [])
    if all(r in result for r in include) and all(r not in result for r in exclude):
        return 1.
    else:
        return 0.


def test_main():
    assert ACTION_HISTORY_PATH.exists(), f"Missing action-history file: {ACTION_HISTORY_PATH}"
    content = ACTION_HISTORY_PATH.read_text(encoding="utf-8")
    assert check_include_exclude(content, RULES) == 1.0, "History does not satisfy OSWorld check_include_exclude"
