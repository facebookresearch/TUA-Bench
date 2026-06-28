# local/004-place-heater-for-sensors

Benchmark task for evaluating whether an agent can solve a small inverse
thermal-design problem on the same simple OpenFOAM plate setup.

The agent receives `/app/input/heater_design_request.json`, which describes:

- the plate dimensions and boundary conditions
- a 10 mm x 10 mm fixed-400 K heater patch on the top face
- four top-surface sensor locations
- four target sensor temperatures
- the allowed heater-origin search domain

The agent must estimate the heater origin/center, predicted sensor
temperatures, and per-sensor errors, and write:

- `/app/artifacts/heater_placement_result.json`
- `/app/artifacts/heater_placement_top_view.svg`

The verifier checks required files, validates the JSON shape, and compares the
reported heater center to a hidden reference center with 1.0 mm absolute
distance tolerance.
The SVG is only checked for existence and nonzero size for manual inspection.
