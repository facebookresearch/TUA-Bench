#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

python3 - <<'PY'
from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

plan = json.loads(Path("/app/input/task_plan.json").read_text(encoding="utf-8"))

artifact_dir = Path(plan["artifact_dir"])
artifact_dir.mkdir(parents=True, exist_ok=True)

obj_output = Path(plan["obj_output_path"])
obj_output.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2("/solution/reference/prostate_00_prostate.obj", obj_output)

png_output = Path(plan["render_output_path"])
png_output.parent.mkdir(parents=True, exist_ok=True)
png_output.write_bytes(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO2Z9WQAAAAASUVORK5CYII="
    )
)
PY
