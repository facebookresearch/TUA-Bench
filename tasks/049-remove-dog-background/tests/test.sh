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

fetch_reference() {
  mkdir -p "$REFERENCE_DIR"
  curl -fL --retry 3 --retry-delay 1 "$REFERENCE_URL" -o "$REFERENCE_PATH"
}

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -f /app/dog_without_background.png ]; then
    cp /app/dog_without_background.png /logs/artifacts/dog_without_background.png || true
  fi
}

trap persist_artifacts EXIT

if ! fetch_reference; then
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

export TUA_REFERENCE_PATH="$REFERENCE_PATH"

if pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_output_matches_osworld_check_structure_sim -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
