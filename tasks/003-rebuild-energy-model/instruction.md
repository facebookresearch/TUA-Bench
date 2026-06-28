Given `/app/input/floorplan.png`, `/app/input/weather.epw`, and `/app/input/task_plan.json`, reconstruct a 3D OpenStudio building model from the floor plan, run an annual EnergyPlus simulation, and write the results under `/app/artifacts`.

Requirements:

1. Save the reconstructed building model to `/app/artifacts/reconstructed_building.osm`.
2. Save the translated EnergyPlus model to `/app/artifacts/generated_building.idf`.
3. Write the simulation outputs to `/app/artifacts/energyplus_run`.
4. Save review renders under `/app/artifacts/render_views` and also write `/app/artifacts/building_render.png`.
5. Write `/app/artifacts/simulation_summary.txt` with exactly these keys in exactly this order:
   - `bldg_id=<int>`
   - `translated_version=<string>`
   - `building_name=<string>`
   - `weather_file=<string>`
   - `row_count=<int>`
   - `annual_electricity_kwh=<float>`
   - `annual_natural_gas_kwh=<float>`
   - `annual_fuel_oil_kwh=<float>`
   - `annual_site_energy_kwh=<float>`

Use the `bldg_id`, `weather_file`, `row_count`, meter names, and meter output frequency from `/app/input/task_plan.json`.

Constraints:

- Keep all files in `/app/input/*` unchanged.
- Store all outputs under `/app/artifacts`.
- The verifier checks annual energy totals against hidden ground truth with `1%` relative tolerance.
