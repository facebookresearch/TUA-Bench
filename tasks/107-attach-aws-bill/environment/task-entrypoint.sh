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
export GNOME_ACCESSIBILITY="${GNOME_ACCESSIBILITY:-1}"
export GTK_MODULES="${GTK_MODULES:-gail:atk-bridge}"
export MOZ_ENABLE_WAYLAND=0
unset NO_AT_BRIDGE

mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

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
    if dbus-send --session --dest=org.freedesktop.DBus --type=method_call --print-reply       / org.freedesktop.DBus.ListNames >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

wait_for_atspi() {
  for _ in $(seq 1 60); do
    if [ -S "$XDG_RUNTIME_DIR/at-spi/bus_${DISPLAY#:}" ] || [ -S "$XDG_RUNTIME_DIR/at-spi/bus" ]; then
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

if ! dbus-send --session --dest=org.freedesktop.DBus --type=method_call --print-reply   / org.freedesktop.DBus.ListNames >/dev/null 2>&1; then
  rm -f /tmp/tua-dbus-session /tmp/tua-dbus-session*
  dbus-daemon --session --address="$DBUS_SESSION_BUS_ADDRESS" --fork >/tmp/dbus.log 2>&1
  wait_for_dbus
fi

if ! pgrep -f at-spi-bus-launcher >/dev/null 2>&1; then
  mkdir -p "$XDG_RUNTIME_DIR/at-spi"
  /usr/libexec/at-spi-bus-launcher --launch-immediately >/tmp/atspi-launcher.log 2>&1 &
  wait_for_atspi || echo "WARNING: at-spi bus socket not detected after 30s" >&2
fi
if ! pgrep -f at-spi2-registryd >/dev/null 2>&1; then
  /usr/libexec/at-spi2-registryd >/tmp/atspi-registryd.log 2>&1 &
fi

/usr/local/bin/thunderbird_state.py task >/tmp/thunderbird_state.log 2>&1 || {
  cat /tmp/thunderbird_state.log >&2 || true
  exit 1
}

cat > /tmp/tua-env.sh <<EOF
export DISPLAY="$DISPLAY"
export DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS"
export XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR"
export GNOME_ACCESSIBILITY="$GNOME_ACCESSIBILITY"
export GTK_MODULES="$GTK_MODULES"
EOF
chmod 644 /tmp/tua-env.sh

exec "$@"
