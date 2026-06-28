#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

PROFILE_DIR="$HOME/.config/google-chrome"
PREFERENCES_PATH="$PROFILE_DIR/Default/Preferences"

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -f "$PREFERENCES_PATH" ]; then
    cp "$PREFERENCES_PATH" /logs/artifacts/Preferences || true
  fi
}

trap persist_artifacts EXIT

mkdir -p /logs/verifier || true
mkdir -p /logs/artifacts || true

if /opt/venv/bin/python -m pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_main -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
