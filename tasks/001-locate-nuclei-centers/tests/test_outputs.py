# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import csv
import itertools
import traceback
from pathlib import Path

REFERENCE_CSV_PATH = Path("/tests/reference/Nuclei.csv")
OUTPUT_LOCATIONS_PATH = Path("/app/artifacts/nuclei_locations.csv")
RELATIVE_TOLERANCE = 0.05


def _assert_file_nonempty(path: Path) -> None:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Expected a file at: {path}"
    assert path.stat().st_size > 0, f"Required file is empty: {path}"


def _reference_locations() -> list[tuple[float, float]]:
    _assert_file_nonempty(REFERENCE_CSV_PATH)
    with REFERENCE_CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None, "Reference CSV is missing a header"
        return [
            (float(row["Location_Center_X"]), float(row["Location_Center_Y"]))
            for row in reader
        ]


def _candidate_locations() -> list[tuple[float, float]]:
    _assert_file_nonempty(OUTPUT_LOCATIONS_PATH)
    with OUTPUT_LOCATIONS_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None, "Location CSV is missing a header"
        field_map = {name.strip().lower(): name for name in reader.fieldnames}

        x_field = field_map.get("x") or field_map.get("location_center_x")
        y_field = field_map.get("y") or field_map.get("location_center_y")
        assert x_field is not None, "Location CSV must include an x column"
        assert y_field is not None, "Location CSV must include a y column"

        locations: list[tuple[float, float]] = []
        for index, row in enumerate(reader, start=2):
            try:
                locations.append((float(row[x_field]), float(row[y_field])))
            except (TypeError, ValueError) as exc:
                raise AssertionError(f"Invalid numeric coordinate on CSV row {index}") from exc
        return locations


def _within_tolerance(candidate: tuple[float, float], reference: tuple[float, float]) -> bool:
    candidate_x, candidate_y = candidate
    reference_x, reference_y = reference
    return (
        abs(candidate_x - reference_x) <= abs(reference_x) * RELATIVE_TOLERANCE
        and abs(candidate_y - reference_y) <= abs(reference_y) * RELATIVE_TOLERANCE
    )


def test_output_exists() -> None:
    _assert_file_nonempty(OUTPUT_LOCATIONS_PATH)


def test_locations_match_reference() -> None:
    reference = _reference_locations()
    candidate = _candidate_locations()

    print(f"expected_locations={len(reference)}", flush=True)
    print(f"candidate_locations={len(candidate)}", flush=True)

    assert reference, "Reference location list is empty"
    assert len(candidate) == len(reference), (
        f"Expected {len(reference)} nucleus locations, got {len(candidate)}"
    )

    for permutation in itertools.permutations(candidate):
        if all(
            _within_tolerance(candidate_point, reference_point)
            for candidate_point, reference_point in zip(permutation, reference)
        ):
            return

    tolerance_percent = int(RELATIVE_TOLERANCE * 100)
    raise AssertionError(
        f"No one-to-one assignment of candidate locations matched the reference "
        f"within {tolerance_percent}% coordinate-wise tolerance"
    )


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
            "<test_output_exists|test_locations_match_reference>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
