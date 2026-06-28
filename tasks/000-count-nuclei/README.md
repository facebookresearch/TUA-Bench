Count the nuclei/cells in two microscopy images without being given the original CellProfiler pipeline.

Visible inputs:
- `input/images/1-162hrh2ax2.tif`
- `input/images/1-162hrhoe2.tif`

Expected agent output:
- `/app/artifacts/nuclei_count.txt`

This variant intentionally removes the `.cppipe` pipeline and step-by-step execution hints. CellProfiler is preinstalled in the environment. The verifier derives the correct count from the frozen benchmark `Nuclei.csv` ground truth and checks only the submitted count.
