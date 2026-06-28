# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SPEC = json.loads(Path("/usr/local/share/tua/task_spec.json").read_text(encoding="utf-8"))
INPUT_PATH = Path(SPEC["input_path"])
OUTPUT_PATH = Path(SPEC["output_path"])
EXPECTED_URL = SPEC["expected_url"]
EXPECTED_USER_ID = SPEC["expected_user_id"]
EXPECTED_HOSTS = {"scholar.google.com", "www.scholar.google.com"}


def _load_output_text() -> str:
    return OUTPUT_PATH.read_text(encoding="utf-8").strip()


def _parse_output_url():
    text = _load_output_text()
    return text, urlparse(text)


def test_output_exists() -> None:
    assert INPUT_PATH.exists(), f"Missing task input: {INPUT_PATH}"
    assert OUTPUT_PATH.exists(), f"Missing required output file: {OUTPUT_PATH}"
    assert OUTPUT_PATH.stat().st_size > 0, f"Output file is empty: {OUTPUT_PATH}"
    assert _load_output_text(), "Output file must not be blank"


def test_output_is_single_scholar_profile_url() -> None:
    text, parsed = _parse_output_url()
    assert "\n" not in text, "Output must contain exactly one URL"
    assert " " not in text, "Output must not contain spaces or extra commentary"
    assert parsed.scheme == "https", f"URL must use https, got {parsed.scheme!r}"
    assert parsed.netloc in EXPECTED_HOSTS, f"Unexpected host: {parsed.netloc!r}"
    assert parsed.path.rstrip("/") == "/citations", f"Unexpected path: {parsed.path!r}"
    query = parse_qs(parsed.query)
    user_values = query.get("user", [])
    assert len(user_values) == 1 and user_values[0], "URL must contain exactly one non-empty user parameter"


def test_url_matches_expected_corresponding_author() -> None:
    _, parsed = _parse_output_url()
    query = parse_qs(parsed.query)
    assert query.get("user") == [EXPECTED_USER_ID], (
        f"Expected user={EXPECTED_USER_ID!r}, got {query.get('user')!r}"
    )
    assert parsed.path.rstrip("/") == urlparse(EXPECTED_URL).path, "Unexpected Scholar profile path"


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
            "<test_output_exists|test_output_is_single_scholar_profile_url|test_url_matches_expected_corresponding_author>",
            flush=True,
        )
        raise SystemExit(2)
    raise SystemExit(_run_named_test(sys.argv[1]))
