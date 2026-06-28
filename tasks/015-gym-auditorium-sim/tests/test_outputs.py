# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import re
import sqlite3
import sys
import traceback
from pathlib import Path

PLAN_PATH = Path("/app/input/task_plan.json")
CANDIDATE_OSM_PATH = Path("/app/artifacts/gym_auditorium_only.osm")
CANDIDATE_IDF_PATH = Path("/app/artifacts/generated_building.idf")
CANDIDATE_RUN_DIR = Path("/app/artifacts/energyplus_run")
CANDIDATE_SQL_PATH = CANDIDATE_RUN_DIR / "eplusout.sql"
CANDIDATE_END_PATH = CANDIDATE_RUN_DIR / "eplusout.end"
CANDIDATE_ERR_PATH = CANDIDATE_RUN_DIR / "eplusout.err"
REFERENCE_SQL_PATH = Path("/tests/reference/eplusout.sql")


def _load_plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _assert_file_exists(path: Path, *, nonempty: bool = True) -> None:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Expected a file: {path}"
    if nonempty:
        assert path.stat().st_size > 0, f"Required file is empty: {path}"


def _connect_sqlite(path: Path) -> sqlite3.Connection:
    _assert_file_exists(path)
    conn = sqlite3.connect(path)
    integrity = conn.execute("pragma integrity_check").fetchone()
    assert integrity and integrity[0] == "ok", f"SQLite integrity check failed for {path}: {integrity}"
    return conn


def _annual_summary_values(path: Path) -> dict[tuple[str, str, str, str], float]:
    conn = _connect_sqlite(path)
    try:
        rows = conn.execute(
            """
            select tn.Value, rown.Value, coln.Value, un.Value, td.Value
            from TabularData td
            left join Strings rn on rn.StringIndex = td.ReportNameIndex
            left join Strings tn on tn.StringIndex = td.TableNameIndex
            left join Strings rown on rown.StringIndex = td.RowNameIndex
            left join Strings coln on coln.StringIndex = td.ColumnNameIndex
            left join Strings un on un.StringIndex = td.UnitsIndex
            where rn.Value = 'AnnualBuildingUtilityPerformanceSummary'
            """
        ).fetchall()
    finally:
        conn.close()

    values: dict[tuple[str, str, str, str], float] = {}
    for table_name, row_name, column_name, units, raw_value in rows:
        if raw_value is None:
            continue
        text_value = str(raw_value).strip()
        if not text_value:
            continue
        try:
            value = float(text_value)
        except ValueError:
            continue
        key = (
            str(table_name or ""),
            str(row_name or ""),
            str(column_name or ""),
            str(units or ""),
        )
        values[key] = value
    return values


def test_required_artifacts_exist() -> None:
    _assert_file_exists(CANDIDATE_OSM_PATH)
    _assert_file_exists(CANDIDATE_IDF_PATH)
    _assert_file_exists(CANDIDATE_SQL_PATH)
    _assert_file_exists(CANDIDATE_END_PATH)
    _assert_file_exists(CANDIDATE_ERR_PATH, nonempty=False)


def test_simulation_completed() -> None:
    _assert_file_exists(CANDIDATE_SQL_PATH)
    _assert_file_exists(CANDIDATE_END_PATH)
    _assert_file_exists(CANDIDATE_ERR_PATH, nonempty=False)

    end_text = CANDIDATE_END_PATH.read_text(encoding="utf-8", errors="ignore")
    err_text = CANDIDATE_ERR_PATH.read_text(encoding="utf-8", errors="ignore")

    assert "Completed Successfully" in end_text, (
        f"EnergyPlus did not report successful completion in {CANDIDATE_END_PATH}:\n"
        f"{end_text[-4000:]}"
    )
    assert "Fatal" not in err_text, f"EnergyPlus reported fatal errors:\n{err_text[-4000:]}"

    severe_counts = [int(value) for value in re.findall(r"(\d+)\s+Severe Errors", err_text)]
    assert all(value == 0 for value in severe_counts), (
        f"EnergyPlus reported severe errors:\n{err_text[-4000:]}"
    )


def test_sql_matches_reference() -> None:
    plan = _load_plan()
    relative_tolerance = float(plan["sql_relative_tolerance"])
    zero_abs_tolerance = float(plan["sql_zero_abs_tolerance_gj"])

    actual_values = _annual_summary_values(CANDIDATE_SQL_PATH)
    reference_values = _annual_summary_values(REFERENCE_SQL_PATH)

    failures: list[str] = []
    for metric in plan["sql_metrics"]:
        key = (
            str(metric["table"]),
            str(metric["row"]),
            str(metric["column"]),
            str(metric["units"]),
        )
        assert key in reference_values, f"Reference SQL is missing metric: {key}"
        if key not in actual_values:
            failures.append(f"missing metric {key}")
            continue

        expected = reference_values[key]
        actual = actual_values[key]
        abs_error = abs(actual - expected)

        if abs(expected) <= zero_abs_tolerance:
            passed = abs_error <= zero_abs_tolerance
            error_text = f"abs_error={abs_error:.6g} GJ"
        else:
            relative_error = abs_error / abs(expected)
            passed = relative_error <= relative_tolerance
            error_text = f"relative_error={relative_error:.3%}"

        print(
            f"{key}: actual={actual:.6g} expected={expected:.6g} {error_text}",
            flush=True,
        )
        if not passed:
            failures.append(
                f"{key}: actual {actual:.6g}, expected {expected:.6g}, {error_text}"
            )

    assert not failures, "Simulation SQL did not match reference within tolerance:\n" + "\n".join(
        failures
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
            "Usage: python3 /tests/test_outputs.py "
            "<test_required_artifacts_exist|test_simulation_completed|test_sql_matches_reference>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
