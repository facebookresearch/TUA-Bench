#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parent
SYSTEM_DIR = CASE_DIR / "system"
DESIGN_RESOLUTION_MM = 0.5
PLATE_X_MM = 80.0
PLATE_Y_MM = 80.0
PLATE_Z_MM = 10.0
PORT_Y_MIN_MM = 35.0
PORT_Y_MAX_MM = 45.0
PORT_Z_MIN_MM = 6.0
PORT_Z_MAX_MM = 9.0
CHIP_X_MIN_MM = 30.0
CHIP_X_MAX_MM = 50.0
CHIP_Y_MIN_MM = 30.0
CHIP_Y_MAX_MM = 50.0
CHIP_SOURCE_Z_MAX_MM = 0.5
X_PLANES_MM = [0.0, 20.0, 60.0, 80.0]
Y_PLANES_MM = [0.0, 20.0, 60.0, 80.0]
Z_PLANES_MM = [0.0, 10.0]
X_CELLS = [20, 80, 20]
Y_CELLS = [20, 80, 20]
Z_CELLS = [20]


def _ensure_half_mm(value: float, label: str) -> None:
    if abs(round(value / DESIGN_RESOLUTION_MM) * DESIGN_RESOLUTION_MM - value) > 1e-9:
        raise ValueError(f"{label}={value} must be a multiple of {DESIGN_RESOLUTION_MM} mm")


def _mm_to_index(value_mm: float) -> int:
    return int(round(value_mm / DESIGN_RESOLUTION_MM))


def _iter_box_voxels(box: dict) -> range:
    ix0 = _mm_to_index(float(box["min"][0]))
    ix1 = _mm_to_index(float(box["max"][0]))
    iy0 = _mm_to_index(float(box["min"][1]))
    iy1 = _mm_to_index(float(box["max"][1]))
    iz0 = _mm_to_index(float(box["min"][2]))
    iz1 = _mm_to_index(float(box["max"][2]))
    for i in range(ix0, ix1):
        for j in range(iy0, iy1):
            for k in range(iz0, iz1):
                yield (i, j, k)


def _expected_port_voxels(x_index: int) -> set[tuple[int, int, int]]:
    jy0 = _mm_to_index(PORT_Y_MIN_MM)
    jy1 = _mm_to_index(PORT_Y_MAX_MM)
    kz0 = _mm_to_index(PORT_Z_MIN_MM)
    kz1 = _mm_to_index(PORT_Z_MAX_MM)
    return {
        (x_index, j, k)
        for j in range(jy0, jy1)
        for k in range(kz0, kz1)
    }


def _load_design(path: Path) -> dict:
    design = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(design, dict):
        raise ValueError("design.json must contain a JSON object")
    boxes = design.get("fluid_boxes_mm")
    if not isinstance(boxes, list) or not boxes:
        raise ValueError("design.json must contain a non-empty fluid_boxes_mm list")

    normalized: list[dict] = []
    for index, box in enumerate(boxes):
        if not isinstance(box, dict):
            raise ValueError(f"fluid_boxes_mm[{index}] must be an object")
        name = box.get("name") or f"fluid_box_{index}"
        mins = box.get("min")
        maxs = box.get("max")
        if not (isinstance(mins, list) and isinstance(maxs, list) and len(mins) == 3 and len(maxs) == 3):
            raise ValueError(f"fluid_boxes_mm[{index}] must define min/max 3-vectors")
        mins = [float(value) for value in mins]
        maxs = [float(value) for value in maxs]
        for axis, value in zip(("xmin", "ymin", "zmin"), mins):
            _ensure_half_mm(value, f"{name}.{axis}")
        for axis, value in zip(("xmax", "ymax", "zmax"), maxs):
            _ensure_half_mm(value, f"{name}.{axis}")
        if not (0.0 <= mins[0] < maxs[0] <= PLATE_X_MM):
            raise ValueError(f"{name} x-bounds must stay inside 0..{PLATE_X_MM} mm")
        if not (0.0 <= mins[1] < maxs[1] <= PLATE_Y_MM):
            raise ValueError(f"{name} y-bounds must stay inside 0..{PLATE_Y_MM} mm")
        if not (0.0 <= mins[2] < maxs[2] <= PLATE_Z_MM):
            raise ValueError(f"{name} z-bounds must stay inside 0..{PLATE_Z_MM} mm")
        normalized.append({"name": str(name), "min": mins, "max": maxs})

    design["fluid_boxes_mm"] = normalized
    return design


def _validate_design(design: dict) -> None:
    nx = _mm_to_index(PLATE_X_MM)
    ny = _mm_to_index(PLATE_Y_MM)
    nz = _mm_to_index(PLATE_Z_MM)
    fluid_voxels: set[tuple[int, int, int]] = set()
    for box in design["fluid_boxes_mm"]:
        fluid_voxels.update(_iter_box_voxels(box))

    if not fluid_voxels:
        raise ValueError("The fluid geometry may not be empty")

    if any(j in (0, ny - 1) for _, j, _ in fluid_voxels):
        raise ValueError("Fluid geometry may not touch the y-min or y-max outer walls")
    if any(k in (0, nz - 1) for _, _, k in fluid_voxels):
        raise ValueError("Fluid geometry may not touch the z-min or z-max outer walls")

    inlet_expected = _expected_port_voxels(0)
    outlet_expected = _expected_port_voxels(nx - 1)
    inlet_actual = {voxel for voxel in fluid_voxels if voxel[0] == 0}
    outlet_actual = {voxel for voxel in fluid_voxels if voxel[0] == nx - 1}

    if inlet_actual != inlet_expected:
        raise ValueError("The x-min inlet opening must stay fixed at y=35..45 mm and z=6..9 mm")
    if outlet_actual != outlet_expected:
        raise ValueError("The x-max outlet opening must stay fixed at y=35..45 mm and z=6..9 mm")

    chip_ix0 = _mm_to_index(CHIP_X_MIN_MM)
    chip_ix1 = _mm_to_index(CHIP_X_MAX_MM)
    chip_iy0 = _mm_to_index(CHIP_Y_MIN_MM)
    chip_iy1 = _mm_to_index(CHIP_Y_MAX_MM)
    chip_iz1 = _mm_to_index(CHIP_SOURCE_Z_MAX_MM)
    if any(
        chip_ix0 <= i < chip_ix1 and chip_iy0 <= j < chip_iy1 and k < chip_iz1
        for i, j, k in fluid_voxels
    ):
        raise ValueError("Fluid geometry may not overlap the fixed chip source zone at the bottom face")

    queue = deque(sorted(inlet_expected))
    visited: set[tuple[int, int, int]] = set()
    outlet_reached = False
    while queue:
        voxel = queue.popleft()
        if voxel in visited or voxel not in fluid_voxels:
            continue
        visited.add(voxel)
        if voxel in outlet_expected:
            outlet_reached = True
        i, j, k = voxel
        for di, dj, dk in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            neighbour = (i + di, j + dj, k + dk)
            if neighbour in fluid_voxels and neighbour not in visited:
                queue.append(neighbour)

    if not outlet_reached:
        raise ValueError("The fluid geometry must provide a connected inlet-to-outlet path")
    if len(visited) != len(fluid_voxels):
        raise ValueError("The fluid geometry must form a single connected component")


def _vid(ix: int, iy: int, iz: int) -> int:
    return iz * (len(X_PLANES_MM) * len(Y_PLANES_MM)) + iy * len(X_PLANES_MM) + ix


def _write_block_mesh_dict(path: Path) -> None:
    lines = [
        "/*--------------------------------*- C++ -*----------------------------------*\\",
        "  =========                 |",
        "  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox",
        "   \\\\    /   O peration     | Website:  https://openfoam.org",
        "    \\\\  /    A nd           | Version:  11",
        "     \\\\/     M anipulation  |",
        "\\*---------------------------------------------------------------------------*/",
        "FoamFile",
        "{",
        "    format      ascii;",
        "    class       dictionary;",
        "    object      blockMeshDict;",
        "}",
        "",
        "convertToMeters 0.001;",
        "",
        "vertices",
        "(",
    ]
    for z in Z_PLANES_MM:
        for y in Y_PLANES_MM:
            for x in X_PLANES_MM:
                lines.append(f"    ({x:.6f} {y:.6f} {z:.6f})")
    lines.extend([");", "", "blocks", "("])
    for iy, ny in enumerate(Y_CELLS):
        for ix, nx in enumerate(X_CELLS):
            v000 = _vid(ix, iy, 0)
            v100 = _vid(ix + 1, iy, 0)
            v110 = _vid(ix + 1, iy + 1, 0)
            v010 = _vid(ix, iy + 1, 0)
            v001 = _vid(ix, iy, 1)
            v101 = _vid(ix + 1, iy, 1)
            v111 = _vid(ix + 1, iy + 1, 1)
            v011 = _vid(ix, iy + 1, 1)
            lines.append(
                f"    hex ({v000} {v100} {v110} {v010} {v001} {v101} {v111} {v011}) "
                f"({nx} {ny} {Z_CELLS[0]}) simpleGrading (1 1 1)"
            )
    lines.extend([");", "", "boundary", "("])

    def add_patch(name: str, patch_type: str, faces: list[tuple[int, int, int, int]]) -> None:
        lines.append(f"    {name}")
        lines.append("    {")
        lines.append(f"        type {patch_type};")
        lines.append("        faces")
        lines.append("        (")
        for face in faces:
            lines.append(f"            ({face[0]} {face[1]} {face[2]} {face[3]})")
        lines.append("        );")
        lines.append("    }")

    x_min_faces: list[tuple[int, int, int, int]] = []
    x_max_faces: list[tuple[int, int, int, int]] = []
    y_min_faces: list[tuple[int, int, int, int]] = []
    y_max_faces: list[tuple[int, int, int, int]] = []
    z_min_faces: list[tuple[int, int, int, int]] = []
    z_max_faces: list[tuple[int, int, int, int]] = []

    for iy in range(len(Y_CELLS)):
        x_min_faces.append((_vid(0, iy, 0), _vid(0, iy + 1, 0), _vid(0, iy + 1, 1), _vid(0, iy, 1)))
        x_max_faces.append((_vid(len(X_CELLS), iy, 0), _vid(len(X_CELLS), iy, 1), _vid(len(X_CELLS), iy + 1, 1), _vid(len(X_CELLS), iy + 1, 0)))
    for ix in range(len(X_CELLS)):
        y_min_faces.append((_vid(ix, 0, 0), _vid(ix, 0, 1), _vid(ix + 1, 0, 1), _vid(ix + 1, 0, 0)))
        y_max_faces.append((_vid(ix, len(Y_CELLS), 0), _vid(ix + 1, len(Y_CELLS), 0), _vid(ix + 1, len(Y_CELLS), 1), _vid(ix, len(Y_CELLS), 1)))
        z_min_faces.append((_vid(ix, 0, 0), _vid(ix + 1, 0, 0), _vid(ix + 1, 1, 0), _vid(ix, 1, 0)))
        z_max_faces.append((_vid(ix, 0, 1), _vid(ix, 1, 1), _vid(ix + 1, 1, 1), _vid(ix + 1, 0, 1)))
    for ix in range(len(X_CELLS)):
        for iy in range(1, len(Y_CELLS)):
            z_min_faces.append((_vid(ix, iy, 0), _vid(ix + 1, iy, 0), _vid(ix + 1, iy + 1, 0), _vid(ix, iy + 1, 0)))
            z_max_faces.append((_vid(ix, iy, 1), _vid(ix, iy + 1, 1), _vid(ix + 1, iy + 1, 1), _vid(ix + 1, iy, 1)))

    add_patch("xMin", "patch", x_min_faces)
    add_patch("xMax", "patch", x_max_faces)
    add_patch("yMin", "wall", y_min_faces)
    add_patch("yMax", "wall", y_max_faces)
    add_patch("zMin", "wall", z_min_faces)
    add_patch("zMax", "wall", z_max_faces)

    lines.extend(
        [
            ");",
            "",
            "mergePatchPairs",
            "(",
            ");",
            "",
            "// ************************************************************************* //",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _format_box_m(coords_mm: list[float]) -> str:
    return f"({coords_mm[0] / 1000.0:.6f} {coords_mm[1] / 1000.0:.6f} {coords_mm[2] / 1000.0:.6f})"


def _write_topo_set_dict(path: Path, design: dict) -> None:
    lines = [
        "/*--------------------------------*- C++ -*----------------------------------*\\",
        "  =========                 |",
        "  \\\\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox",
        "   \\\\    /   O peration     | Website:  https://openfoam.org",
        "    \\\\  /    A nd           | Version:  11",
        "     \\\\/     M anipulation  |",
        "\\*---------------------------------------------------------------------------*/",
        "FoamFile",
        "{",
        "    format      ascii;",
        "    class       dictionary;",
        "    object      topoSetDict;",
        "}",
        "",
        "actions",
        "(",
    ]
    for index, box in enumerate(design["fluid_boxes_mm"]):
        action = "new" if index == 0 else "add"
        lines.extend(
            [
                "    {",
                "        name    fluidCells;",
                "        type    cellSet;",
                f"        action  {action};",
                "        source  boxToCell;",
                f"        box     {_format_box_m(box['min'])} {_format_box_m(box['max'])};",
                "    }",
            ]
        )
    lines.extend(
        [
            "    {",
            "        name    fluid;",
            "        type    cellZoneSet;",
            "        action  new;",
            "        source  setToCellZone;",
            "        set     fluidCells;",
            "    }",
            ");",
            "",
            "// ************************************************************************* //",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate blockMesh and topoSet dictionaries for the cold-plate case.")
    parser.add_argument("--design", type=Path, default=Path("design.json"), help="Path to the design JSON file.")
    args = parser.parse_args()

    design = _load_design((CASE_DIR / args.design).resolve() if not args.design.is_absolute() else args.design)
    _validate_design(design)
    _write_block_mesh_dict(SYSTEM_DIR / "blockMeshDict")
    _write_topo_set_dict(SYSTEM_DIR / "topoSetDict", design)


if __name__ == "__main__":
    main()
