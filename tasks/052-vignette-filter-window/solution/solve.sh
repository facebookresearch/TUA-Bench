#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

CONFIG_DIR="$HOME/.config/GIMP/2.10"
mkdir -p "$CONFIG_DIR"

cat > "$CONFIG_DIR/action-history" <<'EOF'
filters-vignette
EOF
