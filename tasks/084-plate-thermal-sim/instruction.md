Given `/app/input/simple_plate_regions.stl` and `/app/input/simple_plate_params.json`, create and run an OpenFOAM simulation for the simple heated plate.

Use the installed OpenFOAM tooling. Keep `/app/input/*` unchanged.

Simulation requirements:
- Use the geometry and named surface regions from `simple_plate_regions.stl`.
- Follow the physical parameters, boundary conditions, time controls, and numerics in `simple_plate_params.json`.
- Run the transient `laplacianFoam` case to `120 s`.
- Preserve the named patches: `heatSource`, `topRest`, `bottomSink`, `xmin`, `xmax`, `ymin`, and `ymax`.

Required outputs:
1. Create `/app/artifacts/simple_plate_case` containing the runnable OpenFOAM case and the generated final field at `/app/artifacts/simple_plate_case/120/T`.
2. Keep the solver log at `/app/artifacts/simple_plate_case/log.laplacianFoam`.
3. Write `/app/artifacts/simple_plate_result_120s.json` as a nested JSON object, not with flattened dotted keys. Use this exact shape:

```json
{
  "case_name": "simple_plate",
  "final_time_s": "<final simulation time in seconds>",
  "mesh": {
    "cell_count": "<integer>",
    "point_count": "<integer>",
    "face_count": "<integer>",
    "internal_face_count": "<integer>",
    "patch_face_counts": {
      "heatSource": "<integer>",
      "topRest": "<integer>",
      "bottomSink": "<integer>",
      "xmin": "<integer>",
      "xmax": "<integer>",
      "ymin": "<integer>",
      "ymax": "<integer>"
    }
  },
  "metrics": {
    "internal_min_temperature_K": "<number>",
    "internal_max_temperature_K": "<number>",
    "top_surface_min_temperature_K": "<number>",
    "top_surface_max_temperature_K": "<number>",
    "reported_min_temperature_K": "<number>",
    "reported_max_temperature_K": "<number>"
  }
}
```

Use numeric JSON values in your final file, not strings. The placeholders above only illustrate the required nesting and key names; compute all values from your actual run.
4. Write `/app/artifacts/simple_plate_top_view.svg`, a top-view SVG visualization of the plate, heater patch, and simulated temperature result. This is for manual inspection in the artifact folder.

The verifier compares these values with hidden ground truth using 1% relative tolerance.
