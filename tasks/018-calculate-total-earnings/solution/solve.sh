#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
OUTPUT_PATH="$APP_DIR/Multiply_Time_Number.xlsx"
export OUTPUT_PATH

python - <<'PY'
import os
from pathlib import Path

output_path = Path(os.environ["OUTPUT_PATH"])
from openpyxl import load_workbook

workbook = load_workbook(output_path)
sheet = workbook[workbook.sheetnames[0]]
sheet["E3"] = 191.6667
workbook.save(output_path)
PY
