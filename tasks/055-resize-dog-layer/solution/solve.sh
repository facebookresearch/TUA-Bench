#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

python - <<'PY'
from PIL import Image

with Image.open("/app/dog_with_background.png") as image:
    width, height = image.size
    new_height = 512
    new_width = round(width * new_height / height)
    image.resize((new_width, new_height), Image.Resampling.LANCZOS).save("/app/resized.png")
PY
