#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

[ -f /tmp/tua-env.sh ] && . /tmp/tua-env.sh

export DISPLAY="${DISPLAY:-:99}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/tmp/tua-dbus-session}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg-runtime-$(id -u)}"
export GNOME_ACCESSIBILITY="${GNOME_ACCESSIBILITY:-1}"
export GTK_MODULES="${GTK_MODULES:-gail:atk-bridge}"
export TUA_THUNDERBIRD_BIN="${TUA_THUNDERBIRD_BIN:-/usr/local/bin/thunderbird}"
unset NO_AT_BRIDGE

mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

dbus_ready() {
  dbus-send --session --reply-timeout=1000 --dest=org.freedesktop.DBus --type=method_call --print-reply \
    / org.freedesktop.DBus.ListNames >/dev/null 2>&1
}

wait_for_dbus() {
  for _ in $(seq 1 60); do
    if dbus_ready; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

a11y_bus_ready() {
  dbus-send --session --reply-timeout=1000 --dest=org.freedesktop.DBus --type=method_call --print-reply=literal \
    / org.freedesktop.DBus.NameHasOwner string:org.a11y.Bus 2>/dev/null | grep -Eq '\btrue\b'
}

wait_for_a11y_bus() {
  for _ in $(seq 1 60); do
    if a11y_bus_ready; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

ensure_verifier_a11y() {
  if ! dbus_ready; then
    rm -f /tmp/tua-dbus-session /tmp/tua-dbus-session*
    pkill -f "dbus-daemon --session" >/dev/null 2>&1 || true
    dbus-daemon --session --address="$DBUS_SESSION_BUS_ADDRESS" --fork >/tmp/verifier-dbus.log 2>&1 || true
    wait_for_dbus || return 1
  fi

  if a11y_bus_ready; then
    return 0
  fi

  dbus-send --session --reply-timeout=1000 --dest=org.freedesktop.DBus --type=method_call --print-reply \
    / org.freedesktop.DBus.StartServiceByName string:org.a11y.Bus uint32:0 >/tmp/verifier-atspi-activation.log 2>&1 || true
  if wait_for_a11y_bus; then
    return 0
  fi

  mkdir -p "$XDG_RUNTIME_DIR/at-spi"
  pkill -f at-spi-bus-launcher >/dev/null 2>&1 || true
  pkill -f at-spi2-registryd >/dev/null 2>&1 || true
  /usr/libexec/at-spi-bus-launcher --launch-immediately >/tmp/verifier-atspi-launcher.log 2>&1 &
  /usr/libexec/at-spi2-registryd >/tmp/verifier-atspi-registryd.log 2>&1 &
  wait_for_a11y_bus
}

persist_artifacts() {
  mkdir -p /logs/artifacts || true
  ps -eo pid=,ppid=,stat=,args= >/tmp/processes.txt 2>&1 || true
  pgrep -a thunderbird >/tmp/thunderbird-processes.txt 2>&1 || true
  xlsclients -display "$DISPLAY" -l >/tmp/xlsclients.txt 2>&1 || true
  if [ -f /tmp/accessibility_tree.xml ]; then
    cp /tmp/accessibility_tree.xml /logs/artifacts/accessibility_tree.xml || true
  fi
  if [ -f /tmp/accessibility_tree_error.txt ]; then
    cp /tmp/accessibility_tree_error.txt /logs/artifacts/accessibility_tree_error.txt || true
  fi
  if [ -f /tmp/thunderbird-attachment-check.txt ]; then
    cp /tmp/thunderbird-attachment-check.txt /logs/artifacts/thunderbird-attachment-check.txt || true
  fi
  if [ -f /tmp/tua-env.sh ]; then
    cp /tmp/tua-env.sh /logs/artifacts/tua-env.sh || true
  fi
  if [ -f /tmp/thunderbird.log ]; then
    cp /tmp/thunderbird.log /logs/artifacts/thunderbird.log || true
  fi
  if [ -f /tmp/thunderbird_state.log ]; then
    cp /tmp/thunderbird_state.log /logs/artifacts/thunderbird_state.log || true
  fi
  if [ -f /tmp/thunderbird-live-helper.log ]; then
    cp /tmp/thunderbird-live-helper.log /logs/artifacts/thunderbird-live-helper.log || true
  fi
  if [ -f /tmp/xvfb.log ]; then
    cp /tmp/xvfb.log /logs/artifacts/xvfb.log || true
  fi
  if [ -f /tmp/dbus.log ]; then
    cp /tmp/dbus.log /logs/artifacts/dbus.log || true
  fi
  if [ -f /tmp/atspi-launcher.log ]; then
    cp /tmp/atspi-launcher.log /logs/artifacts/atspi-launcher.log || true
  fi
  if [ -f /tmp/atspi-registryd.log ]; then
    cp /tmp/atspi-registryd.log /logs/artifacts/atspi-registryd.log || true
  fi
  if [ -f /tmp/verifier-dbus.log ]; then
    cp /tmp/verifier-dbus.log /logs/artifacts/verifier-dbus.log || true
  fi
  if [ -f /tmp/verifier-atspi-activation.log ]; then
    cp /tmp/verifier-atspi-activation.log /logs/artifacts/verifier-atspi-activation.log || true
  fi
  if [ -f /tmp/verifier-atspi-launcher.log ]; then
    cp /tmp/verifier-atspi-launcher.log /logs/artifacts/verifier-atspi-launcher.log || true
  fi
  if [ -f /tmp/verifier-atspi-registryd.log ]; then
    cp /tmp/verifier-atspi-registryd.log /logs/artifacts/verifier-atspi-registryd.log || true
  fi
  if [ -f /tmp/processes.txt ]; then
    cp /tmp/processes.txt /logs/artifacts/processes.txt || true
  fi
  if [ -f /tmp/thunderbird-processes.txt ]; then
    cp /tmp/thunderbird-processes.txt /logs/artifacts/thunderbird-processes.txt || true
  fi
  if [ -f /tmp/xlsclients.txt ]; then
    cp /tmp/xlsclients.txt /logs/artifacts/xlsclients.txt || true
  fi
}

trap persist_artifacts EXIT

mkdir -p /logs/verifier || true
mkdir -p /logs/artifacts || true
ensure_verifier_a11y || echo "WARNING: verifier accessibility bus bootstrap did not complete" >&2

if /opt/venv/bin/python -m pytest -q -s -p no:cacheprovider /tests/test_outputs.py::test_main -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
