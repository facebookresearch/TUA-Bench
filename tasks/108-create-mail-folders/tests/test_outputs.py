# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import configparser
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Dict, List

RULES = {'expect': ['\\bCOMPANY\\.msf\\b',
            '\\bCOMPANY/?(?!\\.msf)',
            '\\bUNIVERSITY\\.msf\\b',
            '\\bUNIVERSITY/?(?!\\.msf)']}
SANITY_LINES = ['COMPANY', 'COMPANY.msf', 'UNIVERSITY', 'UNIVERSITY.msf']

def resolve_profile_dir() -> Path:
    explicit = os.environ.get("TUA_THUNDERBIRD_PROFILE_DIR")
    if explicit:
        return Path(explicit).expanduser()

    root = Path.home() / ".thunderbird"
    ini_path = root / "profiles.ini"
    config = configparser.ConfigParser(interpolation=None)
    config.read(ini_path, encoding="utf-8")

    for section_name in config.sections():
        if not section_name.startswith("Install"):
            continue
        default_path = config[section_name].get("Default")
        if default_path:
            return root / default_path

    for section_name in config.sections():
        if section_name.startswith("Profile") and config[section_name].get("Default") == "1":
            if config[section_name].get("IsRelative", "1") == "1":
                return root / config[section_name]["Path"]
            return Path(config[section_name]["Path"]).expanduser()

    for section_name in config.sections():
        if section_name.startswith("Profile"):
            if config[section_name].get("IsRelative", "1") == "1":
                return root / config[section_name]["Path"]
            return Path(config[section_name]["Path"]).expanduser()

    raise RuntimeError(f"Could not resolve Thunderbird profile from {ini_path}")


RESULT_PATH = Path(os.environ.get("TUA_THUNDERBIRD_LIST_TARGET", str(resolve_profile_dir() / "Mail" / "Local Folders")))


def check_list(result: str, rules: Dict[str, List[str]]) -> float:
    if result is None:
        return 0.0

    expect_patterns = [re.compile(pattern) for pattern in rules.get("expect", [])]
    unexpect_patterns = [re.compile(pattern) for pattern in rules.get("unexpect", [])]

    expect_metrics = [False] * len(expect_patterns)
    unexpect_metric = True
    with open(result, encoding="utf-8") as handle:
        for line in handle:
            for index, pattern in enumerate(expect_patterns):
                expect_metrics[index] = expect_metrics[index] or (pattern.search(line) is not None)
            unexpect_metric = unexpect_metric and all(pattern.search(line) is None for pattern in unexpect_patterns)
    return float(all(expect_metrics) and unexpect_metric)


def snapshot_listing(path: Path, output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as handle:
        if not path.exists():
            return
        for child in sorted(path.rglob("*")):
            handle.write(str(child.relative_to(path)) + "\n")


def run_sanity():
    with tempfile.TemporaryDirectory() as tmpdir:
        good_listing = Path(tmpdir) / "good.txt"
        bad_listing = Path(tmpdir) / "bad.txt"
        good_listing.write_text("\n".join(SANITY_LINES) + "\n", encoding="utf-8")
        bad_listing.write_text("", encoding="utf-8")
        return {
            "fail_score": check_list(str(bad_listing), RULES),
            "pass_score": check_list(str(good_listing), RULES),
        }


def test_main():
    listing_path = Path("/tmp/thunderbird-listing.txt")
    snapshot_listing(RESULT_PATH, listing_path)
    assert check_list(str(listing_path), RULES) == 1.0, "Thunderbird output listing does not satisfy the exact OSWorld rule"


if __name__ == "__main__":
    import json as _json
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--sanity":
        print(_json.dumps(run_sanity(), sort_keys=True))
    else:
        listing_path = Path("/tmp/thunderbird-listing.txt")
        snapshot_listing(RESULT_PATH, listing_path)
        print(check_list(str(listing_path), RULES))
