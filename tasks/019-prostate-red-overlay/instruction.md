Given `/app/input/case_7f3a9c_mri.nii.gz`, create a new NIfTI volume with the prostate overlaid in red.

Required output:
- `/app/artifacts/prostate_red_overlay.nii.gz`

Requirements:
- Use the installed 3D Slicer tooling. Headless use is fine.
- Inspect the MRI data and estimate the prostate region; do not use placeholder geometry.
- The output must be a real `.nii.gz` NIfTI file with red pixels/voxels marking the prostate region.
- Keep `/app/input/*` unchanged.
- Keep final outputs under `/app/artifacts`.
