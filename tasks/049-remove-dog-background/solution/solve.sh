#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

REFERENCE_URL="${OSWORLD_GOLD_URL:-https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/gimp/2a729ded-3296-423d-aec4-7dd55ed5fbb3/dog_cutout_gold.png}"
REFERENCE_DIR="/tmp/tua-049-remove-dog-background"
REFERENCE_PATH="${REFERENCE_DIR}/dog_cutout_gold.png"

mkdir -p "$REFERENCE_DIR"
curl -fL --retry 3 --retry-delay 1 "$REFERENCE_URL" -o "$REFERENCE_PATH"
cp "$REFERENCE_PATH" /app/dog_without_background.png
