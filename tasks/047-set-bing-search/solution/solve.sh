#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

PREFERENCES_DIR="$HOME/.config/google-chrome/Default"
mkdir -p "$PREFERENCES_DIR"

cat > "$PREFERENCES_DIR/Preferences" <<'EOF'
{
  "default_search_provider_data": {
    "template_url_data": {
      "short_name": "Bing"
    }
  }
}
EOF
