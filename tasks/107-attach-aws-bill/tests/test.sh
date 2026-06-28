#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

[ -f /tmp/tua-env.sh ] && . /tmp/tua-env.sh

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -f /tmp/accessibility_tree.xml ]; then
    cp /tmp/accessibility_tree.xml /logs/artifacts/accessibility_tree.xml || true
  fi
  if [ -f /tmp/accessibility_tree_error.txt ]; then
    cp /tmp/accessibility_tree_error.txt /logs/artifacts/accessibility_tree_error.txt || true
  fi
  if [ -f /tmp/thunderbird-attachment-check.txt ]; then
    cp /tmp/thunderbird-attachment-check.txt /logs/artifacts/thunderbird-attachment-check.txt || true
  fi
  if [ -f /tmp/thunderbird.log ]; then
    cp /tmp/thunderbird.log /logs/artifacts/thunderbird.log || true
  fi
  if [ -f /tmp/thunderbird_state.log ]; then
    cp /tmp/thunderbird_state.log /logs/artifacts/thunderbird_state.log || true
  fi
  if [ -f /tmp/thunderbird-live-helper.log ]; then
    cp /tmp/thunderbird-live-helper.log /logs/artifacts/thunderbird-live-helper.log || true
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
