#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
OUTPUT_PATH="$APP_DIR/Movie_title_garbage_clean.xlsx"
TMP_PATH="$(mktemp)"

curl -fsSL --retry 3 --retry-delay 1 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_calc/a9f325aa-8c05-4e4f-8341-9e4358565f4f/Movie_titles_garbage_clean_gold.xlsx -o "$TMP_PATH"
mkdir -p "$(dirname "$OUTPUT_PATH")"
cp "$TMP_PATH" "$OUTPUT_PATH"
rm -f "$TMP_PATH"
