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
from pathlib import Path

import openstudio

plan = json.loads(Path("/app/input/task_plan.json").read_text(encoding="utf-8"))
osm_path = Path("/app/input") / str(plan["source_osm"])
idf_path = Path(str(plan["translated_idf_output"]))
summary_path = Path(str(plan["summary_output"]))

translator = openstudio.osversion.VersionTranslator()
model_opt = translator.loadModel(openstudio.path(str(osm_path)))
if not model_opt.is_initialized():
    raise SystemExit(f"Could not load OSM model: {osm_path}")

workspace = openstudio.energyplus.ForwardTranslator().translateModel(model_opt.get())
if not workspace.save(openstudio.path(str(idf_path)), True):
    raise SystemExit(f"Could not save translated IDF: {idf_path}")

idf_text = idf_path.read_text(encoding="utf-8")


def extract(pattern: str, label: str) -> str:
    match = re.search(pattern, idf_text, flags=re.IGNORECASE)
    if match is None:
        raise SystemExit(f"Could not find {label} in {idf_path}")
    return match.group(1).strip()


translated_version = extract(r"\bVersion,\s*\n\s*([^;]+);", "Version")
building_name = extract(r"\bBuilding,\s*\n\s*([^,\n]+),", "Building name")

summary_path.write_text(
    "\n".join(
        [
            f"bldg_id={int(plan['source_bldg_id'])}",
            f"translated_version={translated_version}",
            f"building_name={building_name}",
            f"row_count={int(plan['source_row_count'])}",
            f"annual_site_energy_kwh={float(plan['annual_site_energy_kwh']):.6f}",
            f"peak_hourly_site_energy_kwh={float(plan['peak_hourly_site_energy_kwh']):.6f}",
        ]
    )
    + "\n",
    encoding="utf-8",
)
PY

openstudio execute_python_script /tmp/solve_task.py
