# local/industrials-openfoam-simple-plate-thermal-simulation

Benchmark task for evaluating whether an agent can reproduce a simple
OpenFOAM solid-plate heat-transfer simulation from provided geometry and
parameter metadata.

## Task summary

- Agent-visible inputs:
  - `/app/input/simple_plate_regions.stl`
  - `/app/input/simple_plate_params.json`
- Agent output case: `/app/artifacts/simple_plate_case`
- Required machine-readable result:
  `/app/artifacts/simple_plate_result_120s.json`
- Required eyeball-check render:
  `/app/artifacts/simple_plate_top_view.svg`

The expected simulation is a transient `laplacianFoam` run to `120 s` on an
80 mm x 50 mm x 5 mm solid plate. The top corner heater patch is fixed at
400 K, the rest of the top surface has weak mixed cooling to 300 K, and the
other boundaries are insulated.

## Verifier

The verifier checks:

1. Required case, final field, log, and JSON outputs exist.
   It also checks that the top-view SVG exists and is nonempty, but does not
   judge the SVG visual correctness.
2. Reported mesh and temperature metrics match the hidden ground-truth JSON
   within 1% relative tolerance.
3. The reported metrics are consistent with the submitted final OpenFOAM field
   at `120/T`.

Reward follows the same partial-credit pattern as the cold-plate OpenFOAM task:
`0`, `0.33`, `0.66`, or `1`.
