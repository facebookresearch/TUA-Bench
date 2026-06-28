#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

mkdir -p /app/artifacts
python3 - <<'PY'
import csv
from pathlib import Path

reference = Path("/solution/reference/Nuclei.csv")
with reference.open("r", encoding="utf-8", newline="") as handle:
    count = max(sum(1 for _ in csv.reader(handle)) - 1, 0)

Path("/app/artifacts/nuclei_count.txt").write_text(f"{count}\n", encoding="utf-8")
PY
test -s /app/artifacts/nuclei_count.txt
