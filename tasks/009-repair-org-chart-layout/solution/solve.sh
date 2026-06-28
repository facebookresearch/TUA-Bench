#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

cp /app/input/org_chart.drawio /app/corporate_org_chart.drawio
cp /solution/corporate_org_chart.png /app/corporate_org_chart.png
