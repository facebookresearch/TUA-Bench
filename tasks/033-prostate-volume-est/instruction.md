Given `/app/input/case_7f3a9c_mri.nii.gz`, estimate the volume of the prostate.

Required output:
- `/app/artifacts/prostate_volume.txt`

Output format:
- The file must contain just one number.
- The number must be the prostate volume in cubic centimeters, equivalent to milliliters.

Requirements:
- Use the installed 3D Slicer tooling. Headless use is fine.
- Inspect the MRI data and estimate the prostate region; do not use placeholder values.
- Keep `/app/input/*` unchanged.
- Keep final outputs under `/app/artifacts`.
