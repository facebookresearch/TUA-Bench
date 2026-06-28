Given `/app/input/task_plan.json`, improve the thermal performance of the liquid-cooled aluminum cold plate by changing only the internal coolant-side geometry inside the plate.

Use the installed OpenFOAM and ParaView tooling from this environment. Keep `/app/input/*` unchanged. No starter OpenFOAM case is provided. Create your own case and automation under `/app/artifacts/improved_case`.

Fixed design conditions:
- External plate envelope: `80 mm x 80 mm x 10 mm`
- Plate material: aluminum
- Coolant: water
- Heat source footprint: `20 mm x 20 mm`, centered on the bottom face
- Chip power: `300 W`
- Coolant inlet temperature: `300 K`
- Coolant inlet velocity: `0.05 m/s`
- Flow direction: inlet on the `x-min` face, outlet on the `x-max` face
- Dry top face temperature used by the verifier reference physics: fixed at `300 K`
- Simulation style: simple, defensible steady-state CHT smoke test

What must stay fixed:
- The external plate size and overall bounding box
- The chip footprint, chip location, and chip power
- The coolant type, inlet temperature, inlet velocity, inlet face, outlet face, and overall flow direction
- The non-coolant-side boundary conditions described in `task_plan.json` and enforced by the verifier

What is free to change:
- The internal fluid-path geometry inside the plate
- The internal solid-fluid interface geometry inside the channel region
- The internal passive solid/fluid distribution inside the plate, as long as it remains physically plausible

Design constraints:
- Stay fully inside the `80 x 80 x 10 mm` plate envelope
- Maintain a continuous connected fluid path from inlet to outlet
- Use passive geometry only
- Minimum solid thickness: `0.5 mm`
- Minimum fluid gap / opening: `0.5 mm`
- Do not create a numerically fragile or obviously blocked flow path

Success criteria:
- Chip average temperature `<= 335 K`
- Pressure drop `<= 12 Pa`
- Outlet mass flow `>= 0.0012 kg/s`

Required outputs:
1. Create `/app/artifacts/improved_case` and place your OpenFOAM case, geometry-generation workflow, and automation there.
2. Regenerate the simulation outputs by running your artifact case.
3. Write `/app/artifacts/metrics.json` with these keys:
   - `chip_average_temperature_k`
   - `solid_max_temperature_k`
   - `pressure_drop_pa`
   - `outlet_mass_flow_kg_s`
   - `thermal_resistance_k_per_w`
4. Write `/app/artifacts/baseline_vs_improved.md` with a short baseline-vs-improved comparison.
5. Write these review renders under `/app/artifacts/renders`:
   - `geometry_view.svg`
   - `temperature_view.svg`
   - `top_surface_temperature.svg`
