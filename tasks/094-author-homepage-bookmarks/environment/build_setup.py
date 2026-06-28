#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.


from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


SPEC_PATH = Path(__file__).with_name("task_spec.json")
if not SPEC_PATH.exists():
    SPEC_PATH = Path("/usr/local/share/tua/task_spec.json")
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
CACHE_DIR = Path("/tmp") / SPEC["slug"] / "build"
ROOT_OVERRIDE = os.environ.get("TUA_SANITY_ROOT")
BOOKMARKS_PATH = "/home/user/.config/google-chrome/Default/Bookmarks"

EMPTY_BOOKMARKS = {
    "checksum": "",
    "roots": {
        "bookmark_bar": {
            "children": [],
            "date_added": "13300000000000000",
            "date_last_used": "0",
            "date_modified": "0",
            "guid": "00000000-0000-4000-a000-000000000004",
            "id": "1",
            "name": "Bookmarks bar",
            "type": "folder",
        },
        "other": {
            "children": [],
            "date_added": "13300000000000001",
            "date_last_used": "0",
            "date_modified": "0",
            "guid": "00000000-0000-4000-a000-000000000005",
            "id": "2",
            "name": "Other bookmarks",
            "type": "folder",
        },
        "synced": {
            "children": [],
            "date_added": "13300000000000002",
            "date_last_used": "0",
            "date_modified": "0",
            "guid": "00000000-0000-4000-a000-000000000006",
            "id": "3",
            "name": "Mobile bookmarks",
            "type": "folder",
        },
    },
    "version": 1,
}


def localize_path(path: str | Path) -> Path:
    raw = str(path)
    if ROOT_OVERRIDE:
        root = Path(ROOT_OVERRIDE)
        if raw.startswith("/app/"):
            return root / "app" / raw.removeprefix("/app/")
        if raw == "/app":
            return root / "app"
        if raw.startswith("/home/user/"):
            return root / "home" / "user" / raw.removeprefix("/home/user/")
        if raw == "/home/user":
            return root / "home" / "user"
    return Path(raw).expanduser()


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


def ensure_downloads() -> None:
    for item in SPEC.get("downloads", []):
        destination = localize_path(item["path"])
        ensure_parent(destination)
        if destination.exists():
            continue
        shutil.copyfile(fetch(item["url"], item["dest_name"]), destination)


def ensure_bookmarks_file() -> None:
    bookmarks_path = localize_path(BOOKMARKS_PATH)
    if bookmarks_path.exists():
        return
    ensure_parent(bookmarks_path)
    bookmarks_path.write_text(json.dumps(EMPTY_BOOKMARKS, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ensure_downloads()
    ensure_bookmarks_file()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
