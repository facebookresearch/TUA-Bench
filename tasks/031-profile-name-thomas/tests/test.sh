#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

PREFERENCES_PATH="$HOME/.config/google-chrome/Default/Preferences"

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -f "$PREFERENCES_PATH" ]; then
    cp "$PREFERENCES_PATH" /logs/artifacts/Preferences || true
  fi
}

trap persist_artifacts EXIT

mkdir -p /logs/verifier || true

# Mirror the OSWorld postconfig intent by checking the saved profile after Chrome exits.
pkill -f "chromium|google-chrome" >/dev/null 2>&1 || true
sleep 2

if /opt/venv/bin/python -m pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_main -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
