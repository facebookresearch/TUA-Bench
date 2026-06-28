#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


      set -euo pipefail

      persist_artifacts() {
        mkdir -p /logs/artifacts || true
        (
                  getent passwd charles || true
ls -ld /home/test1 || true
                ) > /logs/artifacts/'account_state.txt' 2>&1 || true
      }

      trap persist_artifacts EXIT

      mkdir -p /logs/verifier || true

      if pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_main -rA; then
        echo 1 > /logs/verifier/reward.txt
      else
        echo 0 > /logs/verifier/reward.txt
      fi
