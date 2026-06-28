#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

python - <<'PY'
from docx import Document

path = '/app/LibreOffice_Open_Source_Word_Processing.docx'
doc = Document(path)
for section in doc.sections:
    footer = section.footer
    paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    paragraph.text = '1'
doc.save(path)
PY
