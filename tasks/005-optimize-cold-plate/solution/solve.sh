#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd /app

rm -rf /app/artifacts
mkdir -p /app/artifacts

cp -R "$SCRIPT_DIR/template_case" /app/artifacts/improved_case

python3 - <<'PY'
import json
from pathlib import Path

design_path = Path("/app/artifacts/improved_case/design.json")
design = json.loads(design_path.read_text(encoding="utf-8"))
design["description"] = "Denser ten-channel near-chip field that increases wetted area while keeping pressure drop below the verifier limit."
design["fluid_boxes_mm"] = [
    {
        "name": "inlet_duct",
        "min": [0.0, 35.0, 6.0],
        "max": [14.0, 45.0, 9.0]
    },
    {
        "name": "inlet_manifold",
        "min": [14.0, 16.0, 1.0],
        "max": [22.0, 62.0, 8.5]
    },
    {
        "name": "ch1",
        "min": [20.0, 16.0, 0.5],
        "max": [60.0, 18.5, 3.0]
    },
    {
        "name": "ch2",
        "min": [20.0, 20.5, 0.5],
        "max": [60.0, 23.0, 3.0]
    },
    {
        "name": "ch3",
        "min": [20.0, 25.0, 0.5],
        "max": [60.0, 27.5, 3.0]
    },
    {
        "name": "ch4",
        "min": [20.0, 29.5, 0.5],
        "max": [60.0, 32.0, 3.0]
    },
    {
        "name": "ch5",
        "min": [20.0, 34.0, 0.5],
        "max": [60.0, 36.5, 3.0]
    },
    {
        "name": "ch6",
        "min": [20.0, 38.5, 0.5],
        "max": [60.0, 41.0, 3.0]
    },
    {
        "name": "ch7",
        "min": [20.0, 43.0, 0.5],
        "max": [60.0, 45.5, 3.0]
    },
    {
        "name": "ch8",
        "min": [20.0, 47.5, 0.5],
        "max": [60.0, 50.0, 3.0]
    },
    {
        "name": "ch9",
        "min": [20.0, 52.0, 0.5],
        "max": [60.0, 54.5, 3.0]
    },
    {
        "name": "ch10",
        "min": [20.0, 56.5, 0.5],
        "max": [60.0, 59.0, 3.0]
    },
    {
        "name": "outlet_manifold",
        "min": [58.0, 16.0, 1.0],
        "max": [66.0, 62.0, 8.5]
    },
    {
        "name": "outlet_duct",
        "min": [66.0, 35.0, 6.0],
        "max": [80.0, 45.0, 9.0]
    }
]
design_path.write_text(json.dumps(design, indent=2) + "\n", encoding="utf-8")
PY

bash /app/artifacts/improved_case/run_case.sh

cp /app/artifacts/improved_case/metrics.json /app/artifacts/metrics.json
mkdir -p /app/artifacts/renders
cp /app/artifacts/improved_case/renders/*.svg /app/artifacts/renders/

python3 - <<'PY'
import json
from pathlib import Path

metrics = json.loads(Path("/app/artifacts/metrics.json").read_text(encoding="utf-8"))
baseline = {
    "chip_average_temperature_k": 337.306622,
    "solid_max_temperature_k": 354.33536,
    "pressure_drop_pa": 9.66107384,
    "outlet_mass_flow_kg_s": 0.00149997575,
}

comparison = "\n".join(
    [
        "# Baseline vs Improved",
        "",
        f"- Baseline chip average temperature: {baseline['chip_average_temperature_k']:.3f} K",
        f"- Improved chip average temperature: {metrics['chip_average_temperature_k']:.3f} K",
        f"- Baseline solid max temperature: {baseline['solid_max_temperature_k']:.3f} K",
        f"- Improved solid max temperature: {metrics['solid_max_temperature_k']:.3f} K",
        f"- Baseline pressure drop: {baseline['pressure_drop_pa']:.3f} Pa",
        f"- Improved pressure drop: {metrics['pressure_drop_pa']:.3f} Pa",
        f"- Baseline outlet mass flow: {baseline['outlet_mass_flow_kg_s']:.6f} kg/s",
        f"- Improved outlet mass flow: {metrics['outlet_mass_flow_kg_s']:.6f} kg/s",
        "",
        "The improved design increases the number of near-chip flow channels, which raises wetted perimeter over the heat source while keeping the same inlet, outlet, top-face sink, and overall envelope."
    ]
)
Path("/app/artifacts/baseline_vs_improved.md").write_text(comparison + "\n", encoding="utf-8")
PY

test -s /app/artifacts/improved_case/metrics.json
test -s /app/artifacts/metrics.json
test -s /app/artifacts/baseline_vs_improved.md
test -s /app/artifacts/renders/geometry_view.svg
test -s /app/artifacts/renders/temperature_view.svg
test -s /app/artifacts/renders/top_surface_temperature.svg
