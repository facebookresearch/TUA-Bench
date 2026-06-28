#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
OUTPUT_PATH="$APP_DIR/Date_Budget_Variance_HideNA.xlsx"
TMP_PATH="$(mktemp)"

curl -fsSL --retry 3 --retry-delay 1 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_calc/6054afcb-5bab-4702-90a0-b259b5d3217c/Date_Budget_Variance_HideNA_gold.xlsx -o "$TMP_PATH"
mkdir -p "$(dirname "$OUTPUT_PATH")"
cp "$TMP_PATH" "$OUTPUT_PATH"
rm -f "$TMP_PATH"
