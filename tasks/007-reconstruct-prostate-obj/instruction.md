Given `/app/input/case_7f3a9c_mri.nii.gz` and `/app/input/task_plan.json`, reconstruct a 3D prostate surface model with the installed 3D Slicer and write outputs under `/app/artifacts`.

Required outputs:
1. Read `/app/input/task_plan.json`.
2. Read the input volume data, identify the prostate anatomy, and segment out only the prostate region.
3. Generate `/app/artifacts/prostate_model.obj` as a real non-empty 3D prostate mesh derived from that prostate-only segmentation.
4. Generate `/app/artifacts/prostate_render.png` as a rendered PNG view of the generated prostate model.

Requirements:
- Use the real 3D Slicer installation in this environment. Headless use is fine.
- Keep `/app/input/*` completely unchanged.
- Keep all final outputs under `/app/artifacts`.
- The input is imaging data, so you must inspect it and create the segmentation yourself instead of assuming the whole volume is already the prostate.
- Segment only the prostate. Do not export the whole scan volume, background, or unrelated anatomy.
- The OBJ must be a valid mesh export of the prostate, not placeholder geometry or an unrelated shape.
