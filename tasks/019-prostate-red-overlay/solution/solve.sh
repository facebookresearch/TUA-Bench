#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

python3 <<'PY'
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

plan = json.loads(Path("/app/input/task_plan.json").read_text(encoding="utf-8"))
input_volume_path = Path(plan["input_volume_path"])
output_path = Path(plan["overlay_output_path"])
reference_label_path = Path("/tests/reference/prostate_00_label_backup.nii.gz")

output_path.parent.mkdir(parents=True, exist_ok=True)

mri_img = nib.load(str(input_volume_path))
mri_data = np.asanyarray(mri_img.dataobj)
if mri_data.ndim > 3:
    mri_data = np.squeeze(mri_data)
if mri_data.ndim > 3:
    mri_data = mri_data[..., 0]
assert mri_data.ndim == 3, f"Expected a 3D MRI volume, got {mri_data.shape}"

label_data = np.squeeze(np.asanyarray(nib.load(str(reference_label_path)).dataobj))
assert label_data.shape == mri_data.shape, (
    f"Reference label shape {label_data.shape} does not match MRI shape {mri_data.shape}"
)
mask = label_data > 0

finite = np.asarray(mri_data[np.isfinite(mri_data)], dtype=np.float32)
if finite.size:
    lo, hi = np.percentile(finite, [1.0, 99.0])
else:
    lo, hi = 0.0, 1.0
if hi <= lo:
    hi = lo + 1.0

gray = np.clip((np.asarray(mri_data, dtype=np.float32) - lo) / (hi - lo), 0.0, 1.0)
gray_u8 = (gray * 180.0).astype(np.uint8)
rgb = np.stack([gray_u8, gray_u8, gray_u8], axis=-1)
rgb[mask] = np.array([255, 0, 0], dtype=np.uint8)

out_img = nib.Nifti1Image(rgb, mri_img.affine)
out_img.header.set_data_dtype(np.uint8)
nib.save(out_img, str(output_path))
PY

test -s /app/artifacts/prostate_red_overlay.nii.gz
