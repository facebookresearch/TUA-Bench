#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

export DISPLAY="${DISPLAY:-:99}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/tmp/tua-dbus-session}"

wait_for_x_display() {
  for _ in $(seq 1 60); do
    if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

wait_for_dbus() {
  for _ in $(seq 1 60); do
    if dbus-send --session --dest=org.freedesktop.DBus --type=method_call --print-reply \
      / org.freedesktop.DBus.ListNames >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
  Xvfb "$DISPLAY" -screen 0 1280x720x24 >/tmp/xvfb.log 2>&1 &
  wait_for_x_display
fi

if ! dbus-send --session --dest=org.freedesktop.DBus --type=method_call --print-reply \
  / org.freedesktop.DBus.ListNames >/dev/null 2>&1; then
  rm -f /tmp/tua-dbus-session /tmp/tua-dbus-session*
  dbus-daemon --session --address="$DBUS_SESSION_BUS_ADDRESS" --fork >/tmp/dbus.log 2>&1
  wait_for_dbus
fi

/usr/local/bin/chrome_state.py task >/tmp/chrome_state.log 2>&1

exec "$@"
