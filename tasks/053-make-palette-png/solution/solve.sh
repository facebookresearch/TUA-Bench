#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

python - <<'PY'
from PIL import Image

source_path = "/app/computer.png"
target_path = "/app/palette_computer.png"

with Image.open(source_path) as image:
    palette_image = image.convert("P", palette=Image.Palette.ADAPTIVE)
    palette_image.save(target_path)
PY
