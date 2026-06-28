Given `/app/input/case_7f3a9c_label.nii.gz` and `/app/input/task_plan.json`, reconstruct a 3D prostate surface model with the installed 3D Slicer and write outputs under `/app/artifacts`.

Required outputs:
1. Read `/app/input/task_plan.json`.
2. Read the provided label map. The nonzero voxels are the prostate segmentation.
3. Generate `/app/artifacts/prostate_model.obj` as a real non-empty 3D prostate mesh derived from that label map.

Requirements:
- Use the real 3D Slicer installation in this environment. Headless use is fine.
- Keep `/app/input/*` completely unchanged.
- Keep all final outputs under `/app/artifacts`.
- Do not export the whole image volume, background, or placeholder geometry.
- The OBJ must be a valid mesh export of the prostate label.
