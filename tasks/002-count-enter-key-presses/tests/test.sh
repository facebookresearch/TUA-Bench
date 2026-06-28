#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -uo pipefail

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -f /app/result.txt ]; then
    cp /app/result.txt /logs/artifacts/result.txt || true
  fi
}

trap persist_artifacts EXIT

python3 /tests/verify.py
