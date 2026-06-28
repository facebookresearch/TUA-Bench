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
output = Path("/app/artifacts/nuclei_locations.csv")
with reference.open("r", encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle)
    rows = [(row["Location_Center_X"], row["Location_Center_Y"]) for row in reader]

with output.open("w", encoding="utf-8", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["x", "y"])
    writer.writerows(rows)
PY
test -s /app/artifacts/nuclei_locations.csv
