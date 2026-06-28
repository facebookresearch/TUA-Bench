#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

TMP_DIR="/tmp/117-comma-text-to-table"
TMP_PATH="$TMP_DIR/Graphemes_Sound_Letter_Patterns.docx"
mkdir -p "$TMP_DIR"
curl -fL --retry 3 --retry-delay 1 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_writer/936321ce-5236-426a-9a20-e0e3c5dc536f/Graphemes_Sound_Letter_Patterns_Gold.docx -o "$TMP_PATH"
cp "$TMP_PATH" /app/Graphemes_Sound_Letter_Patterns.docx
