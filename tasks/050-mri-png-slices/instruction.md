Given `/app/input/case_7f3a9c_mri.nii.gz` and `/app/input/task_plan.json`, export every axial T2 layer of the MRI volume as a PNG image.

Required output directory:
- `/app/artifacts/png_slices`

Requirements:
- Use the installed 3D Slicer tooling. Headless use is fine.
- The input NIfTI contains two channels/volumes; export the first one as the T2 series.
- Preserve the axial display orientation used by Slicer. If you use array operations directly, this is equivalent to rotating each `volume[:, :, z]` slice 90 degrees counterclockwise before saving it.
- Use a consistent grayscale window/normalization across the exported slices so the anatomy remains visible.
- Export exactly 15 PNG files, one for each axial slice.
- Use these filenames exactly: `prostate_00_t2_slice_00.png`, `prostate_00_t2_slice_01.png`, ..., `prostate_00_t2_slice_14.png`.
- Each PNG should preserve the slice appearance and orientation from the input MRI data.
- Keep `/app/input/*` unchanged.
- Keep final outputs under `/app/artifacts`.
