#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

mkdir -p /logs/verifier /logs/artifacts || true

# Postconfig spawns libreoffice for xlsx->csv conversion, whose stdout
# pollutes the captured score. Keep only the last stdout line, which is the
# numeric reward printed by test_outputs.py.
if raw_score=$(/opt/venv/bin/python /tests/test_outputs.py); then
  score=$(printf '%s\n' "$raw_score" | tail -n 1)
else
  score="0"
fi

printf '%s\n' "$score" > /logs/verifier/reward.txt
