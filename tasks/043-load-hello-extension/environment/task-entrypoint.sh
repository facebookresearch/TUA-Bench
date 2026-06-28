#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"

PROFILE_DIR="${CHROME_USER_DATA_DIR:-$HOME/.config/google-chrome}"
START_URL="chrome://extensions/"

mkdir -p "$HOME/Desktop" "$PROFILE_DIR"

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  Xvfb "$DISPLAY" -screen 0 1440x900x24 >/tmp/xvfb.log 2>&1 &
  for _ in $(seq 1 60); do
    if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
fi

if ! pgrep -f "chromium.*--user-data-dir=$PROFILE_DIR" >/dev/null 2>&1; then
  rm -rf "$PROFILE_DIR"/Singleton*
  /usr/local/bin/google-chrome --new-window "$START_URL" >/tmp/chrome.log 2>&1 &
  sleep 5
fi

exec "$@"
