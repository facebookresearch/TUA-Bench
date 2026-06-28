Given `/app/input/heater_design_request.json`, find where to place the fixed-temperature heater so the four sensors match their target temperatures.

Use the installed OpenFOAM tooling or any defensible numerical search workflow. Keep `/app/input/*` unchanged.

Problem setup:
- Plate dimensions: `0.08 m x 0.05 m x 0.005 m`
- Heater patch: `0.01 m x 0.01 m`, fixed at `400 K`, on the top face
- Bottom and side faces are insulated
- Non-heater top surface weakly cools to `300 K` with `valueFraction = 0.005`
- Thermal diffusivity: `8.4e-5 m^2/s`
- Final time: `120 s`
- The four sensor positions and target temperatures are listed in `heater_design_request.json`
- Match each target sensor temperature within `0.5 K`

Required outputs:
1. Write `/app/artifacts/heater_placement_result.json` as a nested JSON object with this shape:

```json
{
  "heater_origin_m": ["<x>", "<y>", "<z>"],
  "heater_center_m": ["<x>", "<y>", "<z>"],
  "predicted_sensor_temperatures": [
    {
      "name": "S1",
      "point_m": ["<x>", "<y>", "<z>"],
      "temperature_K": "<number>",
      "target_temperature_K": "<number>",
      "error_K": "<predicted minus target>"
    }
  ],
  "max_abs_error_K": "<number>",
  "method_summary": "<short description of how you searched or simulated>"
}
```

Use numeric JSON values in your final file, not strings. Include all four sensors, `S1` through `S4`.

2. Write `/app/artifacts/heater_placement_top_view.svg`, a top-view SVG showing the plate outline, the selected heater patch, and the four sensor locations. This is for manual inspection in the artifact folder.
