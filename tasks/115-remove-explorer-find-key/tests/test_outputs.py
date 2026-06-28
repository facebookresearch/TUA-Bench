# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import json
import tempfile
from pathlib import Path

# Exact local port of OSWorld vs_code/ea98c5d7-3cf9-4f9b-8ad3-366b58e0fcae using check_json_keybindings.
TARGET_PATH = Path('/home/agent/.config/Code/User/keybindings.json')
EXPECTED_RULES = {'expected': {'key': 'ctrl+f', 'command': '-list.find', 'when': 'listFocus && listSupportsFind'}}
FAILURE_MESSAGE = '/home/agent/.config/Code/User/keybindings.json does not contain the expected VS Code keybinding'
GOOD_JSON = '[\n  {\n    "key": "ctrl+f",\n    "command": "-list.find",\n    "when": "listFocus && listSupportsFind"\n  }\n]\n'
BAD_JSON = '[]\n'


def check_json_keybindings(actual: str, expected: dict, **options) -> float:
    def direct_load_json(fp):
        try:
            with open(fp, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data
        except Exception:
            return None

    def skip_first_line_load_json(fp):
        try:
            with open(fp, "r", encoding="utf-8") as handle:
                handle.readline()
                data = json.load(handle)
            return data
        except Exception:
            return None

    for loader in [direct_load_json, skip_first_line_load_json]:
        data = loader(actual)
        if data is not None and type(data) == list:
            break
    else:
        return 0.0

    expected = expected["expected"]
    if expected in data:
        return 1.0
    return 0.0


def evaluate_keybindings(path: Path = TARGET_PATH) -> float:
    return check_json_keybindings(str(path), EXPECTED_RULES)


def run_sanity() -> dict[str, float]:
    with tempfile.TemporaryDirectory() as tmpdir:
        good_path = Path(tmpdir) / "good.json"
        bad_path = Path(tmpdir) / "bad.json"
        good_path.write_text(GOOD_JSON, encoding="utf-8")
        bad_path.write_text(BAD_JSON, encoding="utf-8")
        return {
            "pass_score": check_json_keybindings(str(good_path), EXPECTED_RULES),
            "fail_score": check_json_keybindings(str(bad_path), EXPECTED_RULES),
        }


def test_sanity():
    result = run_sanity()
    assert result["pass_score"] == 1.0, result
    assert result["fail_score"] == 0.0, result


def test_main():
    assert evaluate_keybindings() == 1.0, FAILURE_MESSAGE
