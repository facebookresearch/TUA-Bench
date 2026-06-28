#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
mkdir -p "$APP_DIR"

TMP_PATH_0="$(mktemp)"
curl -fsSL --retry 3 --retry-delay 1 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_calc/a01fbce3-2793-461f-ab86-43680ccbae25/Set_Decimal_Separator_Dot_gold_ru.xlsx -o "$TMP_PATH_0"
cp "$TMP_PATH_0" "$APP_DIR/Set_Decimal_Separator_Dot.xlsx"
rm -f "$TMP_PATH_0"
TMP_PATH_1="$(mktemp)"
curl -fsSL --retry 3 --retry-delay 1 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_calc/a01fbce3-2793-461f-ab86-43680ccbae25/Set_Decimal_Separator_Dot_gold_ru.csv -o "$TMP_PATH_1"
cp "$TMP_PATH_1" "$APP_DIR/Set_Decimal_Separator_Dot-Sheet1.csv"
rm -f "$TMP_PATH_1"
