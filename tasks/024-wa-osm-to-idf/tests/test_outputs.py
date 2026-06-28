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
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

PLAN_PATH = Path("/app/input/task_plan.json")
OSM_PATH = Path("/app/input/building.osm")
PARQUET_PATH = Path("/app/input/building_timeseries.parquet")
GENERATED_IDF_PATH = Path("/app/generated_building.idf")
SUMMARY_PATH = Path("/app/translation_summary.txt")

FLOAT_ABS_TOL = 1e-6


def _load_plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_idf_value(idf_path: Path, pattern: str, label: str) -> str:
    text = idf_path.read_text(encoding="utf-8")
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        raise AssertionError(f"Could not find {label} in {idf_path}")
    return match.group(1).strip()


def _build_reference_idf(output_path: Path) -> None:
    script_text = f"""from __future__ import annotations
import sys
import openstudio

osm_path = {str(OSM_PATH)!r}
idf_path = {str(output_path)!r}

translator = openstudio.osversion.VersionTranslator()
model_opt = translator.loadModel(openstudio.path(osm_path))
if not model_opt.is_initialized():
    raise SystemExit(f"Could not load OSM model: {{osm_path}}")

workspace = openstudio.energyplus.ForwardTranslator().translateModel(model_opt.get())
if not workspace.save(openstudio.path(idf_path), True):
    raise SystemExit(f"Could not save translated IDF: {{idf_path}}")
"""

    with tempfile.TemporaryDirectory() as tmp_dir:
        script_path = Path(tmp_dir) / "translate.py"
        script_path.write_text(script_text, encoding="utf-8")
        proc = subprocess.run(
            ["openstudio", "execute_python_script", str(script_path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert proc.returncode == 0, (
            "OpenStudio reference translation failed in verifier.\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )


def _expected_source_metrics() -> dict[str, float | int]:
    plan = _load_plan()
    return {
        "bldg_id": int(plan["source_bldg_id"]),
        "row_count": int(plan["source_row_count"]),
        "annual_site_energy_kwh": float(plan["annual_site_energy_kwh"]),
        "peak_hourly_site_energy_kwh": float(plan["peak_hourly_site_energy_kwh"]),
    }


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


def test_output_files_exist() -> None:
    required = [GENERATED_IDF_PATH, SUMMARY_PATH]
    for path in required:
        assert path.exists(), f"Missing required output: {path}"
        assert path.stat().st_size > 0, f"Required output is empty: {path}"


def test_translated_idf_matches_reference() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        reference_idf = Path(tmp_dir) / "reference.idf"
        _build_reference_idf(reference_idf)
        expected_hash = _sha256(reference_idf)
        actual_hash = _sha256(GENERATED_IDF_PATH)
        assert actual_hash == expected_hash, (
            "Generated IDF does not match deterministic OpenStudio translation.\n"
            f"expected={expected_hash}\nactual={actual_hash}"
        )


def test_summary_matches_inputs() -> None:
    plan = _load_plan()
    expected_key_order = list(plan["summary_key_order"])

    idf_version = _parse_idf_value(
        GENERATED_IDF_PATH,
        r"\bVersion,\s*\n\s*([^;]+);",
        "Version",
    )
    building_name = _parse_idf_value(
        GENERATED_IDF_PATH,
        r"\bBuilding,\s*\n\s*([^,\n]+),",
        "Building name",
    )
    source_metrics = _expected_source_metrics()

    summary_entries = _parse_summary(SUMMARY_PATH)
    actual_key_order = [key for key, _ in summary_entries]
    assert actual_key_order == expected_key_order, (
        f"Summary keys/order mismatch: expected={expected_key_order} got={actual_key_order}"
    )
    summary = dict(summary_entries)

    assert summary["bldg_id"] == str(source_metrics["bldg_id"]), (
        f"bldg_id mismatch: expected={source_metrics['bldg_id']} got={summary['bldg_id']}"
    )
    assert summary["translated_version"] == idf_version, (
        f"translated_version mismatch: expected={idf_version} got={summary['translated_version']}"
    )
    assert summary["building_name"] == building_name, (
        f"building_name mismatch: expected={building_name!r} got={summary['building_name']!r}"
    )
    assert summary["row_count"] == str(source_metrics["row_count"]), (
        f"row_count mismatch: expected={source_metrics['row_count']} got={summary['row_count']}"
    )

    actual_annual = float(summary["annual_site_energy_kwh"])
    actual_peak = float(summary["peak_hourly_site_energy_kwh"])
    assert math.isclose(
        actual_annual,
        float(source_metrics["annual_site_energy_kwh"]),
        rel_tol=0.0,
        abs_tol=FLOAT_ABS_TOL,
    ), (
        "annual_site_energy_kwh mismatch: "
        f"expected={source_metrics['annual_site_energy_kwh']} got={actual_annual}"
    )
    assert math.isclose(
        actual_peak,
        float(source_metrics["peak_hourly_site_energy_kwh"]),
        rel_tol=0.0,
        abs_tol=FLOAT_ABS_TOL,
    ), (
        "peak_hourly_site_energy_kwh mismatch: "
        f"expected={source_metrics['peak_hourly_site_energy_kwh']} got={actual_peak}"
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
            "<test_output_files_exist|test_translated_idf_matches_reference|test_summary_matches_inputs>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
