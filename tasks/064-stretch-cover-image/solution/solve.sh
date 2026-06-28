#!/usr/bin/env bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
AGENT_HOME="${AGENT_HOME:-/home/agent}"
export APP_DIR AGENT_HOME

python - <<'PY'
import os
from pathlib import Path

APP_DIR = Path(os.environ['APP_DIR'])
AGENT_HOME = Path(os.environ['AGENT_HOME'])

def localize_path(path: str) -> Path:
    if path.startswith('/app/'):
        return APP_DIR / path.removeprefix('/app/')
    if path.startswith('/home/agent/'):
        return AGENT_HOME / path.removeprefix('/home/agent/')
    return Path(path)

output_path = localize_path("/app/CPD_Background_Investigation_Process.pptx")
from pptx import Presentation

presentation = Presentation(output_path)
slide = presentation.slides[0]
pictures = [shape for shape in slide.shapes if shape.shape_type == 13]
if not pictures:
    raise RuntimeError("Could not locate the slide 1 picture")
picture = pictures[0]
picture.left = 0
picture.top = 0
picture.width = presentation.slide_width
picture.height = presentation.slide_height
presentation.save(output_path)
PY
