Run a saved CellProfiler pipeline on two microscopy images and reproduce the nuclei measurement table.

Visible inputs:
- `input/config/ExampleSpeckles.cppipe`
- `input/images/1-162hrh2ax2.tif`
- `input/images/1-162hrhoe2.tif`

Expected agent output:
- `/app/artifacts/Nuclei.csv`

This variant intentionally removes the helper task plan and step-by-step execution hints. CellProfiler is preinstalled in the environment, and the verifier compares the generated `Nuclei.csv` against the hidden GT table from the frozen benchmark case.
