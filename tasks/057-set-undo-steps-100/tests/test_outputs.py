# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from pathlib import Path

CONFIG_PATH = Path.home() / ".config/GIMP/2.10/gimprc"
RULE = {"key": "undo-levels", "type:": "key-value", "value": "100"}


def check_config_status(actual_config_path, rule):
    """
    Check if the GIMP status is as expected
    """
    if actual_config_path is None:
        return 0.

    with open(actual_config_path, 'r') as f:
        content = f.readlines()

    for line in content:
        if line.startswith('#') or line == '\n':
            continue
        items = line.strip().lstrip('(').rstrip(')\n').split()
        if isinstance(rule["key"], str):
            if items[0] == rule["key"] and items[-1] == rule["value"]:
                return 1.
        elif isinstance(rule["key"], list) and len(rule["key"]) == 2:
            if items[0] == rule["key"][0] \
                    and items[1] == rule["key"][1] \
                    and items[-1] == rule["value"]:
                return 1.
    return 0.


def test_main():
    assert CONFIG_PATH.exists(), f"Missing config file: {CONFIG_PATH}"
    assert check_config_status(str(CONFIG_PATH), RULE) == 1.0, "Config does not satisfy OSWorld check_config_status"
