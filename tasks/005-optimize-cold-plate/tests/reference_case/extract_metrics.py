#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import argparse
import json
from pathlib import Path

INLET_TEMPERATURE_K = 300.0
CHIP_POWER_W = 300.0


def _numeric_sort_key(path: Path) -> float:
    try:
        return float(path.parent.name)
    except ValueError:
        return float("-inf")


def _read_last_value(path: Path) -> tuple[float, float]:
    last_line = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        last_line = line
    if last_line is None:
        raise RuntimeError(f"No numeric rows found in {path}")
    parts = last_line.split()
    if len(parts) < 2:
        raise RuntimeError(f"Unexpected data row in {path}: {last_line}")
    return float(parts[0]), float(parts[-1])


def _find_postprocessing_file(case_dir: Path, relative_pattern: str) -> Path:
    matches = sorted((case_dir / "postProcessing").glob(relative_pattern), key=_numeric_sort_key)
    if not matches:
        raise RuntimeError(f"Could not find a postProcessing file matching {relative_pattern!r}")
    return matches[-1]


def _load_metrics(case_dir: Path) -> dict[str, float]:
    chip_time, chip_avg = _read_last_value(
        _find_postprocessing_file(case_dir, "solid/chipAverageTemperature/*/surfaceFieldValue.dat")
    )
    solid_time, solid_max = _read_last_value(
        _find_postprocessing_file(case_dir, "solid/solidMaxTemperature/*/volFieldValue.dat")
    )
    inlet_time, inlet_pressure = _read_last_value(
        _find_postprocessing_file(case_dir, "fluid/inletPressureAverage/*/surfaceFieldValue.dat")
    )
    outlet_time, outlet_pressure = _read_last_value(
        _find_postprocessing_file(case_dir, "fluid/outletPressureAverage/*/surfaceFieldValue.dat")
    )
    flow_time, outlet_mass_flow = _read_last_value(
        _find_postprocessing_file(case_dir, "fluid/outletMassFlow/*/surfaceFieldValue.dat")
    )

    last_time = min(chip_time, solid_time, inlet_time, outlet_time, flow_time)
    pressure_drop = inlet_pressure - outlet_pressure
    thermal_resistance = (chip_avg - INLET_TEMPERATURE_K) / CHIP_POWER_W
    return {
        "chip_average_temperature_k": chip_avg,
        "solid_max_temperature_k": solid_max,
        "pressure_drop_pa": pressure_drop,
        "outlet_mass_flow_kg_s": outlet_mass_flow,
        "thermal_resistance_k_per_w": thermal_resistance,
        "last_time_s": last_time,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract cold-plate metrics from OpenFOAM postProcessing outputs.")
    parser.add_argument("--case", type=Path, required=True, help="Case directory.")
    parser.add_argument("--output", type=Path, required=True, help="JSON output path.")
    args = parser.parse_args()

    metrics = _load_metrics(args.case)
    args.output.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
