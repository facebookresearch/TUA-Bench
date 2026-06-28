Reconstruct a 3D prostate surface mesh from a medical image volume using 3D Slicer.

Visible inputs:
- `input/case_7f3a9c_mri.nii.gz`
- `input/task_plan.json`

Expected agent outputs:
- `/app/artifacts/prostate_model.obj`
- `/app/artifacts/prostate_render.png`

The verifier keeps a hidden reference OBJ and a hidden label backup. It only checks that the PNG exists; mesh quality is scored from OBJ similarity against the hidden reference model.
