#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -f "/app/New_Club_Spring_2018_Training.pptx" ]; then
    cp "/app/New_Club_Spring_2018_Training.pptx" /logs/artifacts/New_Club_Spring_2018_Training.pptx || true
  fi
}

trap persist_artifacts EXIT

mkdir -p /logs/verifier || true

if score=$(/opt/venv/bin/python /tests/test_outputs.py); then
  :
else
  score="0"
fi

printf '%s\n' "$score" > /logs/verifier/reward.txt
