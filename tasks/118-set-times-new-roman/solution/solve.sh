#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

python - <<'PY'
from docx import Document

path = '/app/Dublin_Zoo_Intro.docx'
font_name = 'Times New Roman'
doc = Document(path)
for paragraph in doc.paragraphs:
    for run in paragraph.runs:
        run.font.name = font_name
doc.save(path)
PY
