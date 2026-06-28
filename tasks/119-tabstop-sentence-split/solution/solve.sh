#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

TMP_DIR="/tmp/119-tabstop-sentence-split"
TMP_PATH="$TMP_DIR/04 CHIN9505 EBook Purchasing info 2021 Jan.docx"
mkdir -p "$TMP_DIR"
curl -fL --retry 3 --retry-delay 1 https://huggingface.co/datasets/xlangai/ubuntu_osworld_file_cache/resolve/main/libreoffice_writer/0a0faba3-5580-44df-965d-f562a99b291c/04%20CHIN9505%20EBook%20Purchasing%20info%202021%20Jan_Gold.docx -o "$TMP_PATH"
cp "$TMP_PATH" '/app/04 CHIN9505 EBook Purchasing info 2021 Jan.docx'

python - <<'PY'
import re
from docx import Document

path = '/app/04 CHIN9505 EBook Purchasing info 2021 Jan.docx'
doc = Document(path)
for paragraph in doc.paragraphs:
    if not paragraph.text.strip() or "\t" not in paragraph.text:
        continue
    left, right = paragraph.text.split("\t", 1)
    left_words = [word for word in re.split(r"\s+", left.strip()) if word]
    right_words = [word for word in re.split(r"\s+", right.strip()) if word]
    if len(left_words) < 3 and right_words:
        move_count = min(3 - len(left_words), len(right_words))
        left_words.extend(right_words[:move_count])
        right_words = right_words[move_count:]
    paragraph.text = " ".join(left_words) + "\t" + " ".join(right_words)
doc.save(path)
PY
