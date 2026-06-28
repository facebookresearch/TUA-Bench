#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import ast
import json
import sys
from copy import deepcopy
from pathlib import Path

STATE_PATH = Path("/var/lib/tua-state/gsettings.json")
DEFAULT_STATE = {
    "org.gnome.desktop.interface": {
        "gtk-theme": "Adwaita",
        "text-scaling-factor": 1.0,
    },
}
VALUE_TYPES = {
    ("org.gnome.desktop.interface", "gtk-theme"): "str",
    ("org.gnome.desktop.interface", "text-scaling-factor"): "float",
}


def load_state() -> dict:
    if not STATE_PATH.exists():
        save_state(deepcopy(DEFAULT_STATE))
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def ensure_supported(schema: str, key: str) -> str:
    value_type = VALUE_TYPES.get((schema, key))
    if value_type is None:
        raise SystemExit(f"Unsupported key: {schema} {key}")
    return value_type


def format_value(value_type: str, value) -> str:
    if value_type == "str":
        return f"'{value}'"
    if value_type == "float":
        return str(float(value))
    raise SystemExit(f"Unsupported value type: {value_type}")


def parse_value(value_type: str, raw: str):
    if value_type == "str":
        try:
            return ast.literal_eval(raw.strip())
        except Exception:
            return raw.strip()
    if value_type == "float":
        return float(raw.strip())
    raise SystemExit(f"Unsupported value type: {value_type}")


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print("Usage: gsettings <get|set> <schema> <key> [value...]", file=sys.stderr)
        return 1
    command, schema, key = argv[1], argv[2], argv[3]
    value_type = ensure_supported(schema, key)
    state = load_state()
    state.setdefault(schema, {})
    if command == "get":
        value = state[schema].get(key, deepcopy(DEFAULT_STATE[schema][key]))
        print(format_value(value_type, value))
        return 0
    if command == "set":
        raw_value = " ".join(argv[4:])
        state[schema][key] = parse_value(value_type, raw_value)
        save_state(state)
        return 0
    print(f"Unsupported gsettings command: {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
