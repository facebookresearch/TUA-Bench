#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -f $HOME/.config/GIMP/2.10/action-history ]; then
    cp $HOME/.config/GIMP/2.10/action-history /logs/artifacts/action-history || true
  fi
}

trap persist_artifacts EXIT

mkdir -p /logs/verifier || true

if pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_main -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
