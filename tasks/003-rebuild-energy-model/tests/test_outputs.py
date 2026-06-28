# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import math
import re
import sqlite3
import traceback
from pathlib import Path

PLAN_PATH = Path("/app/input/task_plan.json")
ARTIFACT_DIR = Path("/app/artifacts")
SUMMARY_PATH = ARTIFACT_DIR / "simulation_summary.txt"
SIMULATION_OUTPUT_DIR = ARTIFACT_DIR / "energyplus_run"
MTR_PATH = SIMULATION_OUTPUT_DIR / "eplusout.mtr"
END_PATH = SIMULATION_OUTPUT_DIR / "eplusout.end"
REFERENCE_SQL_PATH = Path("/tests/reference/eplusout.sql")

SUMMARY_KEY_BY_METER = {
    "Electricity:Facility": "annual_electricity_kwh",
    "NaturalGas:Facility": "annual_natural_gas_kwh",
    "FuelOilNo2:Facility": "annual_fuel_oil_kwh",
}
REFERENCE_SQL_KEY_BY_SUMMARY_KEY = {
    "annual_electricity_kwh": ("End Uses", "Total End Uses", "Electricity", "GJ"),
    "annual_natural_gas_kwh": ("End Uses", "Total End Uses", "Natural Gas", "GJ"),
    "annual_fuel_oil_kwh": ("End Uses", "Total End Uses", "Fuel Oil No 2", "GJ"),
    "annual_site_energy_kwh": ("Site and Source Energy", "Total Site Energy", "Total Energy", "GJ"),
}
FLOAT_ABS_TOL = 1e-3
GJ_TO_KWH = 277.77777777777777


def _load_plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _parse_summary(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "=" not in line:
            raise AssertionError(f"Invalid summary line (missing '='): {line}")
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


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
    if missing:
        raise AssertionError(f"Missing required meters in {mtr_path}: {missing}")

    totals_kwh = {name: totals_joules[name] / 3.6e6 for name in meter_names}
    return totals_kwh, sample_counts


def _load_reference_sql_totals() -> dict[str, float]:
    assert REFERENCE_SQL_PATH.exists(), f"Missing reference SQL: {REFERENCE_SQL_PATH}"
    assert REFERENCE_SQL_PATH.stat().st_size > 0, f"Reference SQL is empty: {REFERENCE_SQL_PATH}"

    query = """
        select tn.Value, rown.Value, coln.Value, un.Value, td.Value
        from TabularData td
        left join Strings rn on rn.StringIndex = td.ReportNameIndex
        left join Strings tn on tn.StringIndex = td.TableNameIndex
        left join Strings rown on rown.StringIndex = td.RowNameIndex
        left join Strings coln on coln.StringIndex = td.ColumnNameIndex
        left join Strings un on un.StringIndex = td.UnitsIndex
        where rn.Value = 'AnnualBuildingUtilityPerformanceSummary'
    """

    values: dict[tuple[str, str, str, str], float] = {}
    with sqlite3.connect(REFERENCE_SQL_PATH) as connection:
        for table, row, column, units, value in connection.execute(query):
            try:
                values[(str(table), str(row), str(column), str(units))] = float(str(value).strip())
            except ValueError:
                continue

    totals: dict[str, float] = {}
    for summary_key, sql_key in REFERENCE_SQL_KEY_BY_SUMMARY_KEY.items():
        totals[summary_key] = values.get(sql_key, 0.0) * GJ_TO_KWH

    missing = [
        summary_key
        for summary_key, sql_key in REFERENCE_SQL_KEY_BY_SUMMARY_KEY.items()
        if sql_key not in values and summary_key != "annual_natural_gas_kwh"
    ]
    if missing:
        raise AssertionError(f"Missing required annual totals in reference SQL: {missing}")

    return totals


def _assert_successful_run() -> None:
    assert END_PATH.exists(), f"Missing EnergyPlus completion marker: {END_PATH}"
    end_text = END_PATH.read_text(encoding="utf-8", errors="ignore")
    assert "Completed Successfully" in end_text, f"EnergyPlus did not complete successfully: {END_PATH}"


def _assert_close(actual: float, expected: float, label: str) -> None:
    assert math.isclose(actual, expected, rel_tol=0.0, abs_tol=FLOAT_ABS_TOL), (
        f"{label} mismatch: expected={expected} got={actual}"
    )


def _assert_within_relative_tolerance(actual: float, expected: float, tolerance: float, label: str) -> None:
    if math.isclose(expected, 0.0, rel_tol=0.0, abs_tol=FLOAT_ABS_TOL):
        assert math.isclose(actual, 0.0, rel_tol=0.0, abs_tol=FLOAT_ABS_TOL), (
            f"{label} expected zero but got {actual}"
        )
        return
    relative_error = abs(actual - expected) / abs(expected)
    assert relative_error <= tolerance, (
        f"{label} outside tolerance: expected={expected} got={actual} "
        f"relative_error={relative_error:.6%} tolerance={tolerance:.6%}"
    )


def main() -> None:
    plan = _load_plan()
    for path in (SUMMARY_PATH, MTR_PATH, END_PATH):
        assert path.exists(), f"Missing required energy artifact: {path}"
        assert path.stat().st_size > 0, f"Required energy artifact is empty: {path}"

    _assert_successful_run()

    optional_review_paths = [
        Path(str(plan["reconstructed_osm_output"])),
        Path(str(plan["translated_idf_output"])),
        Path(str(plan["review_render_output"])),
    ]
    for path in optional_review_paths:
        if not path.exists() or path.stat().st_size == 0:
            print(f"warning: optional review artifact missing or empty: {path}", flush=True)

    summary = _parse_summary(SUMMARY_PATH)
    required_summary_keys = [
        "annual_electricity_kwh",
        "annual_natural_gas_kwh",
        "annual_fuel_oil_kwh",
        "annual_site_energy_kwh",
    ]
    for key in required_summary_keys:
        assert key in summary, f"Missing summary key: {key}"

    expected_row_count = int(plan["source_row_count"])
    tolerance = float(plan["relative_tolerance"])
    meter_names = list(plan["required_meter_names"])

    agent_meter_totals, agent_sample_counts = _load_meter_totals(MTR_PATH, meter_names)
    for meter_name in meter_names:
        assert agent_sample_counts[meter_name] == expected_row_count, (
            f"Unexpected sample count for {meter_name}: "
            f"expected={expected_row_count} got={agent_sample_counts[meter_name]}"
        )
        summary_key = SUMMARY_KEY_BY_METER[meter_name]
        _assert_close(float(summary[summary_key]), agent_meter_totals[meter_name], summary_key)

    agent_site_total = sum(agent_meter_totals.values())
    _assert_close(float(summary["annual_site_energy_kwh"]), agent_site_total, "annual_site_energy_kwh")

    reference_totals = _load_reference_sql_totals()

    for summary_key, reference_total in reference_totals.items():
        actual = agent_site_total if summary_key == "annual_site_energy_kwh" else float(summary[summary_key])
        _assert_within_relative_tolerance(actual, reference_total, tolerance, summary_key)

    print("energy check passed", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
