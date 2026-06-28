#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

persist_artifacts() {
  mkdir -p /logs/artifacts || true
if [ -e /var/lib/tua-state/vscode_state.json ]; then
  if [ -d /var/lib/tua-state/vscode_state.json ]; then
    cp -R /var/lib/tua-state/vscode_state.json /logs/artifacts/vscode_state.json || true
  else
    cp /var/lib/tua-state/vscode_state.json /logs/artifacts/vscode_state.json || true
  fi
fi
if [ -e /app/project.code-workspace ]; then
  if [ -d /app/project.code-workspace ]; then
    cp -R /app/project.code-workspace /logs/artifacts/project.code-workspace || true
  else
    cp /app/project.code-workspace /logs/artifacts/project.code-workspace || true
  fi
fi
}

trap persist_artifacts EXIT

mkdir -p /logs/verifier || true

if /opt/venv/bin/python -m pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_main -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
