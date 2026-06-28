# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

INPUT_DIR = Path("/app/input")
ARTIFACT_DIR = Path("/app/artifacts")
CASE_TEMPLATE_DIR = Path(__file__).resolve().parent / "reference_case"
TASK_PLAN_PATH = INPUT_DIR / "task_plan.json"
VERIFIER_RERUN_DIR = ARTIFACT_DIR / "verifier_rerun"
RERUN_CASE_DIR = Path("/tmp/verifier_cold_plate_case")

PLAN = json.loads(TASK_PLAN_PATH.read_text(encoding="utf-8"))
IMPROVED_CASE_DIR = Path(PLAN["case_output_dir"])
METRICS_OUTPUT = Path(PLAN["metrics_output"])
COMPARISON_OUTPUT = Path(PLAN["comparison_output"])
RENDER_DIR = Path(PLAN["render_dir"])
REQUIRED_METRIC_KEYS = {
    "chip_average_temperature_k",
    "solid_max_temperature_k",
    "pressure_drop_pa",
    "outlet_mass_flow_kg_s",
    "thermal_resistance_k_per_w",
}


def _load_template_build_case():
    spec = importlib.util.spec_from_file_location(
        "cold_plate_template_build_case",
        CASE_TEMPLATE_DIR / "build_case.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD_CASE = _load_template_build_case()


def _assert_file_nonempty(path: Path) -> None:
    assert path.exists(), f"Missing required file: {path}"
    assert path.is_file(), f"Expected a file at: {path}"
    assert path.stat().st_size > 0, f"Required file is empty: {path}"


def _load_json_file(path: Path) -> dict:
    _assert_file_nonempty(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"Expected a JSON object in {path}"
    return payload


def _load_artifact_design() -> dict:
    design_path = IMPROVED_CASE_DIR / "design.json"
    return BUILD_CASE._load_design(design_path)


def _validate_design_constraints() -> None:
    envelope = PLAN["plate_envelope_mm"]
    assert envelope == [BUILD_CASE.PLATE_X_MM, BUILD_CASE.PLATE_Y_MM, BUILD_CASE.PLATE_Z_MM]
    assert PLAN["minimum_solid_thickness_mm"] == BUILD_CASE.DESIGN_RESOLUTION_MM
    assert PLAN["minimum_fluid_gap_mm"] == BUILD_CASE.DESIGN_RESOLUTION_MM
    design = _load_artifact_design()
    BUILD_CASE._validate_design(design)


def _tail(path: Path, line_count: int = 80) -> str:
    if not path.exists():
        return f"{path} does not exist"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-line_count:])


def _copy_tree_if_present(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copytree(src, dst)


def _persist_rerun_outputs(case_dir: Path) -> None:
    if VERIFIER_RERUN_DIR.exists():
        shutil.rmtree(VERIFIER_RERUN_DIR)
    VERIFIER_RERUN_DIR.mkdir(parents=True, exist_ok=True)

    for file_name in ("design.json", "metrics.json"):
        src = case_dir / file_name
        if src.exists():
            shutil.copy2(src, VERIFIER_RERUN_DIR / file_name)

    _copy_tree_if_present(case_dir / "logs", VERIFIER_RERUN_DIR / "logs")
    _copy_tree_if_present(case_dir / "renders", VERIFIER_RERUN_DIR / "renders")
    _copy_tree_if_present(case_dir / "postProcessing", VERIFIER_RERUN_DIR / "postProcessing")


def _stage_clean_case() -> Path:
    if RERUN_CASE_DIR.exists():
        shutil.rmtree(RERUN_CASE_DIR)
    shutil.copytree(CASE_TEMPLATE_DIR, RERUN_CASE_DIR)
    shutil.copy2(IMPROVED_CASE_DIR / "design.json", RERUN_CASE_DIR / "design.json")
    return RERUN_CASE_DIR


def _run_clean_rerun() -> dict:
    case_dir = _stage_clean_case()
    try:
        subprocess.run(
            ["bash", "./run_case.sh"],
            cwd=case_dir,
            check=True,
            timeout=3600,
        )
    except subprocess.CalledProcessError as exc:
        _persist_rerun_outputs(case_dir)
        foam_log = _tail(case_dir / "logs" / "foamMultiRun.log")
        raise AssertionError(
            "Verifier rerun failed.\n"
            f"See {VERIFIER_RERUN_DIR} for copied logs.\n"
            f"foamMultiRun.log tail:\n{foam_log}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        _persist_rerun_outputs(case_dir)
        raise AssertionError("Verifier rerun timed out after 3600 seconds") from exc

    _persist_rerun_outputs(case_dir)
    metrics = _load_json_file(case_dir / "metrics.json")
    missing = REQUIRED_METRIC_KEYS - set(metrics)
    assert not missing, f"Rerun metrics.json is missing keys: {sorted(missing)}"
    return metrics


def test_outputs_exist() -> None:
    assert ARTIFACT_DIR.exists(), "Missing /app/artifacts"
    assert IMPROVED_CASE_DIR.exists(), f"Missing improved case directory: {IMPROVED_CASE_DIR}"

    for relative_path in PLAN["required_case_files"]:
        _assert_file_nonempty(IMPROVED_CASE_DIR / relative_path)

    metrics = _load_json_file(METRICS_OUTPUT)
    missing = REQUIRED_METRIC_KEYS - set(metrics)
    assert not missing, f"Artifact metrics.json is missing keys: {sorted(missing)}"

    _assert_file_nonempty(COMPARISON_OUTPUT)

    for render_name in PLAN["required_render_files"]:
        _assert_file_nonempty(RENDER_DIR / render_name)


def test_design_constraints() -> None:
    _validate_design_constraints()


def test_rerun_meets_targets() -> None:
    _validate_design_constraints()
    metrics = _run_clean_rerun()
    targets = PLAN["target_metrics"]

    chip_temperature = float(metrics["chip_average_temperature_k"])
    pressure_drop = float(metrics["pressure_drop_pa"])
    outlet_mass_flow = float(metrics["outlet_mass_flow_kg_s"])

    assert chip_temperature <= float(targets["chip_average_temperature_k_max"]), (
        f"Chip average temperature target failed: "
        f"{chip_temperature:.6f} K > {targets['chip_average_temperature_k_max']:.6f} K"
    )
    assert pressure_drop <= float(targets["pressure_drop_pa_max"]), (
        f"Pressure drop target failed: "
        f"{pressure_drop:.6f} Pa > {targets['pressure_drop_pa_max']:.6f} Pa"
    )
    assert outlet_mass_flow >= float(targets["outlet_mass_flow_kg_s_min"]), (
        f"Outlet mass-flow target failed: "
        f"{outlet_mass_flow:.9f} kg/s < {targets['outlet_mass_flow_kg_s_min']:.9f} kg/s"
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
            "<test_outputs_exist|test_design_constraints|test_rerun_meets_targets>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
