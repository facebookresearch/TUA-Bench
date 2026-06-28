# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import re
import traceback
from pathlib import Path

GROUND_TRUTH_PATH = Path("/tests/reference/simple_plate_ground_truth_120s.json")

GROUND_TRUTH = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))

ARTIFACT_DIR = Path("/app/artifacts")
CASE_DIR = Path("/app/artifacts/simple_plate_case")
METRICS_OUTPUT = Path("/app/artifacts/simple_plate_result_120s.json")
TOP_VIEW_SVG = Path("/app/artifacts/simple_plate_top_view.svg")
FINAL_FIELD_PATH = Path("/app/artifacts/simple_plate_case/120/T")
SOLVER_LOG_PATH = Path("/app/artifacts/simple_plate_case/log.laplacianFoam")
RELATIVE_TOLERANCE = 0.01
REQUIRED_METRIC_KEYS = [
    "internal_min_temperature_K",
    "internal_max_temperature_K",
    "top_surface_min_temperature_K",
    "top_surface_max_temperature_K",
    "reported_min_temperature_K",
    "reported_max_temperature_K",
]
REQUIRED_PATCHES = [
    "heatSource",
    "topRest",
    "bottomSink",
    "xmin",
    "xmax",
    "ymin",
    "ymax",
]

FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?")


def _assert_file_nonempty(path: Path) -> None:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Expected a file at: {path}"
    assert path.stat().st_size > 0, f"Required file is empty: {path}"


def _load_json_file(path: Path) -> dict:
    _assert_file_nonempty(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"Expected a JSON object in {path}"
    return payload


def _relative_error(actual: float, expected: float) -> float:
    denominator = max(abs(expected), 1e-12)
    return abs(actual - expected) / denominator


def _assert_close(actual: float, expected: float, label: str) -> None:
    error = _relative_error(actual, expected)
    assert error <= RELATIVE_TOLERANCE, (
        f"{label} differs by {error:.3%}; expected {expected}, got {actual}; "
        f"allowed {RELATIVE_TOLERANCE:.3%}"
    )


def _candidate_metrics_block(payload: dict) -> dict:
    for key in ("metrics", "reference_metrics"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return payload


def _patch_block(text: str, patch_name: str) -> str:
    match = re.search(rf"^\s*{re.escape(patch_name)}\s*\{{", text, re.M)
    assert match, f"Could not find boundary patch {patch_name!r} in final T field"
    start = match.end()
    depth = 1
    index = start
    while index < len(text) and depth:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0, f"Boundary patch {patch_name!r} has an unterminated block"
    return text[start : index - 1]


def _parse_scalar_list_after(keyword: str, text: str) -> list[float]:
    nonuniform = re.search(
        rf"{keyword}\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if nonuniform:
        return [float(token) for token in FLOAT_RE.findall(nonuniform.group(1))]

    uniform = re.search(rf"{keyword}\s+uniform\s+({FLOAT_RE.pattern})\s*;", text)
    if uniform:
        return [float(uniform.group(1))]

    raise AssertionError(f"Could not parse {keyword} scalar values")


def _field_metrics_from_t(path: Path) -> dict[str, float]:
    _assert_file_nonempty(path)
    text = path.read_text(encoding="ascii", errors="ignore")
    internal = _parse_scalar_list_after("internalField", text)
    assert len(internal) > 100, f"Expected a real mesh field, got {len(internal)} internal values"

    top_temperatures: list[float] = []
    for patch_name in ("heatSource", "topRest"):
        top_temperatures.extend(_parse_scalar_list_after("value", _patch_block(text, patch_name)))
    assert top_temperatures, "No top-surface boundary temperatures found"

    reported = internal + top_temperatures
    return {
        "internal_min_temperature_K": min(internal),
        "internal_max_temperature_K": max(internal),
        "top_surface_min_temperature_K": min(top_temperatures),
        "top_surface_max_temperature_K": max(top_temperatures),
        "reported_min_temperature_K": min(reported),
        "reported_max_temperature_K": max(reported),
    }


def test_outputs_exist() -> None:
    assert ARTIFACT_DIR.exists(), "Missing /app/artifacts"
    assert CASE_DIR.exists() and CASE_DIR.is_dir(), f"Missing case directory: {CASE_DIR}"
    _assert_file_nonempty(METRICS_OUTPUT)
    _assert_file_nonempty(TOP_VIEW_SVG)
    _assert_file_nonempty(FINAL_FIELD_PATH)
    _assert_file_nonempty(SOLVER_LOG_PATH)


def test_metrics_match_ground_truth() -> None:
    candidate = _load_json_file(METRICS_OUTPUT)
    candidate_metrics = _candidate_metrics_block(candidate)
    expected_metrics = GROUND_TRUTH["reference_metrics"]

    _assert_close(float(candidate["final_time_s"]), float(GROUND_TRUTH["final_time_s"]), "final_time_s")

    candidate_mesh = candidate.get("mesh")
    assert isinstance(candidate_mesh, dict), "Candidate metrics JSON must contain a mesh object"
    expected_mesh = GROUND_TRUTH["mesh"]
    for key in ("cell_count", "point_count", "face_count", "internal_face_count"):
        _assert_close(float(candidate_mesh[key]), float(expected_mesh[key]), f"mesh.{key}")

    candidate_patch_counts = candidate_mesh.get("patch_face_counts")
    assert isinstance(candidate_patch_counts, dict), "mesh.patch_face_counts must be a JSON object"
    for patch_name in REQUIRED_PATCHES:
        _assert_close(
            float(candidate_patch_counts[patch_name]),
            float(expected_mesh["patch_face_counts"][patch_name]),
            f"mesh.patch_face_counts.{patch_name}",
        )

    for key in REQUIRED_METRIC_KEYS:
        assert key in candidate_metrics, f"Missing metric {key!r}"
        _assert_close(float(candidate_metrics[key]), float(expected_metrics[key]), f"metrics.{key}")

    print(
        json.dumps(
            {
                "checked_mesh_keys": ["cell_count", "point_count", "face_count", "internal_face_count"],
                "checked_metric_keys": REQUIRED_METRIC_KEYS,
                "relative_tolerance": RELATIVE_TOLERANCE,
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )


def test_final_field_supports_metrics() -> None:
    candidate = _load_json_file(METRICS_OUTPUT)
    candidate_metrics = _candidate_metrics_block(candidate)
    field_metrics = _field_metrics_from_t(FINAL_FIELD_PATH)
    expected_metrics = GROUND_TRUTH["reference_metrics"]

    for key in REQUIRED_METRIC_KEYS:
        _assert_close(float(field_metrics[key]), float(candidate_metrics[key]), f"field_vs_json.{key}")
        _assert_close(float(field_metrics[key]), float(expected_metrics[key]), f"field_vs_ground_truth.{key}")

    print(json.dumps(field_metrics, indent=2, sort_keys=True), flush=True)


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
            "<test_outputs_exist|test_metrics_match_ground_truth|test_final_field_supports_metrics>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
