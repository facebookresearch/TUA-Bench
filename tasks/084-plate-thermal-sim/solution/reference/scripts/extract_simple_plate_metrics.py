#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?")


def latest_time_dir(case_dir: Path) -> Path:
    candidates: list[tuple[float, Path]] = []
    for path in case_dir.iterdir():
        if not path.is_dir():
            continue
        try:
            value = float(path.name)
        except ValueError:
            continue
        if value > 0:
            candidates.append((value, path))
    if not candidates:
        raise FileNotFoundError(f"No positive time directories found in {case_dir}")
    return max(candidates, key=lambda item: item[0])[1]


def parse_scalar_list_after(keyword: str, text: str) -> list[float]:
    match = re.search(
        rf"{keyword}\s+nonuniform\s+List<scalar>\s+\d+\s*\((.*?)\)\s*;",
        text,
        re.S,
    )
    if match:
        return [float(token) for token in FLOAT_RE.findall(match.group(1))]
    match = re.search(rf"{keyword}\s+uniform\s+({FLOAT_RE.pattern})\s*;", text)
    if match:
        return [float(match.group(1))]
    raise ValueError(f"Could not parse {keyword} scalar values")


def patch_block(text: str, patch_name: str) -> str:
    match = re.search(rf"^\s*{re.escape(patch_name)}\s*\{{", text, re.M)
    if not match:
        raise ValueError(f"Could not find boundary patch {patch_name}")
    start = match.end()
    depth = 1
    index = start
    while index < len(text) and depth:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
        index += 1
    if depth != 0:
        raise ValueError(f"Patch {patch_name} has an unterminated block")
    return text[start : index - 1]


def field_metrics(case_dir: Path) -> tuple[float, dict[str, float]]:
    time_dir = latest_time_dir(case_dir)
    text = (time_dir / "T").read_text(encoding="ascii", errors="ignore")
    internal = parse_scalar_list_after("internalField", text)
    top_temperatures: list[float] = []
    for patch_name in ("heatSource", "topRest"):
        top_temperatures.extend(parse_scalar_list_after("value", patch_block(text, patch_name)))
    reported = internal + top_temperatures
    return float(time_dir.name), {
        "internal_min_temperature_K": min(internal),
        "internal_max_temperature_K": max(internal),
        "top_surface_min_temperature_K": min(top_temperatures),
        "top_surface_max_temperature_K": max(top_temperatures),
        "reported_min_temperature_K": min(reported),
        "reported_max_temperature_K": max(reported),
    }


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: extract_simple_plate_metrics.py <case_dir> <ground_truth_json> <output_json>"
        )
    case_dir = Path(sys.argv[1]).resolve()
    ground_truth = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    output_path = Path(sys.argv[3]).resolve()

    final_time, metrics = field_metrics(case_dir)
    payload = {
        "case_name": "simple_plate",
        "final_time_s": final_time,
        "mesh": ground_truth["mesh"],
        "metrics": metrics,
    }
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
