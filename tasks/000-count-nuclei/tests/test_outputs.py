# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import csv
import re
import traceback
from pathlib import Path

REFERENCE_CSV_PATH = Path("/tests/reference/Nuclei.csv")
OUTPUT_COUNT_PATH = Path("/app/artifacts/nuclei_count.txt")


def _assert_file_nonempty(path: Path) -> None:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Expected a file at: {path}"
    assert path.stat().st_size > 0, f"Required file is empty: {path}"


def _expected_count() -> int:
    _assert_file_nonempty(REFERENCE_CSV_PATH)
    with REFERENCE_CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows, "Reference CSV is empty"
    return len(rows) - 1


def _candidate_count() -> int:
    _assert_file_nonempty(OUTPUT_COUNT_PATH)
    text = OUTPUT_COUNT_PATH.read_text(encoding="utf-8").strip()
    assert text, "Count output is empty"
    assert re.fullmatch(
        r"\d+", text
    ), "Count output must contain only a non-negative integer"
    return int(text)


def test_output_exists() -> None:
    _assert_file_nonempty(OUTPUT_COUNT_PATH)


def test_count_matches_reference() -> None:
    expected = _expected_count()
    candidate = _candidate_count()
    print(f"expected_count={expected}", flush=True)
    print(f"candidate_count={candidate}", flush=True)
    assert candidate == expected, f"Expected nuclei count {expected}, got {candidate}"


def _run_named_test(test_name: str) -> int:
    fn = globals().get(test_name)
    if fn is None or not callable(fn):
        print(f"Unknown test function: {test_name}", flush=True)
        return 2
    try:
        fn()
    except Exception:
        traceback.print_exc()
        return 1
    print(f"{test_name}: PASS", flush=True)
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: python3 /tests/test_outputs.py "
            "<test_output_exists|test_count_matches_reference>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
