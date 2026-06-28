Given `/app/input/building.osm`, `/app/input/weather.epw`, and `/app/input/task_plan.json`, use the installed OpenStudio CLI (`openstudio`) and the bundled EnergyPlus executable to produce a translated IDF, run the simulation, and summarize the annual energy totals.

Here is the workflow I'd like you to follow:

1. Read `/app/input/task_plan.json`.
2. Use the real OpenStudio CLI to translate `/app/input/building.osm` into `/app/artifacts/generated_building.idf`.
3. Append the required `Output:Meter` objects in the exact order listed in `/app/input/task_plan.json`, using the reporting frequency listed there.
4. Run the real EnergyPlus simulator with `/app/input/weather.epw` and write the run directory to `/app/artifacts/energyplus_run`.
5. Parse `/app/artifacts/energyplus_run/eplusout.mtr` to compute annual totals in kWh for:
   - electricity
   - natural gas
   - fuel oil
   - total site energy, defined as the sum of those three annual totals
6. Write `/app/artifacts/simulation_summary.txt` with exactly the following keys in exactly this order:
   - `bldg_id=<int>`
   - `translated_version=<string>`
   - `building_name=<string>`
   - `weather_file=<string>`
   - `row_count=<int>`
   - `annual_electricity_kwh=<float>`
   - `annual_natural_gas_kwh=<float>`
   - `annual_fuel_oil_kwh=<float>`
   - `annual_site_energy_kwh=<float>`

Use the values recorded in `/app/input/task_plan.json` for `bldg_id`, `weather_file`, and `row_count`. The verifier holds the ground-truth annual totals separately, so the inputs exposed under `/app/input` do not contain the reference answer.

Please keep the following constraints in mind:

- Use the real `openstudio` CLI and the real EnergyPlus executable. Avoid fake, hand-written, or placeholder simulation outputs.
- Keep all files in `/app/input/*` unchanged.
- Ensure `/app/artifacts/generated_building.idf`, `/app/artifacts/simulation_summary.txt`, `/app/artifacts/energyplus_run/eplusout.mtr`, `/app/artifacts/energyplus_run/eplusout.sql`, and `/app/artifacts/energyplus_run/eplustbl.htm` all exist and are non-empty.
- Store the final outputs under `/app/artifacts` so they are preserved as task artifacts.
