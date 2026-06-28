#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

[ -f /tmp/tua-env.sh ] && . /tmp/tua-env.sh

/usr/local/bin/thunderbird_live_helper.py fill-login \
  --name Anonym \
  --email anonym-x2024@outlook.com \
  --password password
