#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

SVG_WIDTH = 960
SVG_HEIGHT = 720


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _project(point: tuple[float, float, float]) -> tuple[float, float]:
    x, y, z = point
    px = 120.0 + x * 7.0 - y * 4.0
    py = 600.0 - z * 32.0 - y * 2.2 - x * 1.2
    return px, py


def _color_gradient(t: float, cool: tuple[int, int, int], hot: tuple[int, int, int]) -> str:
    t = max(0.0, min(1.0, t))
    channels = [round(cool[i] * (1.0 - t) + hot[i] * t) for i in range(3)]
    return "#%02x%02x%02x" % tuple(channels)


def _box_faces(box: dict) -> list[list[tuple[float, float, float]]]:
    x0, y0, z0 = box["min"]
    x1, y1, z1 = box["max"]
    return [
        [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
        [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    ]


def _polygon(points: list[tuple[float, float]], fill: str, stroke: str, opacity: float = 1.0) -> str:
    joined = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polygon points="{joined}" fill="{fill}" fill-opacity="{opacity:.3f}" stroke="{stroke}" stroke-width="1.5"/>'


def _render_geometry(design: dict, output_path: Path) -> None:
    outer_box = {"min": [0.0, 0.0, 0.0], "max": [80.0, 80.0, 10.0]}
    elements = []
    for face in _box_faces(outer_box):
        elements.append(_polygon([_project(tuple(point)) for point in face], "#d9dee6", "#708090", 0.30))

    sorted_boxes = sorted(design["fluid_boxes_mm"], key=lambda box: sum(box["min"]) + sum(box["max"]))
    for box in sorted_boxes:
        for face in _box_faces(box):
            elements.append(_polygon([_project(tuple(point)) for point in face], "#4b9fe1", "#1d5f91", 0.70))

    labels = [
        '<text x="36" y="42" font-size="28" font-family="DejaVu Sans Mono" fill="#1b2733">Cold Plate Geometry</text>',
        '<text x="36" y="76" font-size="18" font-family="DejaVu Sans Mono" fill="#34495e">External envelope: 80 x 80 x 10 mm</text>'
    ]

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{SVG_HEIGHT}" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">',
        '<rect width="100%" height="100%" fill="#f7f8fb"/>',
        *labels,
        *elements,
        "</svg>",
        ""
    ]
    output_path.write_text("\n".join(svg), encoding="utf-8")


def _render_temperature_view(design: dict, metrics: dict, output_path: Path) -> None:
    chip = metrics["chip_average_temperature_k"]
    solid_max = metrics["solid_max_temperature_k"]
    outer_box = {"min": [0.0, 0.0, 0.0], "max": [80.0, 80.0, 10.0]}

    elements = []
    for face in _box_faces(outer_box):
        elements.append(_polygon([_project(tuple(point)) for point in face], "#f4f0ea", "#8b8b8b", 0.18))

    denom = max(1e-6, solid_max - 300.0)
    for box in sorted(design["fluid_boxes_mm"], key=lambda item: sum(item["min"]) + sum(item["max"])):
        local_depth = 10.0 - box["min"][2]
        color = _color_gradient((local_depth / 10.0) * 0.35, (37, 113, 192), (255, 201, 96))
        for face in _box_faces(box):
            elements.append(_polygon([_project(tuple(point)) for point in face], color, "#204f75", 0.82))

    chip_box = {"min": [30.0, 30.0, 0.0], "max": [50.0, 50.0, 0.5]}
    chip_color = _color_gradient((chip - 300.0) / denom, (255, 212, 96), (196, 57, 57))
    for face in _box_faces(chip_box):
        elements.append(_polygon([_project(tuple(point)) for point in face], chip_color, "#7f1d1d", 0.95))

    text = [
        '<text x="36" y="42" font-size="28" font-family="DejaVu Sans Mono" fill="#1b2733">Temperature View</text>',
        f'<text x="36" y="76" font-size="18" font-family="DejaVu Sans Mono" fill="#34495e">Chip average: {chip:.3f} K</text>',
        f'<text x="36" y="104" font-size="18" font-family="DejaVu Sans Mono" fill="#34495e">Solid max: {solid_max:.3f} K</text>'
    ]

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{SVG_HEIGHT}" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">',
        '<rect width="100%" height="100%" fill="#fffaf4"/>',
        *text,
        *elements,
        "</svg>",
        ""
    ]
    output_path.write_text("\n".join(svg), encoding="utf-8")


def _fluid_depth_at(design: dict, x_mm: float, y_mm: float) -> float | None:
    depth = None
    for box in design["fluid_boxes_mm"]:
        if box["min"][0] <= x_mm <= box["max"][0] and box["min"][1] <= y_mm <= box["max"][1]:
            local = 10.0 - box["min"][2]
            depth = local if depth is None else max(depth, local)
    return depth


def _render_top_surface(design: dict, metrics: dict, output_path: Path) -> None:
    chip = metrics["chip_average_temperature_k"]
    solid_max = metrics["solid_max_temperature_k"]
    min_temp = 300.0
    max_temp = solid_max

    grid_step = 2.0
    rects = []
    for ix in range(int(80 / grid_step)):
        for iy in range(int(80 / grid_step)):
            x = ix * grid_step
            y = iy * grid_step
            cx = x + grid_step / 2.0
            cy = y + grid_step / 2.0
            r = math.hypot(cx - 40.0, cy - 40.0)
            fluid_depth = _fluid_depth_at(design, cx, cy)
            cooling_factor = 0.65 if fluid_depth is None else max(0.20, 1.0 - fluid_depth / 14.0)
            temp = min_temp + (chip - min_temp) * math.exp(-(r / 18.0) ** 2) * cooling_factor
            color = _color_gradient((temp - min_temp) / max(1e-6, max_temp - min_temp), (55, 127, 184), (215, 48, 39))
            px = 80 + x * 7
            py = 80 + (80.0 - y - grid_step) * 7
            rects.append(f'<rect x="{px:.2f}" y="{py:.2f}" width="{grid_step * 7:.2f}" height="{grid_step * 7:.2f}" fill="{color}" stroke="none"/>')

    overlays = []
    for box in design["fluid_boxes_mm"]:
        x0, y0, _ = box["min"]
        x1, y1, _ = box["max"]
        px = 80 + x0 * 7
        py = 80 + (80.0 - y1) * 7
        overlays.append(
            f'<rect x="{px:.2f}" y="{py:.2f}" width="{(x1 - x0) * 7:.2f}" height="{(y1 - y0) * 7:.2f}" '
            'fill="none" stroke="#102a43" stroke-width="2"/>'
        )

    chip_overlay = '<rect x="290.00" y="290.00" width="140.00" height="140.00" fill="none" stroke="#7f1d1d" stroke-width="3"/>'

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{SVG_HEIGHT}" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">',
        '<rect width="100%" height="100%" fill="#fbfbfd"/>',
        '<text x="36" y="42" font-size="28" font-family="DejaVu Sans Mono" fill="#1b2733">Top-Surface Temperature</text>',
        '<text x="36" y="76" font-size="18" font-family="DejaVu Sans Mono" fill="#34495e">Synthetic SVG review heatmap driven by the rerun metrics and internal geometry layout.</text>',
        *rects,
        *overlays,
        chip_overlay,
        "</svg>",
        ""
    ]
    output_path.write_text("\n".join(svg), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render SVG review images for the cold-plate case.")
    parser.add_argument("--case", type=Path, required=True, help="Case directory.")
    parser.add_argument("--metrics", type=Path, required=True, help="Metrics JSON path.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Render output directory.")
    args = parser.parse_args()

    design = _load_json(args.case / "design.json")
    metrics = _load_json(args.metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    _render_geometry(design, args.output_dir / "geometry_view.svg")
    _render_temperature_view(design, metrics, args.output_dir / "temperature_view.svg")
    _render_top_surface(design, metrics, args.output_dir / "top_surface_temperature.svg")


if __name__ == "__main__":
    main()
