#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

python - <<'PY'
from PIL import Image, ImageDraw

image = Image.new("RGB", (1200, 700), "orange")
draw = ImageDraw.Draw(image)
draw.rectangle((0, 240, 220, 420), fill="white")
draw.text((18, 285), "Textbox", fill="black")
image.save("/app/leftside_textbox.png")
PY
