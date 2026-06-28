#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

mkdir -p "$HOME" /app
: > "$HOME/.bash_history" || true

python3 /usr/local/bin/task_state.py task >/tmp/task_state.log 2>&1 || true

exec "$@"
