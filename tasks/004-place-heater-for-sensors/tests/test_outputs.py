# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import math
import traceback
from pathlib import Path

ARTIFACT_DIR = Path("/app/artifacts")
RESULT_PATH = ARTIFACT_DIR / "heater_placement_result.json"
TOP_VIEW_SVG = ARTIFACT_DIR / "heater_placement_top_view.svg"
REFERENCE_PATH = Path("/tests/reference/heater_placement_solution.json")
REQUEST_PATH = Path("/app/input/heater_design_request.json")

CENTER_DISTANCE_TOLERANCE_M = 0.001
HEATER_SIZE_M = [0.01, 0.01, 0.0]
REQUIRED_SENSOR_NAMES = ["S1", "S2", "S3", "S4"]

REFERENCE = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
REQUEST = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))


def _assert_file_nonempty(path: Path) -> None:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Expected a file at: {path}"
    assert path.stat().st_size > 0, f"Required file is empty: {path}"


def _load_json_file(path: Path) -> dict:
    _assert_file_nonempty(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"Expected a JSON object in {path}"
    return payload


def _vector3(value: object, label: str) -> list[float]:
    assert isinstance(value, list) and len(value) == 3, f"{label} must be a length-3 list"
    vector = [float(component) for component in value]
    assert all(math.isfinite(component) for component in vector), f"{label} contains non-finite values"
    return vector


def _reported_center(result: dict) -> list[float]:
    if "heater_center_m" in result:
        return _vector3(result["heater_center_m"], "heater_center_m")
    origin = _vector3(result.get("heater_origin_m"), "heater_origin_m")
    return [
        origin[0] + 0.5 * HEATER_SIZE_M[0],
        origin[1] + 0.5 * HEATER_SIZE_M[1],
        origin[2] + 0.5 * HEATER_SIZE_M[2],
    ]


def _assert_center_in_domain(center: list[float]) -> None:
    domain = REQUEST["heater_origin_search_domain_m"]
    origin = [
        center[0] - 0.5 * HEATER_SIZE_M[0],
        center[1] - 0.5 * HEATER_SIZE_M[1],
        center[2],
    ]
    assert float(domain["x_min"]) <= origin[0] <= float(domain["x_max"]), (
        f"heater origin x={origin[0]} is outside the search domain"
    )
    assert float(domain["y_min"]) <= origin[1] <= float(domain["y_max"]), (
        f"heater origin y={origin[1]} is outside the search domain"
    )
    assert abs(origin[2] - float(domain["z"])) <= 1e-9, (
        f"heater z={origin[2]} does not match the top-face search plane"
    )


def test_outputs_exist() -> None:
    assert ARTIFACT_DIR.exists(), "Missing /app/artifacts"
    _assert_file_nonempty(RESULT_PATH)
    _assert_file_nonempty(TOP_VIEW_SVG)


def test_result_schema() -> None:
    result = _load_json_file(RESULT_PATH)
    _vector3(result.get("heater_origin_m"), "heater_origin_m")
    center = _reported_center(result)
    _assert_center_in_domain(center)

    sensors = result.get("predicted_sensor_temperatures")
    assert isinstance(sensors, list) and len(sensors) == 4, (
        "predicted_sensor_temperatures must contain four sensor entries"
    )
    names = sorted(str(sensor.get("name")) for sensor in sensors if isinstance(sensor, dict))
    assert names == REQUIRED_SENSOR_NAMES, f"Expected sensor names {REQUIRED_SENSOR_NAMES}, got {names}"
    for sensor in sensors:
        assert isinstance(sensor, dict), "Each sensor entry must be an object"
        _vector3(sensor.get("point_m"), f"{sensor.get('name')}.point_m")
        for key in ("temperature_K", "target_temperature_K", "error_K"):
            value = float(sensor[key])
            assert math.isfinite(value), f"{sensor.get('name')}.{key} must be finite"

    max_abs_error = float(result.get("max_abs_error_K"))
    assert math.isfinite(max_abs_error), "max_abs_error_K must be finite"
    assert isinstance(result.get("method_summary"), str) and result["method_summary"].strip(), (
        "method_summary must be a nonempty string"
    )


def test_heater_center_matches_reference() -> None:
    result = _load_json_file(RESULT_PATH)
    actual = _reported_center(result)
    expected = [float(value) for value in REFERENCE["heater_center_m"]]
    _assert_center_in_domain(actual)

    component_abs_errors_m = {
        axis: abs(actual_value - expected_value)
        for axis, actual_value, expected_value in zip(("x", "y", "z"), actual, expected)
    }
    center_distance_m = math.sqrt(
        sum((actual_value - expected_value) ** 2 for actual_value, expected_value in zip(actual, expected))
    )
    print(
        json.dumps(
            {
                "actual_heater_center_m": actual,
                "center_distance_m": center_distance_m,
                "component_abs_errors_m": component_abs_errors_m,
                "distance_tolerance_m": CENTER_DISTANCE_TOLERANCE_M,
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    assert center_distance_m <= CENTER_DISTANCE_TOLERANCE_M, (
        f"Heater center is {center_distance_m * 1000.0:.3f} mm from reference; "
        f"allowed {CENTER_DISTANCE_TOLERANCE_M * 1000.0:.3f} mm"
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
            "<test_outputs_exist|test_result_schema|test_heater_center_matches_reference>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
