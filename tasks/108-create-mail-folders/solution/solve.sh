#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

/usr/local/bin/thunderbird_state.py kill >/dev/null 2>&1 || true
PROFILE_DIR="$("/usr/local/bin/thunderbird_state.py" profile)"

PROFILE_DIR="$PROFILE_DIR" python - <<'PY'
import os
from pathlib import Path

root = Path(os.environ["PROFILE_DIR"]) / "Mail" / "Local Folders"
root.mkdir(parents=True, exist_ok=True)
folders = ['COMPANY', 'UNIVERSITY']
for name in folders:
    (root / name).touch()
    (root / f"{name}.msf").touch()
PY
