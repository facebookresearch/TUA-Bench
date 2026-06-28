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

passed_tests=0

if ! python3 /tests/test_outputs.py test_outputs_exist; then
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

passed_tests=$((passed_tests + 1))

if python3 /tests/test_outputs.py test_metrics_match_ground_truth; then
  passed_tests=$((passed_tests + 1))
fi

if python3 /tests/test_outputs.py test_final_field_supports_metrics; then
  passed_tests=$((passed_tests + 1))
fi

if [ "$passed_tests" -eq 3 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  case "$passed_tests" in
    2) echo 0.66 > /logs/verifier/reward.txt ;;
    1) echo 0.33 > /logs/verifier/reward.txt ;;
    *) echo 0 > /logs/verifier/reward.txt ;;
  esac
fi
