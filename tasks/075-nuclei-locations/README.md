Locate the nuclei/cells in two microscopy images using detailed CellProfiler-style segmentation guidance.

Visible inputs:
- `input/images/1-162hrh2ax2.tif`
- `input/images/1-162hrhoe2.tif`

Expected agent output:
- `/app/artifacts/nuclei_locations.csv`

The relevant nucleus-detection settings are summarized in `instruction.md`. CellProfiler is preinstalled in the environment. The verifier derives the correct nucleus center locations from the frozen benchmark `Nuclei.csv` ground truth and checks submitted `x,y` coordinates with 5% coordinate-wise tolerance.
