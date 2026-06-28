# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import csv
import hashlib
import json
import traceback
from pathlib import Path

REFERENCE_CSV_PATH = Path("/tests/reference/Nuclei.csv")
OUTPUT_CSV_PATH = Path("/app/artifacts/Nuclei.csv")
EXPECTED_ROWS = 6


def _assert_file_nonempty(path: Path) -> None:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Expected a file at: {path}"
    assert path.stat().st_size > 0, f"Required file is empty: {path}"


def _read_csv(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


def _csv_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_output_exists() -> None:
    _assert_file_nonempty(OUTPUT_CSV_PATH)


def test_csv_shape() -> None:
    _assert_file_nonempty(REFERENCE_CSV_PATH)
    _assert_file_nonempty(OUTPUT_CSV_PATH)

    reference_rows = _read_csv(REFERENCE_CSV_PATH)
    candidate_rows = _read_csv(OUTPUT_CSV_PATH)

    assert reference_rows, "Reference CSV is empty"
    assert candidate_rows, "Candidate CSV is empty"

    assert candidate_rows[0] == reference_rows[0], "CSV header does not match the reference header"
    assert len(candidate_rows) - 1 == EXPECTED_ROWS, (
        f"Unexpected number of data rows: expected {EXPECTED_ROWS}, got {len(candidate_rows) - 1}"
    )
    assert len(candidate_rows) == len(reference_rows), (
        f"Unexpected total number of rows: expected {len(reference_rows)}, got {len(candidate_rows)}"
    )
    assert all(len(row) == len(reference_rows[0]) for row in candidate_rows), "CSV row width is inconsistent"


def test_csv_similarity() -> None:
    _assert_file_nonempty(REFERENCE_CSV_PATH)
    _assert_file_nonempty(OUTPUT_CSV_PATH)

    reference_rows = _read_csv(REFERENCE_CSV_PATH)
    candidate_rows = _read_csv(OUTPUT_CSV_PATH)

    print(
        json.dumps(
            {
                "reference_sha256": _csv_digest(REFERENCE_CSV_PATH),
                "candidate_sha256": _csv_digest(OUTPUT_CSV_PATH),
                "reference_rows": len(reference_rows) - 1,
                "candidate_rows": len(candidate_rows) - 1,
                "reference_columns": len(reference_rows[0]) if reference_rows else 0,
                "candidate_columns": len(candidate_rows[0]) if candidate_rows else 0,
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )

    assert candidate_rows == reference_rows, "Generated CSV does not match the hidden GT exactly"


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
            "<test_output_exists|test_csv_shape|test_csv_similarity>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
