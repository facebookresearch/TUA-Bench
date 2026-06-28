#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  PROFILE_DIR="$("/usr/local/bin/thunderbird_state.py" profile)"
  if [ -d "$PROFILE_DIR/Mail/Local Folders" ]; then
    ls -R "$PROFILE_DIR/Mail/Local Folders" > /logs/artifacts/local-folders.ls || true
  fi
}

trap persist_artifacts EXIT

mkdir -p /logs/verifier || true
mkdir -p /logs/artifacts || true

/usr/local/bin/thunderbird_state.py kill >/dev/null 2>&1 || true

if /opt/venv/bin/python -m pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_main -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
