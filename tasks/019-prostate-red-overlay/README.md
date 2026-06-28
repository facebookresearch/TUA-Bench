# local/medical-3d-slicer-prostate-red-overlay

This task asks the agent to inspect a prostate MRI volume and create a NIfTI
volume where the prostate region is highlighted in red.

The agent must:

1. Read `/app/input/case_7f3a9c_mri.nii.gz`.
2. Identify the prostate region.
3. Write `/app/artifacts/prostate_red_overlay.nii.gz`.

The verifier reads the submitted NIfTI, extracts red voxels, and compares each
slice against the hidden prostate label map with 5% area-error tolerance. The
slice comparison tries rotations by 90, 180, and 270 degrees, plus horizontal
and vertical flips, before scoring each slice.
