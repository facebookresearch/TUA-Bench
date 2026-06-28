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
if [ -e /home/agent/.config/Code/User/keybindings.json ]; then
  if [ -d /home/agent/.config/Code/User/keybindings.json ]; then
    cp -R /home/agent/.config/Code/User/keybindings.json /logs/artifacts/keybindings.json || true
  else
    cp /home/agent/.config/Code/User/keybindings.json /logs/artifacts/keybindings.json || true
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
