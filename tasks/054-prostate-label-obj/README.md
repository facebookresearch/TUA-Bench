# local/medical-3d-slicer-prostate-label-obj-reconstruction

This task asks the agent to reconstruct a prostate surface mesh from a provided
prostate label map using 3D Slicer.

The agent must:

1. Read `/app/input/case_7f3a9c_label.nii.gz`.
2. Use the nonzero label voxels as the prostate segmentation.
3. Export `/app/artifacts/prostate_model.obj`.

The verifier checks that the OBJ exists and that its geometry matches the hidden
reference prostate mesh within 1% tolerance.
