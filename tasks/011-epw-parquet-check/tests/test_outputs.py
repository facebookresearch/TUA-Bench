# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

import openstudio

PLAN_PATH = Path("/app/input/task_plan.json")
OSM_PATH = Path("/app/input/building.osm")
WEATHER_PATH = Path("/app/input/weather.epw")
REFERENCE_METRICS_PATH = Path("/tests/reference_metrics.json")
ARTIFACT_DIR = Path("/app/artifacts")
GENERATED_IDF_PATH = ARTIFACT_DIR / "generated_building.idf"
SUMMARY_PATH = ARTIFACT_DIR / "simulation_summary.txt"
SIMULATION_OUTPUT_DIR = ARTIFACT_DIR / "energyplus_run"
ENERGYPLUS_BIN = Path("/opt/openstudio/EnergyPlus/energyplus")

SUMMARY_KEY_BY_METER = {
    "Electricity:Facility": "annual_electricity_kwh",
    "NaturalGas:Facility": "annual_natural_gas_kwh",
    "FuelOilNo2:Facility": "annual_fuel_oil_kwh",
}
FLOAT_ABS_TOL = 1e-3


def _load_plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _load_reference_metrics() -> dict:
    return json.loads(REFERENCE_METRICS_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_idf_value(idf_path: Path, pattern: str, label: str) -> str:
    text = idf_path.read_text(encoding="utf-8")
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        raise AssertionError(f"Could not find {label} in {idf_path}")
    return match.group(1).strip()


def _meter_block(plan: dict) -> str:
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


def _translate_osm_to_idf(osm_path: Path, output_path: Path) -> None:
    translator = openstudio.osversion.VersionTranslator()
    model_opt = translator.loadModel(openstudio.path(str(osm_path)))
    if not model_opt.is_initialized():
        raise AssertionError(f"Could not load OSM model: {osm_path}")

    workspace = openstudio.energyplus.ForwardTranslator().translateModel(model_opt.get())
    if not workspace.save(openstudio.path(str(output_path)), True):
        raise AssertionError(f"Could not save translated IDF: {output_path}")


def _build_reference_idf(output_path: Path) -> None:
    plan = _load_plan()
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_idf = Path(tmp_dir) / "translated.idf"
        _translate_osm_to_idf(OSM_PATH, base_idf)
        output_path.write_text(
            base_idf.read_text(encoding="utf-8").rstrip() + "\n\n" + _meter_block(plan),
            encoding="utf-8",
        )


def _parse_summary(path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        assert "=" in line, f"Invalid summary line (missing '='): {line}"
        key, value = line.split("=", 1)
        entries.append((key.strip(), value.strip()))
    return entries


def _load_meter_totals(mtr_path: Path, meter_names: list[str]) -> tuple[dict[str, float], dict[str, int]]:
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
    assert not missing, f"Missing required meters in {mtr_path}: {missing}"

    totals_kwh = {name: totals_joules[name] / 3.6e6 for name in meter_names}
    return totals_kwh, sample_counts


def _run_energyplus(idf_path: Path, output_dir: Path) -> None:
    assert ENERGYPLUS_BIN.exists(), f"Missing EnergyPlus binary: {ENERGYPLUS_BIN}"
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            str(ENERGYPLUS_BIN),
            "-w",
            str(WEATHER_PATH),
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
        raise AssertionError(
            "EnergyPlus reference rerun failed.\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
            f"eplusout.err:\n{err_text[-4000:]}"
        )


def _assert_successful_run(output_dir: Path) -> None:
    end_path = output_dir / "eplusout.end"
    assert end_path.exists(), f"Missing EnergyPlus completion marker: {end_path}"
    end_text = end_path.read_text(encoding="utf-8", errors="ignore")
    assert "Completed Successfully" in end_text, f"EnergyPlus did not complete successfully: {end_path}"


def _assert_close(actual: float, expected: float, label: str) -> None:
    assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=FLOAT_ABS_TOL), (
        f"{label} mismatch: expected={expected} got={actual}"
    )


def _assert_within_relative_tolerance(actual: float, expected: float, tolerance: float, label: str) -> None:
    relative_error = abs(actual - expected) / abs(expected)
    assert relative_error <= tolerance, (
        f"{label} outside tolerance: expected={expected} got={actual} "
        f"relative_error={relative_error:.6%} tolerance={tolerance:.6%}"
    )


def test_output_files_exist() -> None:
    plan = _load_plan()
    required = [GENERATED_IDF_PATH, SUMMARY_PATH]
    required.extend(SIMULATION_OUTPUT_DIR / name for name in plan["required_simulation_artifacts"])
    for path in required:
        assert path.exists(), f"Missing required output: {path}"
        assert path.stat().st_size > 0, f"Required output is empty: {path}"
    _assert_successful_run(SIMULATION_OUTPUT_DIR)


def test_generated_idf_matches_reference() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        reference_idf = Path(tmp_dir) / "reference.idf"
        _build_reference_idf(reference_idf)
        expected_hash = _sha256(reference_idf)
        actual_hash = _sha256(GENERATED_IDF_PATH)
        assert actual_hash == expected_hash, (
            "Generated IDF does not match deterministic OpenStudio translation with required meters.\n"
            f"expected={expected_hash}\nactual={actual_hash}"
        )


def test_simulation_matches_reference() -> None:
    plan = _load_plan()
    reference_metrics = _load_reference_metrics()
    expected_key_order = list(plan["summary_key_order"])
    meter_names = list(plan["required_meter_names"])
    expected_row_count = int(plan["source_row_count"])
    tolerance = float(reference_metrics["relative_tolerance"])
    reference_totals = dict(reference_metrics["reference_totals_kwh"])

    summary_entries = _parse_summary(SUMMARY_PATH)
    actual_key_order = [key for key, _ in summary_entries]
    assert actual_key_order == expected_key_order, (
        f"Summary keys/order mismatch: expected={expected_key_order} got={actual_key_order}"
    )
    summary = dict(summary_entries)

    translated_version = _parse_idf_value(
        GENERATED_IDF_PATH,
        r"\bVersion,\s*\n\s*([^;]+);",
        "Version",
    )
    building_name = _parse_idf_value(
        GENERATED_IDF_PATH,
        r"\bBuilding,\s*\n\s*([^,\n]+),",
        "Building name",
    )

    assert summary["bldg_id"] == str(int(plan["source_bldg_id"])), (
        f"bldg_id mismatch: expected={plan['source_bldg_id']} got={summary['bldg_id']}"
    )
    assert summary["translated_version"] == translated_version, (
        f"translated_version mismatch: expected={translated_version} got={summary['translated_version']}"
    )
    assert summary["building_name"] == building_name, (
        f"building_name mismatch: expected={building_name!r} got={summary['building_name']!r}"
    )
    assert summary["weather_file"] == Path(str(plan["source_weather"])).name, (
        f"weather_file mismatch: expected={Path(str(plan['source_weather'])).name} got={summary['weather_file']}"
    )
    assert summary["row_count"] == str(expected_row_count), (
        f"row_count mismatch: expected={expected_row_count} got={summary['row_count']}"
    )

    agent_meter_totals, agent_sample_counts = _load_meter_totals(
        SIMULATION_OUTPUT_DIR / "eplusout.mtr",
        meter_names,
    )
    for meter_name in meter_names:
        assert agent_sample_counts[meter_name] == expected_row_count, (
            f"Unexpected sample count for {meter_name}: "
            f"expected={expected_row_count} got={agent_sample_counts[meter_name]}"
        )
        _assert_close(
            float(summary[SUMMARY_KEY_BY_METER[meter_name]]),
            agent_meter_totals[meter_name],
            SUMMARY_KEY_BY_METER[meter_name],
        )
    _assert_close(
        float(summary["annual_site_energy_kwh"]),
        sum(agent_meter_totals.values()),
        "annual_site_energy_kwh",
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        rerun_output_dir = Path(tmp_dir) / "rerun"
        _run_energyplus(GENERATED_IDF_PATH, rerun_output_dir)
        _assert_successful_run(rerun_output_dir)
        rerun_meter_totals, rerun_sample_counts = _load_meter_totals(
            rerun_output_dir / "eplusout.mtr",
            meter_names,
        )

    for meter_name in meter_names:
        assert rerun_sample_counts[meter_name] == expected_row_count, (
            f"Reference rerun sample count mismatch for {meter_name}: "
            f"expected={expected_row_count} got={rerun_sample_counts[meter_name]}"
        )
        _assert_close(
            agent_meter_totals[meter_name],
            rerun_meter_totals[meter_name],
            f"{meter_name} rerun total",
        )
        _assert_within_relative_tolerance(
            rerun_meter_totals[meter_name],
            float(reference_totals[SUMMARY_KEY_BY_METER[meter_name]]),
            tolerance,
            SUMMARY_KEY_BY_METER[meter_name],
        )

    _assert_within_relative_tolerance(
        sum(rerun_meter_totals.values()),
        float(reference_totals["annual_site_energy_kwh"]),
        tolerance,
        "annual_site_energy_kwh",
    )


def _run_named_test(test_name: str) -> int:
    fn = globals().get(test_name)
    if fn is None or not callable(fn):
        print(f"Unknown test function: {test_name}", flush=True)
        return 2
    try:
        fn()
    except Exception:
        traceback.print_exc()
        return 1
    print(f"{test_name}: PASS", flush=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: openstudio execute_python_script /tests/test_outputs.py "
            "<test_output_files_exist|test_generated_idf_matches_reference|test_simulation_matches_reference>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
