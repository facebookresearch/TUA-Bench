# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import itertools
import json
import traceback
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree

PLAN_PATH = Path("/app/input/task_plan.json")
REFERENCE_OBJ_PATH = Path("/tests/reference/prostate_00_prostate.obj")

PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
OBJ_OUTPUT_PATH = Path(str(PLAN["obj_output_path"]))

SAMPLE_COUNT = 10000
RELATIVE_TOLERANCE = float(PLAN.get("similarity_tolerance_relative", 0.01))


def _assert_file_nonempty(path: Path) -> None:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Expected a file at: {path}"
    assert path.stat().st_size > 0, f"Required file is empty: {path}"


def _load_mesh(path: Path) -> trimesh.Trimesh:
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
    assert np.isfinite(mesh.vertices).all(), f"Mesh contains non-finite vertices: {path}"
    assert float(mesh.area) > 0.0, f"Mesh surface area must be positive: {path}"
    return mesh


def _sample_surface_points(mesh: trimesh.Trimesh, count: int) -> np.ndarray:
    np_state = np.random.get_state()
    try:
        np.random.seed(0)
        points, _ = trimesh.sample.sample_surface(mesh, count)
    finally:
        np.random.set_state(np_state)
    points = np.asarray(points, dtype=np.float64)
    assert points.shape == (count, 3), f"Unexpected sampled point shape: {points.shape}"
    return points


def _symmetric_distance_metrics(reference_points: np.ndarray, candidate_points: np.ndarray) -> tuple[float, float]:
    reference_tree = cKDTree(reference_points)
    candidate_tree = cKDTree(candidate_points)

    candidate_to_reference = reference_tree.query(candidate_points, k=1)[0]
    reference_to_candidate = candidate_tree.query(reference_points, k=1)[0]
    all_distances = np.concatenate([candidate_to_reference, reference_to_candidate])

    mean_distance = float(all_distances.mean())
    p95_distance = float(np.quantile(all_distances, 0.95))
    return mean_distance, p95_distance


def _best_axis_aligned_metrics(reference_mesh: trimesh.Trimesh, candidate_mesh: trimesh.Trimesh) -> tuple[float, float, str]:
    reference_points = _sample_surface_points(reference_mesh, SAMPLE_COUNT)
    candidate_points = _sample_surface_points(candidate_mesh, SAMPLE_COUNT)

    reference_center = reference_mesh.bounds.mean(axis=0)
    candidate_center = candidate_mesh.bounds.mean(axis=0)
    reference_points = reference_points - reference_center
    candidate_points = candidate_points - candidate_center

    best_mean = float("inf")
    best_p95 = float("inf")
    best_transform = ""

    for permutation in itertools.permutations(range(3)):
        permuted = candidate_points[:, permutation]
        for signs in itertools.product((-1.0, 1.0), repeat=3):
            transformed = permuted * np.asarray(signs, dtype=np.float64)
            mean_distance, p95_distance = _symmetric_distance_metrics(reference_points, transformed)
            if (mean_distance < best_mean) or (
                np.isclose(mean_distance, best_mean) and p95_distance < best_p95
            ):
                best_mean = mean_distance
                best_p95 = p95_distance
                best_transform = f"perm={permutation}, signs={signs}"

    return best_mean, best_p95, best_transform


def test_obj_exists() -> None:
    _assert_file_nonempty(OBJ_OUTPUT_PATH)


def test_obj_similarity() -> None:
    _assert_file_nonempty(REFERENCE_OBJ_PATH)
    _assert_file_nonempty(OBJ_OUTPUT_PATH)

    reference_mesh = _load_mesh(REFERENCE_OBJ_PATH)
    candidate_mesh = _load_mesh(OBJ_OUTPUT_PATH)

    reference_extents = np.sort(reference_mesh.extents.astype(np.float64))
    candidate_extents = np.sort(candidate_mesh.extents.astype(np.float64))
    bbox_relative_error = np.abs(candidate_extents - reference_extents) / np.maximum(reference_extents, 1e-6)
    max_bbox_relative_error = float(bbox_relative_error.max())

    area_relative_error = float(abs(candidate_mesh.area - reference_mesh.area) / reference_mesh.area)
    mean_chamfer_mm, p95_chamfer_mm, best_transform = _best_axis_aligned_metrics(
        reference_mesh,
        candidate_mesh,
    )

    reference_diagonal_mm = float(np.linalg.norm(reference_mesh.extents.astype(np.float64)))
    mean_chamfer_relative = mean_chamfer_mm / max(reference_diagonal_mm, 1e-6)
    p95_chamfer_relative = p95_chamfer_mm / max(reference_diagonal_mm, 1e-6)

    print(
        json.dumps(
            {
                "reference_extents_mm": reference_extents.tolist(),
                "candidate_extents_mm": candidate_extents.tolist(),
                "max_bbox_relative_error": max_bbox_relative_error,
                "area_relative_error": area_relative_error,
                "mean_chamfer_mm": mean_chamfer_mm,
                "p95_chamfer_mm": p95_chamfer_mm,
                "mean_chamfer_relative": mean_chamfer_relative,
                "p95_chamfer_relative": p95_chamfer_relative,
                "relative_tolerance": RELATIVE_TOLERANCE,
                "best_axis_transform": best_transform,
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )

    assert max_bbox_relative_error <= RELATIVE_TOLERANCE, (
        f"Bounding-box relative error too large: {max_bbox_relative_error:.6f} > {RELATIVE_TOLERANCE:.6f}"
    )
    assert area_relative_error <= RELATIVE_TOLERANCE, (
        f"Surface-area relative error too large: {area_relative_error:.6f} > {RELATIVE_TOLERANCE:.6f}"
    )
    assert mean_chamfer_relative <= RELATIVE_TOLERANCE, (
        f"Mean Chamfer relative error too large: {mean_chamfer_relative:.6f} > {RELATIVE_TOLERANCE:.6f}"
    )
    assert p95_chamfer_relative <= RELATIVE_TOLERANCE, (
        f"95th-percentile Chamfer relative error too large: {p95_chamfer_relative:.6f} > {RELATIVE_TOLERANCE:.6f}"
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
            "Usage: python3 /tests/test_outputs.py <test_obj_exists|test_obj_similarity>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
