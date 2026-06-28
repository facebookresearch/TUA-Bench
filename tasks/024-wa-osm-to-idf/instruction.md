Given `/app/input/building.osm`, `/app/input/building_timeseries.parquet`, and `/app/input/task_plan.json`, use the installed OpenStudio CLI (`openstudio`) to produce a translated IDF and a deterministic summary.

Here is the workflow I'd like you to follow:

1. Read `/app/input/task_plan.json`.
2. Use the real OpenStudio CLI to translate `/app/input/building.osm` into `/app/generated_building.idf`.
3. Parse the generated IDF to extract:
   - the translated EnergyPlus version from the `Version` object
   - the building name from the `Building` object
4. Write `/app/translation_summary.txt` with exactly the following keys in exactly this order:
   - `bldg_id=<int>`
   - `translated_version=<string>`
   - `building_name=<string>`
   - `row_count=<int>`
   - `annual_site_energy_kwh=<float>`
   - `peak_hourly_site_energy_kwh=<float>`

Use the values recorded in `/app/input/task_plan.json` for `bldg_id`, `row_count`, `annual_site_energy_kwh`, and `peak_hourly_site_energy_kwh`. Those values were precomputed from `/app/input/building_timeseries.parquet`, so you do not need to install a parquet reader.

Please keep the following constraints in mind:

- Use the real `openstudio` CLI. Avoid fake, hand-written, or placeholder IDF output.
- Keep all files in `/app/input/*` unchanged.
- Ensure both `/app/generated_building.idf` and `/app/translation_summary.txt` exist and are non-empty.
