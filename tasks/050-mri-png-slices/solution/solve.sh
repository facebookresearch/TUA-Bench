#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

mkdir -p /app/artifacts/png_slices

if [ -d /tests/reference/prostate_00_png_slices ]; then
  cp /tests/reference/prostate_00_png_slices/*.png /app/artifacts/png_slices/
elif [ -d "$(dirname "$0")/reference/prostate_00_png_slices" ]; then
  cp "$(dirname "$0")/reference/prostate_00_png_slices"/*.png /app/artifacts/png_slices/
else
  echo "Reference PNG slice directory is unavailable" >&2
  exit 1
fi

test "$(find /app/artifacts/png_slices -maxdepth 1 -type f -name '*.png' | wc -l)" -eq 15
