#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -uo pipefail

PREFERENCES_PATH="$HOME/.config/google-chrome/Default/Preferences"
ACTIVE_URL_ARTIFACT="/logs/artifacts/active_url.txt"
APPEARANCE_MODE_ARTIFACT="/logs/artifacts/appearance_mode.txt"

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -f "$PREFERENCES_PATH" ]; then
    cp "$PREFERENCES_PATH" /logs/artifacts/Preferences || true
  fi
}

trap persist_artifacts EXIT

mkdir -p /logs/verifier || true
mkdir -p /logs/artifacts || true
echo 0 > /logs/verifier/reward.txt
rm -f "$ACTIVE_URL_ARTIFACT" "$APPEARANCE_MODE_ARTIFACT" || true

# Mirror the OSWorld postconfig sleep before reading the final browser state.
sleep 1

if /opt/venv/bin/python -m pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_main -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
