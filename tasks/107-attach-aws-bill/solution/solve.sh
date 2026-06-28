#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

[ -f /tmp/tua-env.sh ] && . /tmp/tua-env.sh

/usr/local/bin/thunderbird_live_helper.py attach-file \
  --path /app/aws-bill.pdf \
  --subject 'New-month AWS Bill' \
  --from 'Anonym Tester <anonym-x2024@outlook.com>' \
  --to assistant@outlook.com
