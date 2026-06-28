#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -f /app/palette_computer.png ]; then
    cp /app/palette_computer.png /logs/artifacts/palette_computer.png || true
  fi
}

trap persist_artifacts EXIT

mkdir -p /logs/verifier || true

if pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_output_matches_osworld_check_palette_and_structure_sim -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
