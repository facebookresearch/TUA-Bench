# local/medical-3d-slicer-prostate-volume-estimation

This task asks the agent to estimate prostate volume from a prostate MRI volume
using the installed 3D Slicer tooling.

The agent must:

1. Read `/app/input/case_7f3a9c_mri.nii.gz`.
2. Identify and segment the prostate.
3. Write a single numeric volume estimate in cubic centimeters to
   `/app/artifacts/prostate_volume.txt`.

The verifier computes the hidden reference volume from the GT prostate OBJ and
accepts estimates within 5% relative error.
