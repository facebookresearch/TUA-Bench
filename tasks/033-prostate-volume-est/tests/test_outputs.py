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

import trimesh

PLAN_PATH = Path("/app/input/task_plan.json")
REFERENCE_OBJ_PATH = Path("/tests/reference/prostate_00_prostate.obj")

PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
VOLUME_OUTPUT_PATH = Path(str(PLAN["volume_output_path"]))
RELATIVE_TOLERANCE = float(PLAN.get("relative_tolerance", 0.05))


def _assert_file_nonempty(path: Path) -> None:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Expected a file at: {path}"
    assert path.stat().st_size > 0, f"Required file is empty: {path}"


def _parse_single_number(path: Path) -> float:
    _assert_file_nonempty(path)
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    assert re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text), (
        f"Expected exactly one numeric value in {path}, got: {text!r}"
    )
    value = float(text)
    assert value > 0.0, f"Volume must be positive, got {value}"
    return value


def _load_mesh(path: Path) -> trimesh.Trimesh:
    _assert_file_nonempty(path)
    loaded = trimesh.load(path, force="scene", process=False)
    if isinstance(loaded, trimesh.Scene):
        meshes = [
            geometry.copy()
            for geometry in loaded.geometry.values()
            if isinstance(geometry, trimesh.Trimesh)
            and geometry.vertices.shape[0] > 0
            and geometry.faces.shape[0] > 0
        ]
        assert meshes, f"No mesh geometry found in {path}"
        mesh = meshes[0] if len(meshes) == 1 else trimesh.util.concatenate(meshes)
    else:
        assert isinstance(loaded, trimesh.Trimesh), f"Unsupported mesh type for {path}: {type(loaded)!r}"
        mesh = loaded.copy()
    mesh.remove_unreferenced_vertices()
    assert mesh.vertices.shape[0] > 0, f"Mesh has no vertices: {path}"
    assert mesh.faces.shape[0] > 0, f"Mesh has no faces: {path}"
    assert mesh.is_watertight, f"Reference mesh is not watertight: {path}"
    return mesh


def _reference_volume_cm3() -> float:
    mesh = _load_mesh(REFERENCE_OBJ_PATH)
    volume_mm3 = abs(float(mesh.volume))
    assert volume_mm3 > 0.0, f"Reference mesh volume must be positive, got {volume_mm3}"
    return volume_mm3 / 1000.0


def test_volume_exists() -> None:
    _assert_file_nonempty(VOLUME_OUTPUT_PATH)


def test_volume_is_numeric() -> None:
    _parse_single_number(VOLUME_OUTPUT_PATH)


def test_volume_matches_reference() -> None:
    actual_cm3 = _parse_single_number(VOLUME_OUTPUT_PATH)
    expected_cm3 = _reference_volume_cm3()
    relative_error = abs(actual_cm3 - expected_cm3) / expected_cm3
    print(
        json.dumps(
            {
                "actual_volume_cm3": actual_cm3,
                "expected_volume_cm3": expected_cm3,
                "relative_error": relative_error,
                "relative_tolerance": RELATIVE_TOLERANCE,
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    assert relative_error <= RELATIVE_TOLERANCE, (
        f"Volume estimate differs by {relative_error:.3%}; allowed {RELATIVE_TOLERANCE:.3%}"
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
            "<test_volume_exists|test_volume_is_numeric|test_volume_matches_reference>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
