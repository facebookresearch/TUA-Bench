#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -uo pipefail

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  if [ -f /app/corporate_org_chart.png ]; then
    cp /app/corporate_org_chart.png /logs/artifacts/corporate_org_chart.png || true
  fi
  if [ -f /app/corporate_org_chart.drawio ]; then
    cp /app/corporate_org_chart.drawio /logs/artifacts/corporate_org_chart.drawio || true
  fi
}

trap persist_artifacts EXIT

passed_checks=0

if ! pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_png_exists -rA; then
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

if pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_contains_all_target_boxes -rA; then
  passed_checks=$((passed_checks + 1))
fi

if pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_connection_lines_are_not_jagged -rA; then
  passed_checks=$((passed_checks + 1))
fi

if pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_boxes_do_not_overlap -rA; then
  passed_checks=$((passed_checks + 1))
fi

if pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_overall_matches_requirement -rA; then
  passed_checks=$((passed_checks + 1))
fi

case "$passed_checks" in
  4) echo 1 > /logs/verifier/reward.txt ;;
  3) echo 0.75 > /logs/verifier/reward.txt ;;
  2) echo 0.5 > /logs/verifier/reward.txt ;;
  1) echo 0.25 > /logs/verifier/reward.txt ;;
  *) echo 0 > /logs/verifier/reward.txt ;;
esac
