# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

import openstudio

PLAN_PATH = Path("/app/input/task_plan.json")
INPUT_OSM_PATH = Path("/app/input/building.osm")
WEATHER_PATH = Path("/app/input/weather.epw")
CANDIDATE_OSM_PATH = Path("/app/artifacts/gym_auditorium_only.osm")
REFERENCE_OSM_PATH = Path("/tests/reference/gym_auditorium_reference.osm")
ENERGYPLUS_BIN = Path("/opt/openstudio/EnergyPlus/energyplus")

DISALLOWED_SPACE_NAME_TOKENS = {
    "cafeteria",
    "classroom",
    "corridor",
    "kitchen",
    "library",
    "lobby",
    "mechanical",
    "office",
    "restroom",
}


def _load_plan() -> dict:
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def _load_model(path: Path):
    translator = openstudio.osversion.VersionTranslator()
    model_opt = translator.loadModel(openstudio.path(str(path)))
    assert model_opt.is_initialized(), f"Could not load OpenStudio model: {path}"
    return model_opt.get()


def _space_names(model) -> list[str]:
    return [space.nameString() for space in model.getSpaces()]


def _total_floor_area(model) -> float:
    return float(sum(space.floorArea() for space in model.getSpaces()))


def _translate_to_idf(osm_path: Path, idf_path: Path) -> None:
    model = _load_model(osm_path)
    workspace = openstudio.energyplus.ForwardTranslator().translateModel(model)
    assert workspace.save(openstudio.path(str(idf_path)), True), f"Could not save IDF: {idf_path}"


def test_output_exists() -> None:
    assert CANDIDATE_OSM_PATH.exists(), f"Missing required OSM: {CANDIDATE_OSM_PATH}"
    assert CANDIDATE_OSM_PATH.is_file(), f"Expected a file: {CANDIDATE_OSM_PATH}"
    assert CANDIDATE_OSM_PATH.stat().st_size > 0, f"Candidate OSM is empty: {CANDIDATE_OSM_PATH}"


def test_model_contains_only_gym_auditorium() -> None:
    plan = _load_plan()
    candidate = _load_model(CANDIDATE_OSM_PATH)
    reference = _load_model(REFERENCE_OSM_PATH)
    source = _load_model(INPUT_OSM_PATH)

    candidate_names = _space_names(candidate)
    reference_names = _space_names(reference)
    source_names = _space_names(source)

    print(f"source_space_count={len(source_names)}", flush=True)
    print(f"candidate_space_count={len(candidate_names)}", flush=True)
    print(f"reference_space_count={len(reference_names)}", flush=True)

    assert len(candidate_names) == int(plan["expected_space_count"]), (
        f"Expected {plan['expected_space_count']} spaces in the reduced model, "
        f"got {len(candidate_names)}"
    )
    assert len(candidate_names) < len(source_names), "Candidate still appears to contain the whole school"
    assert len(candidate.getThermalZones()) == int(plan["expected_thermal_zone_count"]), (
        f"Expected {plan['expected_thermal_zone_count']} thermal zones, "
        f"got {len(candidate.getThermalZones())}"
    )

    allowed_keywords = [str(token).lower() for token in plan["allowed_space_name_keywords"]]
    for name in candidate_names:
        lower_name = name.lower()
        assert any(token in lower_name for token in allowed_keywords), (
            f"Space does not look like gym/auditorium scope: {name}"
        )
        unexpected = sorted(token for token in DISALLOWED_SPACE_NAME_TOKENS if token in lower_name)
        assert not unexpected, f"Space appears outside gym/auditorium scope: {name} ({unexpected})"

    assert any("gym" in name.lower() for name in candidate_names), "Reduced model is missing gym spaces"
    assert any("auditorium" in name.lower() for name in candidate_names), (
        "Reduced model is missing auditorium spaces"
    )

    reference_area = _total_floor_area(reference)
    candidate_area = _total_floor_area(candidate)
    source_area = _total_floor_area(source)
    tolerance = float(plan["floor_area_relative_tolerance"])
    relative_error = abs(candidate_area - reference_area) / reference_area

    print(f"source_floor_area_m2={source_area:.3f}", flush=True)
    print(f"candidate_floor_area_m2={candidate_area:.3f}", flush=True)
    print(f"reference_floor_area_m2={reference_area:.3f}", flush=True)

    assert candidate_area < source_area * 0.6, "Candidate floor area is too large for the reduced scope"
    assert relative_error <= tolerance, (
        f"Candidate floor area differs from reference by {relative_error:.2%}; "
        f"allowed {tolerance:.2%}"
    )


def test_model_simulates_successfully() -> None:
    assert ENERGYPLUS_BIN.exists(), f"Missing EnergyPlus binary: {ENERGYPLUS_BIN}"
    assert WEATHER_PATH.exists(), f"Missing weather file: {WEATHER_PATH}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        idf_path = tmp_path / "candidate.idf"
        run_dir = tmp_path / "energyplus_run"
        run_dir.mkdir(parents=True, exist_ok=True)

        _translate_to_idf(CANDIDATE_OSM_PATH, idf_path)

        proc = subprocess.run(
            [
                str(ENERGYPLUS_BIN),
                "-w",
                str(WEATHER_PATH),
                "-d",
                str(run_dir),
                str(idf_path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        err_path = run_dir / "eplusout.err"
        end_path = run_dir / "eplusout.end"
        err_text = err_path.read_text(encoding="utf-8", errors="ignore") if err_path.exists() else ""
        end_text = end_path.read_text(encoding="utf-8", errors="ignore") if end_path.exists() else ""

        if proc.returncode != 0:
            raise AssertionError(
                "EnergyPlus failed for candidate model.\n"
                f"stdout:\n{proc.stdout[-4000:]}\n"
                f"stderr:\n{proc.stderr[-4000:]}\n"
                f"eplusout.err:\n{err_text[-4000:]}"
            )

        assert "Completed Successfully" in end_text, (
            f"EnergyPlus did not complete successfully. eplusout.end:\n{end_text[-4000:]}"
        )
        assert "Fatal" not in err_text, f"EnergyPlus reported fatal errors:\n{err_text[-4000:]}"

        severe_counts = [int(value) for value in re.findall(r"(\d+)\s+Severe Errors", err_text)]
        assert all(value == 0 for value in severe_counts), (
            f"EnergyPlus reported severe errors:\n{err_text[-4000:]}"
        )

        artifact_dir = Path("/app/artifacts/energyplus_validation_run")
        shutil.rmtree(artifact_dir, ignore_errors=True)
        shutil.copytree(run_dir, artifact_dir)


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
            "<test_output_exists|test_model_contains_only_gym_auditorium|test_model_simulates_successfully>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
