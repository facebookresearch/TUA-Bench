#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

mkdir -p /app/artifacts
cp /solution/reference/prostate_00_prostate.obj /app/artifacts/prostate_model.obj
test -s /app/artifacts/prostate_model.obj
