#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set +u
source /opt/openfoam11/etc/bashrc >/dev/null 2>&1 || true
set -u

rm -rf /app/artifacts
mkdir -p /app/artifacts
cp -R "$SCRIPT_DIR/reference/simple_plate_case" /app/artifacts/simple_plate_case

cd /app/artifacts/simple_plate_case
rm -rf constant/polyMesh [1-9]* 0.[0-9]* VTK log.*

blockMesh > log.blockMesh 2>&1
laplacianFoam > log.laplacianFoam 2>&1
foamToVTK -latestTime > log.foamToVTK 2>&1

python3 "$SCRIPT_DIR/reference/scripts/extract_simple_plate_metrics.py" \
  /app/artifacts/simple_plate_case \
  "$SCRIPT_DIR/reference/simple_plate_ground_truth_120s.json" \
  /app/artifacts/simple_plate_result_120s.json

python3 <<'PY'
from __future__ import annotations

import json
from pathlib import Path

params = json.loads(Path("/app/input/simple_plate_params.json").read_text(encoding="utf-8"))
metrics = json.loads(Path("/app/artifacts/simple_plate_result_120s.json").read_text(encoding="utf-8"))

plate_x, plate_y, _ = params["geometry"]["plate_dimensions_m"]
heater = params["geometry"]["heater_patch"]
heater_x, heater_y, _ = heater["origin_m"]
heater_w, heater_h = heater["size_m"]
reported = metrics["metrics"]

width = 920
height = 660
margin_x = 90
margin_y = 120
plot_w = 720
plot_h = plot_w * plate_y / plate_x

def sx(x: float) -> float:
    return margin_x + x * plot_w / plate_x

def sy(y: float) -> float:
    return margin_y + plot_h - y * plot_h / plate_y

heater_svg_x = sx(heater_x)
heater_svg_y = sy(heater_y + heater_h)
heater_svg_w = sx(heater_x + heater_w) - sx(heater_x)
heater_svg_h = sy(heater_y) - sy(heater_y + heater_h)

parts = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    '<rect width="100%" height="100%" fill="#f8fafc"/>',
    '<text x="48" y="58" font-family="Helvetica, Arial, sans-serif" font-size="30" fill="#111827">Simple Plate Top View</text>',
    '<text x="48" y="92" font-family="Helvetica, Arial, sans-serif" font-size="17" fill="#4b5563">laplacianFoam result at 120 s; SVG intended for artifact eyeball check</text>',
    f'<rect x="{margin_x:.2f}" y="{margin_y:.2f}" width="{plot_w:.2f}" height="{plot_h:.2f}" fill="#e5edf6" stroke="#334155" stroke-width="2"/>',
    f'<rect x="{heater_svg_x:.2f}" y="{heater_svg_y:.2f}" width="{heater_svg_w:.2f}" height="{heater_svg_h:.2f}" fill="#dc2626" fill-opacity="0.78" stroke="#7f1d1d" stroke-width="2"/>',
    f'<text x="{heater_svg_x + heater_svg_w + 10:.2f}" y="{heater_svg_y + 24:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#7f1d1d">400 K heatSource</text>',
    f'<text x="{margin_x:.2f}" y="{margin_y + plot_h + 42:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#374151">plate: {plate_x * 1000:.0f} mm x {plate_y * 1000:.0f} mm</text>',
    f'<text x="{margin_x:.2f}" y="{margin_y + plot_h + 70:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#374151">reported temperature range: {reported["reported_min_temperature_K"]:.2f} K to {reported["reported_max_temperature_K"]:.2f} K</text>',
    f'<text x="{margin_x + plot_w:.2f}" y="{margin_y + plot_h + 42:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#374151" text-anchor="end">top surface min/max: {reported["top_surface_min_temperature_K"]:.2f} K / {reported["top_surface_max_temperature_K"]:.2f} K</text>',
    '</svg>',
]

Path("/app/artifacts/simple_plate_top_view.svg").write_text("\n".join(parts) + "\n", encoding="utf-8")
PY

test -s /app/artifacts/simple_plate_case/120/T
test -s /app/artifacts/simple_plate_case/log.laplacianFoam
test -s /app/artifacts/simple_plate_result_120s.json
test -s /app/artifacts/simple_plate_top_view.svg
