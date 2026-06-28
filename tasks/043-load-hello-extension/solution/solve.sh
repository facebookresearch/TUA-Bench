#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

DESKTOP_DIR="$HOME/Desktop"
PREFERENCES_DIR="$HOME/.config/google-chrome/Default"
PREFERENCES_PATH="$PREFERENCES_DIR/Preferences"
EXPECTED_PATH="$DESKTOP_DIR/helloExtension"

pkill -f "chromium|google-chrome" >/dev/null 2>&1 || true
sleep 1

mkdir -p "$DESKTOP_DIR" "$PREFERENCES_DIR"

if [ -f "$DESKTOP_DIR/helloExtension.zip" ]; then
  unzip -oq "$DESKTOP_DIR/helloExtension.zip" -d "$DESKTOP_DIR"
fi
rm -rf "$DESKTOP_DIR/__MACOSX"

cat > "$PREFERENCES_PATH" <<EOF
{
  "extensions": {
    "settings": {
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa": {
        "path": "$EXPECTED_PATH"
      }
    }
  }
}
EOF
