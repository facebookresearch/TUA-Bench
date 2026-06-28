Use the provided microscopy images to locate the nuclei/cells.

CellProfiler is available in the environment. The nucleus-detection settings are summarized below. Follow these settings as closely as practical to detect the nucleus centers from the nuclear stain image.

Inputs:
- `/app/input/images/1-162hrh2ax2.tif`
- `/app/input/images/1-162hrhoe2.tif`

Relevant pipeline behavior:
- Treat both inputs as grayscale images.
- Use filename rules to identify the channels:
  - the file whose name contains `hoe` is the nuclear stain image; use this as the nucleus detection input.
  - the file whose name contains `h2ax` is the green foci image; it is not needed for nucleus center detection.
- Do not group image sets.
- Detect primary objects named `Nuclei` from the nuclear stain image with these settings:
  - typical object diameter: minimum `120` pixels, maximum `300` pixels
  - discard objects outside that diameter range
  - discard objects touching the image border
  - threshold strategy: global
  - thresholding method: Otsu
  - threshold correction factor: `1.0`
  - threshold smoothing scale: `1.3488`
  - threshold bounds: lower `0.0`, upper `1.0`
  - two-class thresholding; assign the middle-intensity class to foreground if applicable
  - distinguish clumped objects by shape
  - draw dividing lines between clumped objects by shape
  - smoothing filter size for declumping: `10`
  - suppress local maxima closer than `7.0` pixels
  - fill holes after thresholding and declumping
  - automatically calculate the smoothing filter and local-maxima distance for declumping
  - maximum object count: `500`
- Report each detected nucleus by its object center, equivalent to CellProfiler's `Location_Center_X` and `Location_Center_Y` measurements.

Required final output:
- `/app/artifacts/nuclei_locations.csv`

Write a CSV file with exactly these columns:

```csv
x,y
```

Each data row should contain one nucleus/cell center in pixel coordinates. The output must be generated from the provided input images.
