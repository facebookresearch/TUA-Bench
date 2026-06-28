Use the provided microscopy images to locate the nuclei/cells.

CellProfiler is available in the environment. Inspect the images and use an appropriate software workflow to estimate the center location of each nucleus/cell from the nuclear stain image.

Inputs:
- `/app/input/images/1-162hrh2ax2.tif`
- `/app/input/images/1-162hrhoe2.tif`

Required final output:
- `/app/artifacts/nuclei_locations.csv`

Write a CSV file with exactly these columns:

```csv
x,y
```

Each data row should contain one nucleus/cell center in pixel coordinates. The output must be generated from the provided input images.
