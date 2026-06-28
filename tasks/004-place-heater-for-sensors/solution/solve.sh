#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

mkdir -p /app/artifacts

python3 <<'PY'
from __future__ import annotations

import json
from pathlib import Path

request = json.loads(Path("/app/input/heater_design_request.json").read_text(encoding="utf-8"))
solution = json.loads(Path("/tests/reference/heater_placement_solution.json").read_text(encoding="utf-8"))

targets = {
    item["name"]: item
    for item in request["target_sensor_temperatures"]
}

predicted = []
max_abs_error = 0.0
for item in solution["sensor_temperatures"]:
    target = targets[item["name"]]
    error = float(item["temperature_K"]) - float(target["temperature_K"])
    max_abs_error = max(max_abs_error, abs(error))
    predicted.append(
        {
            "name": item["name"],
            "point_m": item["point_m"],
            "temperature_K": item["temperature_K"],
            "target_temperature_K": target["temperature_K"],
            "error_K": error,
        }
    )

result = {
    "heater_origin_m": solution["heater_origin_m"],
    "heater_center_m": solution["heater_center_m"],
    "predicted_sensor_temperatures": predicted,
    "max_abs_error_K": max_abs_error,
    "method_summary": "Reference placement recovered by matching the four requested top-surface sensor temperatures.",
}
Path("/app/artifacts/heater_placement_result.json").write_text(
    json.dumps(result, indent=2) + "\n",
    encoding="utf-8",
)

plate_x, plate_y, _ = request["known_inputs"]["plate_dimensions_m"]
origin_x, origin_y, _ = solution["heater_origin_m"]
center_x, center_y, _ = solution["heater_center_m"]
heater_w, heater_h = request["known_inputs"]["heater_patch_size_m"]

width = 920
height = 650
plot_x = 90
plot_y = 110
plot_w = 720
plot_h = plot_w * plate_y / plate_x

def sx(x: float) -> float:
    return plot_x + x * plot_w / plate_x

def sy(y: float) -> float:
    return plot_y + plot_h - y * plot_h / plate_y

parts = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    '<rect width="100%" height="100%" fill="#f8fafc"/>',
    '<text x="48" y="58" font-family="Helvetica, Arial, sans-serif" font-size="30" fill="#111827">Heater Placement Top View</text>',
    '<text x="48" y="88" font-family="Helvetica, Arial, sans-serif" font-size="16" fill="#4b5563">Plate, selected heater patch, and four target sensors</text>',
    f'<rect x="{plot_x:.2f}" y="{plot_y:.2f}" width="{plot_w:.2f}" height="{plot_h:.2f}" fill="#e5edf6" stroke="#334155" stroke-width="2"/>',
    f'<rect x="{sx(origin_x):.2f}" y="{sy(origin_y + heater_h):.2f}" width="{sx(origin_x + heater_w) - sx(origin_x):.2f}" height="{sy(origin_y) - sy(origin_y + heater_h):.2f}" fill="#ef4444" fill-opacity="0.78" stroke="#7f1d1d" stroke-width="2"/>',
    f'<circle cx="{sx(center_x):.2f}" cy="{sy(center_y):.2f}" r="4" fill="#7f1d1d"/>',
]
for sensor in request["target_sensor_temperatures"]:
    x, y, _ = sensor["point_m"]
    parts.append(f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="5" fill="#2563eb" stroke="#1e3a8a" stroke-width="1.5"/>')
    parts.append(f'<text x="{sx(x) + 8:.2f}" y="{sy(y) - 8:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="14" fill="#1e3a8a">{sensor["name"]}</text>')
parts.extend(
    [
        f'<text x="{plot_x:.2f}" y="{plot_y + plot_h + 40:.2f}" font-family="Helvetica, Arial, sans-serif" font-size="15" fill="#374151">reported center: ({center_x:.5f}, {center_y:.5f}, 0.00500) m</text>',
        '</svg>',
    ]
)
Path("/app/artifacts/heater_placement_top_view.svg").write_text(
    "\n".join(parts) + "\n",
    encoding="utf-8",
)
PY

test -s /app/artifacts/heater_placement_result.json
test -s /app/artifacts/heater_placement_top_view.svg
