# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

TASK_SPEC = {
    "slug": "118-set-times-new-roman",
    "output_path": "/app/Dublin_Zoo_Intro.docx",
    "metric_spec": {
        "func": "compare_font_names",
        "result": "/app/Dublin_Zoo_Intro.docx",
        "options": {},
        "expected": {"type": "rule", "rules": {"font_name": "Times New Roman"}},
    },
}

import logging

from docx import Document

logger = logging.getLogger("tua.writer.osworld")
logging.basicConfig(level=logging.INFO)


def compare_font_names(docx_file, rules):
    if not docx_file:
        return 0

    try:
        doc = Document(docx_file)
    except Exception as exc:
        logger.error("Error: %s", exc)
        return 0

    expected_font = rules["font_name"]
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            if run.font.name != expected_font:
                return 0

    return 1


def run_evaluation():
    metric_spec = TASK_SPEC["metric_spec"]
    expected_spec = metric_spec["expected"]
    if expected_spec["type"] != "rule":
        raise ValueError(f"Unsupported expected spec: {expected_spec}")

    return float(compare_font_names(metric_spec["result"], expected_spec["rules"]))


if __name__ == "__main__":
    print(run_evaluation())
