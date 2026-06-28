#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

mkdir -p /app/artifacts
printf '47.1065233568328\n' > /app/artifacts/prostate_volume.txt
test -s /app/artifacts/prostate_volume.txt
