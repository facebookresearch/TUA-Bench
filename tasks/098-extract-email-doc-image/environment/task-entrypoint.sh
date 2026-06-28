#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/tmp/tua-dbus-session}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg-runtime-$(id -u)}"
unset NO_AT_BRIDGE

mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
mkdir -p "$HOME/Desktop" "$HOME/Documents" "$HOME/Downloads" "$HOME/Music" "$HOME/Drive"

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  Xvfb "$DISPLAY" -screen 0 1440x900x24 >/tmp/xvfb.log 2>&1 &
  for _ in $(seq 1 60); do
    if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
      break
    fi
    sleep 0.5
  done
fi

if ! dbus-send --session --dest=org.freedesktop.DBus --type=method_call --print-reply   / org.freedesktop.DBus.ListNames >/dev/null 2>&1; then
  rm -f /tmp/tua-dbus-session /tmp/tua-dbus-session*
  dbus-daemon --session --address="$DBUS_SESSION_BUS_ADDRESS" --fork >/tmp/dbus.log 2>&1
fi

: > "$HOME/.bash_history" || true

python3 /usr/local/bin/task_state.py task >/tmp/task_state.log 2>&1 || true

exec "$@"
