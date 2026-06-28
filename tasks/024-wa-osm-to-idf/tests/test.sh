#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -uo pipefail

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -f /app/generated_building.idf ]; then
    cp /app/generated_building.idf /logs/artifacts/generated_building.idf || true
  fi
  if [ -f /app/translation_summary.txt ]; then
    cp /app/translation_summary.txt /logs/artifacts/translation_summary.txt || true
  fi
}

trap persist_artifacts EXIT

mkdir -p /logs/verifier || true

passed_tests=0

if ! openstudio execute_python_script /tests/test_outputs.py test_output_files_exist; then
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

passed_tests=$((passed_tests + 1))

if openstudio execute_python_script /tests/test_outputs.py test_translated_idf_matches_reference; then
  passed_tests=$((passed_tests + 1))
fi

if openstudio execute_python_script /tests/test_outputs.py test_summary_matches_inputs; then
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
