# local/medical-3d-slicer-prostate-mri-png-slices

This task asks the agent to inspect a prostate MRI NIfTI volume and export each
axial layer as a PNG image.

The agent must:

1. Read `/app/input/case_7f3a9c_mri.nii.gz`.
2. Use the first 3D channel/volume in the 4D MRI file.
3. Export the 15 axial T2 slices to `/app/artifacts/png_slices`.
4. Preserve the axial display orientation used by Slicer. In array terms, this
   is equivalent to rotating each `volume[:, :, z]` slice 90 degrees
   counterclockwise before writing it.
5. Name the files `prostate_00_t2_slice_00.png` through
   `prostate_00_t2_slice_14.png`.

The verifier compares the submitted PNG set against hidden reference PNGs. It
requires the exact image count, filenames, and dimensions, then checks each
slice using luminance SSIM and normalized RMSE. The reward is binary: `1` only
when every slice passes; otherwise `0`.
