# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import traceback
from pathlib import Path

import nibabel as nib
import numpy as np

PLAN_PATH = Path("/app/input/task_plan.json")
REFERENCE_LABEL_PATH = Path("/tests/reference/prostate_00_label_backup.nii.gz")

PLAN = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
OVERLAY_OUTPUT_PATH = Path(str(PLAN["overlay_output_path"]))
SLICE_AREA_RELATIVE_TOLERANCE = float(PLAN.get("slice_area_relative_tolerance", 0.05))


def _assert_file_nonempty(path: Path) -> None:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Expected a file at: {path}"
    assert path.stat().st_size > 0, f"Required file is empty: {path}"


def _squeeze_non_color_singletons(array: np.ndarray) -> np.ndarray:
    arr = np.asarray(array)
    if arr.ndim == 0:
        return arr

    color_axis = arr.ndim - 1 if arr.shape[-1] in (3, 4) else None
    if color_axis is None:
        for axis, size in enumerate(arr.shape):
            if size in (3, 4):
                color_axis = axis
                break

    squeeze_axes = [
        axis for axis, size in enumerate(arr.shape) if size == 1 and axis != color_axis
    ]
    if squeeze_axes:
        arr = np.squeeze(arr, axis=tuple(squeeze_axes))
    return arr


def _load_label_mask(path: Path) -> np.ndarray:
    _assert_file_nonempty(path)
    data = np.asanyarray(nib.load(str(path)).dataobj)
    data = np.squeeze(data)
    assert data.ndim == 3, f"Reference label must be 3D after squeezing, got {data.shape}"
    return data > 0


def _load_red_mask(path: Path) -> np.ndarray:
    _assert_file_nonempty(path)
    data = np.asanyarray(nib.load(str(path)).dataobj)

    if data.dtype.fields:
        field_names = {name.lower(): name for name in data.dtype.fields}
        assert {"r", "g", "b"}.issubset(field_names), (
            f"Structured RGB NIfTI must contain R, G, and B fields, got {list(data.dtype.fields)}"
        )
        r = np.asarray(data[field_names["r"]], dtype=np.float32)
        g = np.asarray(data[field_names["g"]], dtype=np.float32)
        b = np.asarray(data[field_names["b"]], dtype=np.float32)
    else:
        arr = _squeeze_non_color_singletons(np.asarray(data))
        assert arr.ndim >= 4 and arr.shape[-1] in (3, 4), (
            "Expected an RGB/RGBA NIfTI with color in the final dimension; "
            f"got {arr.shape} and dtype {arr.dtype}"
        )
        rgb = arr.astype(np.float32, copy=False)
        r = rgb[..., 0]
        g = rgb[..., 1]
        b = rgb[..., 2]

    scale = 255.0 if max(float(np.nanmax(r)), float(np.nanmax(g)), float(np.nanmax(b))) > 1.5 else 1.0
    red = (
        np.isfinite(r)
        & np.isfinite(g)
        & np.isfinite(b)
        & (r > 0.45 * scale)
        & ((r - np.maximum(g, b)) > 0.15 * scale)
        & (r > 1.15 * g)
        & (r > 1.15 * b)
    )
    red = np.squeeze(red)
    while red.ndim > 3:
        red = np.any(red, axis=-1)
    assert red.ndim == 3, f"Red mask must be 3D after extracting RGB voxels, got {red.shape}"
    return red


def _slice_transforms(slice_mask: np.ndarray) -> list[np.ndarray]:
    candidates: list[np.ndarray] = []
    seen: set[tuple[tuple[int, ...], bytes]] = set()
    for k in range(4):
        rotated = np.rot90(slice_mask, k=k)
        for transformed in (
            rotated,
            np.fliplr(rotated),
            np.flipud(rotated),
            np.flipud(np.fliplr(rotated)),
        ):
            key = (transformed.shape, np.ascontiguousarray(transformed).tobytes())
            if key not in seen:
                seen.add(key)
                candidates.append(transformed)
    return candidates


def _slice_relative_error(candidate: np.ndarray, reference: np.ndarray) -> float:
    ref_area = int(np.count_nonzero(reference))
    cand_area = int(np.count_nonzero(candidate))
    if ref_area == 0:
        return cand_area / float(reference.size)
    return int(np.count_nonzero(np.logical_xor(candidate, reference))) / float(ref_area)


def _best_slice_error(candidate_slice: np.ndarray, reference_slice: np.ndarray) -> float:
    compatible = [
        transformed
        for transformed in _slice_transforms(candidate_slice)
        if transformed.shape == reference_slice.shape
    ]
    assert compatible, (
        f"No allowed in-plane rotation/flip can map candidate slice shape "
        f"{candidate_slice.shape} to reference shape {reference_slice.shape}"
    )
    return min(_slice_relative_error(transformed, reference_slice) for transformed in compatible)


def _compare_slice_masks(candidate: np.ndarray, reference: np.ndarray) -> dict[str, object]:
    assert candidate.ndim == 3 and reference.ndim == 3
    assert candidate.shape[2] == reference.shape[2], (
        f"Expected the same number of axial slices, got candidate {candidate.shape[2]} "
        f"and reference {reference.shape[2]}"
    )

    per_slice_errors: list[float] = []
    failed_slices: list[dict[str, float | int]] = []
    gt_nonempty_slices = 0

    for z in range(reference.shape[2]):
        reference_slice = reference[:, :, z]
        candidate_slice = candidate[:, :, z]
        error = _best_slice_error(candidate_slice, reference_slice)
        per_slice_errors.append(error)
        if np.any(reference_slice):
            gt_nonempty_slices += 1
        if error > SLICE_AREA_RELATIVE_TOLERANCE:
            failed_slices.append(
                {
                    "slice": z,
                    "relative_error": error,
                    "candidate_red_area": int(np.count_nonzero(candidate_slice)),
                    "reference_area": int(np.count_nonzero(reference_slice)),
                }
            )

    assert gt_nonempty_slices > 0, "Reference label has no prostate voxels"
    return {
        "slice_count": reference.shape[2],
        "nonempty_reference_slices": gt_nonempty_slices,
        "max_slice_relative_error": max(per_slice_errors),
        "mean_slice_relative_error": float(np.mean(per_slice_errors)),
        "slice_area_relative_tolerance": SLICE_AREA_RELATIVE_TOLERANCE,
        "failed_slices": failed_slices[:20],
        "failed_slice_count": len(failed_slices),
    }


def test_overlay_exists() -> None:
    _assert_file_nonempty(OVERLAY_OUTPUT_PATH)


def test_overlay_contains_red() -> None:
    red_mask = _load_red_mask(OVERLAY_OUTPUT_PATH)
    red_voxels = int(np.count_nonzero(red_mask))
    print(json.dumps({"red_voxels": red_voxels}, indent=2, sort_keys=True), flush=True)
    assert red_voxels > 0, "No red prostate overlay voxels were detected"


def test_overlay_matches_reference() -> None:
    red_mask = _load_red_mask(OVERLAY_OUTPUT_PATH)
    reference_mask = _load_label_mask(REFERENCE_LABEL_PATH)
    result = _compare_slice_masks(red_mask, reference_mask)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    assert result["failed_slice_count"] == 0, (
        f"{result['failed_slice_count']} slices exceeded "
        f"{SLICE_AREA_RELATIVE_TOLERANCE:.1%} area-overlap error"
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
            "<test_overlay_exists|test_overlay_contains_red|test_overlay_matches_reference>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
