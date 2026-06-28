#!/bin/bash
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


set -euo pipefail

cat > /tmp/solve_task.py <<'PY'
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import openstudio

PLAN_PATH = Path("/app/input/task_plan.json")
ENERGYPLUS_BIN = Path("/opt/openstudio/EnergyPlus/energyplus")
SUMMARY_KEY_BY_METER = {
    "Electricity:Facility": "annual_electricity_kwh",
    "NaturalGas:Facility": "annual_natural_gas_kwh",
    "FuelOilNo2:Facility": "annual_fuel_oil_kwh",
}


def load_plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def parse_idf_value(idf_path: Path, pattern: str, label: str) -> str:
    text = idf_path.read_text(encoding="utf-8")
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        raise SystemExit(f"Could not find {label} in {idf_path}")
    return match.group(1).strip()


def meter_block(plan: dict) -> str:
    frequency = str(plan["meter_output_frequency"])
    blocks = []
    for meter_name in plan["required_meter_names"]:
        blocks.append(
            "\n".join(
                [
                    "Output:Meter,",
                    f"  {meter_name},",
                    f"  {frequency};",
                ]
            )
        )
    return "\n\n".join(blocks) + "\n"


def translate_and_meter(plan: dict, output_path: Path) -> None:
    osm_path = Path("/app/input") / str(plan["source_osm"])
    translator = openstudio.osversion.VersionTranslator()
    model_opt = translator.loadModel(openstudio.path(str(osm_path)))
    if not model_opt.is_initialized():
        raise SystemExit(f"Could not load OSM model: {osm_path}")

    workspace = openstudio.energyplus.ForwardTranslator().translateModel(model_opt.get())

    with tempfile.TemporaryDirectory() as tmp_dir:
        base_idf_path = Path(tmp_dir) / "translated.idf"
        if not workspace.save(openstudio.path(str(base_idf_path)), True):
            raise SystemExit(f"Could not save translated IDF: {base_idf_path}")
        final_text = base_idf_path.read_text(encoding="utf-8").rstrip() + "\n\n" + meter_block(plan)
        output_path.write_text(final_text, encoding="utf-8")


def run_energyplus(idf_path: Path, weather_path: Path, output_dir: Path) -> None:
    if not ENERGYPLUS_BIN.exists():
        raise SystemExit(f"Missing EnergyPlus binary: {ENERGYPLUS_BIN}")
    output_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            str(ENERGYPLUS_BIN),
            "-w",
            str(weather_path),
            "-d",
            str(output_dir),
            str(idf_path),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        err_path = output_dir / "eplusout.err"
        err_text = err_path.read_text(encoding="utf-8", errors="ignore") if err_path.exists() else ""
        raise SystemExit(
            "EnergyPlus simulation failed.\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
            f"eplusout.err:\n{err_text[-4000:]}"
        )


def load_meter_totals(mtr_path: Path, meter_names: list[str]) -> tuple[dict[str, float], dict[str, int]]:
    meter_lookup = set(meter_names)
    index_to_meter: dict[str, str] = {}
    totals_joules = {name: 0.0 for name in meter_names}
    sample_counts = {name: 0 for name in meter_names}
    in_data_dictionary = True

    for raw_line in mtr_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if in_data_dictionary:
            if line == "End of Data Dictionary":
                in_data_dictionary = False
                continue
            match = re.match(r"^(\d+),\d+,(.+?) \[[^\]]+\]", line)
            if match is None:
                continue
            record_id, meter_name = match.groups()
            if meter_name in meter_lookup:
                index_to_meter[record_id] = meter_name
            continue

        record_id, _, value_text = line.partition(",")
        meter_name = index_to_meter.get(record_id)
        if meter_name is None:
            continue
        totals_joules[meter_name] += float(value_text)
        sample_counts[meter_name] += 1

    missing = [name for name in meter_names if sample_counts[name] == 0]
    if missing:
        raise SystemExit(f"Missing required meters in {mtr_path}: {missing}")

    totals_kwh = {name: totals_joules[name] / 3.6e6 for name in meter_names}
    return totals_kwh, sample_counts


def main() -> None:
    plan = load_plan()
    artifact_dir = Path(str(plan["artifact_dir"]))
    generated_idf_path = Path(str(plan["translated_idf_output"]))
    simulation_output_dir = Path(str(plan["simulation_output_dir"]))
    summary_path = Path(str(plan["summary_output"]))
    weather_path = Path("/app/input") / str(plan["source_weather"])

    shutil.rmtree(artifact_dir, ignore_errors=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    translate_and_meter(plan, generated_idf_path)
    run_energyplus(generated_idf_path, weather_path, simulation_output_dir)

    mtr_path = simulation_output_dir / "eplusout.mtr"
    totals_kwh, sample_counts = load_meter_totals(mtr_path, list(plan["required_meter_names"]))
    expected_row_count = int(plan["source_row_count"])
    for meter_name in plan["required_meter_names"]:
        actual_count = sample_counts[meter_name]
        if actual_count != expected_row_count:
            raise SystemExit(
                f"Unexpected sample count for {meter_name}: expected={expected_row_count} got={actual_count}"
            )

    translated_version = parse_idf_value(
        generated_idf_path,
        r"\bVersion,\s*\n\s*([^;]+);",
        "Version",
    )
    building_name = parse_idf_value(
        generated_idf_path,
        r"\bBuilding,\s*\n\s*([^,\n]+),",
        "Building name",
    )

    summary_values: dict[str, str] = {
        "bldg_id": str(int(plan["source_bldg_id"])),
        "translated_version": translated_version,
        "building_name": building_name,
        "weather_file": Path(str(plan["source_weather"])).name,
        "row_count": str(expected_row_count),
    }
    for meter_name, summary_key in SUMMARY_KEY_BY_METER.items():
        summary_values[summary_key] = f"{totals_kwh[meter_name]:.6f}"
    summary_values["annual_site_energy_kwh"] = f"{sum(totals_kwh.values()):.6f}"

    lines = [f"{key}={summary_values[key]}" for key in plan["summary_key_order"]]
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
PY

openstudio execute_python_script /tmp/solve_task.py
