# local/005-optimize-cold-plate

Benchmark task for evaluating whether an agent can improve a simple
liquid-cooled aluminum cold plate by modifying only the internal coolant-side
geometry and rerunning a real OpenFOAM multi-region thermal case.

## Task summary

- Agent-visible input metadata: `/app/input/task_plan.json`
- Agent output case: `/app/artifacts/improved_case`
- Required machine-readable metrics: `/app/artifacts/metrics.json`
- Required comparison note: `/app/artifacts/baseline_vs_improved.md`
- Required review renders:
  - `/app/artifacts/renders/geometry_view.svg`
  - `/app/artifacts/renders/temperature_view.svg`
  - `/app/artifacts/renders/top_surface_temperature.svg`

## System design

### Environment

`environment/Dockerfile` uses `docker.io/openfoam/openfoam11-paraview510` as the
runtime base image so the task has:

- OpenFOAM 11
- ParaView / `pvpython`
- Python 3

### Agent contract

- Harbor runs the agent inside the task container as user `agent`
- The working directory is `/app`
- `/app/input` exposes only `task_plan.json`
- The agent must create its own case and automation in
  `/app/artifacts/improved_case`, run it there, and write the requested outputs
  under `/app/artifacts`

### Case design

The verifier/oracle template uses a structured Cartesian mesh over the
full plate envelope and then defines the internal coolant region with cell-zone
geometry before splitting the mesh into `fluid` and `solid` regions. The thermal
source is fixed under the chip footprint in the solid region. That hidden
template also fixes the dry top face at `300 K` and leaves the other dry outer
faces adiabatic to keep the smoke test in a practical benchmark range.

The supplied baseline case is a simple passive eight-channel layout. The oracle
uses a denser ten-channel variant that satisfies the target chip temperature,
pressure drop, and outlet mass-flow constraints.

### Verifier

`tests/test.sh` runs three checks through `python3 /tests/test_outputs.py <test_name>`:

1. `test_outputs_exist`
2. `test_design_constraints`
3. `test_rerun_meets_targets`

Behavior:

- If required outputs are missing, the verifier immediately returns `0`
- The verifier always copies `/app/artifacts` into `/logs/artifacts/`
- The verifier reruns a hidden clean template using the artifact `design.json`,
  so fixed physics and boundary conditions cannot be altered by editing solver
  inputs alone

## Reward logic

- `0`: required outputs missing or empty
- `0.33`: existence check passed, both deeper checks failed
- `0.66`: existence check passed, one deeper check passed
- `1`: all three checks passed
