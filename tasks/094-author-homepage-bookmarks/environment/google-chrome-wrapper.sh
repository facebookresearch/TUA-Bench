#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
PROFILE_DIR="${CHROME_USER_DATA_DIR:-$HOME/.config/google-chrome}"
mkdir -p "$PROFILE_DIR"

declare -a EXTRA_ARGS
EXTRA_ARGS=(
  "--user-data-dir=$PROFILE_DIR"
  "--profile-directory=Default"
  "--no-first-run"
  "--no-default-browser-check"
  "--password-store=basic"
  "--disable-dev-shm-usage"
  "--no-sandbox"
)

has_remote_debugging_port=0
for arg in "$@"; do
  if [[ "$arg" == --remote-debugging-port=* ]]; then
    has_remote_debugging_port=1
    break
  fi
done

if [ "$has_remote_debugging_port" -eq 0 ]; then
  EXTRA_ARGS+=("--remote-debugging-port=${TUA_CHROME_REMOTE_DEBUGGING_PORT:-${CHROME_REMOTE_DEBUGGING_PORT:-1337}}")
fi

exec /usr/bin/chromium "${EXTRA_ARGS[@]}" "$@"
