# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import tempfile
from itertools import product
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_OVERRIDE = os.environ.get("TUA_SANITY_ROOT")
BOOKMARKS_PATH = "/home/user/.config/google-chrome/Default/Bookmarks"
ARTIFACT_DIR = Path("/logs/artifacts")
RULE = {
    "type": "liked_authors_websites_urls",
    "names": ["Liked Authors"],
    "urls": [
        [
            "https://jimfan.me",
            "https://research.nvidia.com/person/linxi-jim-fan",
            "https://www.linkedin.com/in/drjimfan",
        ],
        [
            "https://research.nvidia.com/person/de-an-huang",
            "https://ai.stanford.edu/~dahuang",
            "https://www.linkedin.com/in/de-an-huang-38242a69",
        ],
        [
            "https://yukezhu.me",
            "https://www.cs.utexas.edu/people/faculty-researchers/yuke-zhu",
            "https://experts.utexas.edu/yuke_zhu",
            "https://research.nvidia.com/person/yuke-zhu",
            "https://www.linkedin.com/in/yukez",
        ],
        [
            "https://tensorlab.cms.caltech.edu/users/anima",
            "http://tensorlab.cms.caltech.edu/users/anima",
            "https://tensorlab.cms.caltech.edu/users/anima/bio.html",
            "https://www.eas.caltech.edu/people/anima",
            "https://en.wikipedia.org/wiki/Anima_Anandkumar",
            "https://www.linkedin.com/in/anima-anandkumar",
        ],
    ],
}
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
ORACLE_URLS = [
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


def normalize_bookmark_url(url: str) -> str:
    parts = urlsplit(url)
    # Ignore path-only trailing slash differences introduced by browser canonicalization.
    normalized_path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, normalized_path, parts.query, parts.fragment))


def make_url_node(url: str, index: int) -> dict[str, str]:
    return {
        "date_added": str(13300000000000010 + index),
        "guid": f"11111111-1111-4111-8111-{index:012d}",
        "id": str(10 + index),
        "name": url,
        "type": "url",
        "url": url,
    }


def make_payload(urls: list[str]) -> dict[str, object]:
    return {
        "checksum": "",
        "roots": {
            "bookmark_bar": {
                "children": [
                    {
                        "children": [make_url_node(url, index) for index, url in enumerate(urls, start=1)],
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
            "other": EMPTY_BOOKMARKS["roots"]["other"],
            "synced": EMPTY_BOOKMARKS["roots"]["synced"],
        },
        "version": 1,
    }


def bookmarks_path() -> Path:
    return localize_path(BOOKMARKS_PATH)


def get_bookmarks() -> Any:
    try:
        return json.loads(bookmarks_path().read_text(encoding="utf-8")).get("roots", {})
    except FileNotFoundError:
        return []
    except Exception as exc:
        logger.error("Failed to load bookmarks: %s", exc)
        return []


def is_expected_bookmarks(bookmarks: Any, rule: dict[str, Any]) -> float:
    if not bookmarks:
        return 0.0
    liked_authors_folder = next(
        (
            bookmark
            for bookmark in bookmarks.get("bookmark_bar", {}).get("children", [])
            if bookmark.get("type") == "folder" and bookmark.get("name") == "Liked Authors"
        ),
        None,
    )
    if not liked_authors_folder:
        return 0.0

    liked_authors_urls = [
        bookmark["url"]
        for bookmark in liked_authors_folder.get("children", [])
        if bookmark.get("type") == "url" and "url" in bookmark
    ]
    logger.info("Liked Authors urls: %s", liked_authors_urls)
    normalized_liked_authors_urls = {normalize_bookmark_url(url) for url in liked_authors_urls}

    choices = [option if isinstance(option, list) else [option] for option in rule["urls"]]
    for combination in product(*choices):
        if {normalize_bookmark_url(url) for url in combination} == normalized_liked_authors_urls:
            return 1.0
    return 0.0


def evaluate_current_state() -> float:
    return float(is_expected_bookmarks(get_bookmarks(), RULE))


def persist_artifacts() -> None:
    source = bookmarks_path()
    if not source.exists():
        return
    try:
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, ARTIFACT_DIR / source.name)
    except OSError as exc:
        logger.info("Skipping artifact copy: %s", exc)


def write_bookmarks(payload: dict[str, object]) -> None:
    destination = bookmarks_path()
    ensure_parent(destination)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run_sanity() -> dict[str, float]:
    with tempfile.TemporaryDirectory(prefix="094-author-homepage-bookmarks-") as temp_dir:
        os.environ["TUA_SANITY_ROOT"] = temp_dir
        global ROOT_OVERRIDE
        ROOT_OVERRIDE = temp_dir

        write_bookmarks(EMPTY_BOOKMARKS)
        fail_score = evaluate_current_state()

        write_bookmarks(make_payload(ORACLE_URLS))
        pass_score = evaluate_current_state()

        return {"pass_score": pass_score, "fail_score": fail_score}


def main() -> int:
    score = evaluate_current_state()
    persist_artifacts()
    print(score)
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sanity":
        print(json.dumps(run_sanity(), sort_keys=True))
    else:
        raise SystemExit(main())
