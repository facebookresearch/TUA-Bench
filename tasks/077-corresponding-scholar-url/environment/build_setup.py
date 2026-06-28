#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


SPEC_PATH = Path(__file__).with_name("task_spec.json")
if not SPEC_PATH.exists():
    SPEC_PATH = Path("/usr/local/share/tua/task_spec.json")
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
CACHE_DIR = Path("/tmp") / SPEC["slug"] / "build"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def fetch(url: str, dest_name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = CACHE_DIR / dest_name
    if not target.exists():
        subprocess.run(
            ["curl", "-fL", "--retry", "3", "--retry-delay", "1", url, "-o", str(target)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return target


def main() -> int:
    Path("/app").mkdir(parents=True, exist_ok=True)
    for item in SPEC.get("downloads", []):
        destination = Path(item["path"]).expanduser()
        ensure_parent(destination)
        if destination.exists():
            continue
        shutil.copyfile(fetch(item["url"], item["dest_name"]), destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
