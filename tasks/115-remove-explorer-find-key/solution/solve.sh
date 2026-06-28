#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

python3 - <<'PY'
import json
from pathlib import Path

path = Path('/home/agent/.config/Code/User/keybindings.json')
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text('[\n  {\n    "key": "ctrl+f",\n    "command": "-list.find",\n    "when": "listFocus && listSupportsFind"\n  }\n]\n', encoding="utf-8")
PY
