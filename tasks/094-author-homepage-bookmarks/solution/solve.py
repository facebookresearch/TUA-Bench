# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT_OVERRIDE = os.environ.get("TUA_SANITY_ROOT")
BOOKMARKS_PATH = "/home/user/.config/google-chrome/Default/Bookmarks"
LIKED_AUTHORS_URLS = [
    "https://jimfan.me/",
    "https://research.nvidia.com/person/de-an-huang",
    "https://yukezhu.me/",
    "https://tensorlab.cms.caltech.edu/users/anima/",
]


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


def make_url_node(url: str, index: int) -> dict[str, str]:
    return {
        "date_added": str(13300000000000010 + index),
        "guid": f"11111111-1111-4111-8111-{index:012d}",
        "id": str(10 + index),
        "name": url,
        "type": "url",
        "url": url,
    }


def make_bookmarks_payload() -> dict[str, object]:
    children = [make_url_node(url, index) for index, url in enumerate(LIKED_AUTHORS_URLS, start=1)]
    return {
        "checksum": "",
        "roots": {
            "bookmark_bar": {
                "children": [
                    {
                        "children": children,
                        "date_added": "13300000000000003",
                        "date_last_used": "0",
                        "date_modified": "13300000000000009",
                        "guid": "22222222-2222-4222-8222-222222222222",
                        "id": "4",
                        "name": "Liked Authors",
                        "type": "folder",
                    }
                ],
                "date_added": "13300000000000000",
                "date_last_used": "0",
                "date_modified": "13300000000000009",
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


def main() -> int:
    bookmarks_path = localize_path(BOOKMARKS_PATH)
    ensure_parent(bookmarks_path)
    bookmarks_path.write_text(json.dumps(make_bookmarks_payload(), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
