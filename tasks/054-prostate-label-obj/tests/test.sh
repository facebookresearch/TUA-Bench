#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -uo pipefail

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -d /app/artifacts ]; then
    cp -R /app/artifacts/. /logs/artifacts/ || true
  fi
}

trap persist_artifacts EXIT

mkdir -p /logs/verifier || true

if ! python3 /tests/test_outputs.py test_obj_exists; then
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

if python3 /tests/test_outputs.py test_obj_similarity; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0.5 > /logs/verifier/reward.txt
fi
