# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import json
import tempfile
from pathlib import Path

WORKSPACE_PATH = Path('/app/project.code-workspace')
EXPECTED_FOLDERS = [{'path': 'project'}, {'path': 'data1'}, {'path': 'data2'}]
UNTOUCHED_WORKSPACE = {'folders': [{'path': 'project'}], 'settings': {}}
FAILURE_MESSAGE = '/app/project.code-workspace does not contain the expected workspace folders'


def normalize_folder_entries(folders: object, workspace_parent: Path) -> list[str] | None:
    if not isinstance(folders, list):
        return None

    normalized: list[str] = []
    for folder in folders:
        if not isinstance(folder, dict) or not isinstance(folder.get("path"), str):
            return None

        folder_path = Path(folder["path"]).expanduser()
        if not folder_path.is_absolute():
            folder_path = workspace_parent / folder_path
        normalized.append(str(folder_path.resolve()))

    return normalized


def check_workspace_folders(
    actual: str,
    expected_folders: list[dict[str, str]],
    **options,
) -> float:
    if not actual:
        return 0.0

    workspace_path = Path(actual)
    try:
        with workspace_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return 0.0

    workspace_parent = workspace_path.parent.resolve()
    actual_folders = normalize_folder_entries(data.get("folders"), workspace_parent)
    expected = normalize_folder_entries(expected_folders, workspace_parent)
    if actual_folders is None or expected is None:
        return 0.0

    if actual_folders != expected:
        return 0.0

    return 1.0


def evaluate_workspace(path: Path = WORKSPACE_PATH) -> float:
    return check_workspace_folders(str(path), EXPECTED_FOLDERS)


def run_sanity() -> dict[str, float]:
    with tempfile.TemporaryDirectory() as tmpdir:
        good_path = Path(tmpdir) / "good.json"
        absolute_path = Path(tmpdir) / "absolute.json"
        bad_path = Path(tmpdir) / "bad.json"
        good_path.write_text(
            json.dumps({"folders": EXPECTED_FOLDERS}, indent=2) + "\n",
            encoding="utf-8",
        )
        absolute_path.write_text(
            json.dumps(
                {
                    "folders": [
                        {"path": str(Path(tmpdir) / "project")},
                        {"path": str(Path(tmpdir) / "data1")},
                        {"path": str(Path(tmpdir) / "data2")},
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        bad_path.write_text(
            json.dumps(UNTOUCHED_WORKSPACE, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "relative_pass_score": check_workspace_folders(
                str(good_path),
                EXPECTED_FOLDERS,
            ),
            "absolute_pass_score": check_workspace_folders(
                str(absolute_path),
                EXPECTED_FOLDERS,
            ),
            "fail_score": check_workspace_folders(str(bad_path), EXPECTED_FOLDERS),
        }


def test_sanity():
    result = run_sanity()
    assert result["relative_pass_score"] == 1.0, result
    assert result["absolute_pass_score"] == 1.0, result
    assert result["fail_score"] == 0.0, result


def test_main():
    assert evaluate_workspace() == 1.0, FAILURE_MESSAGE
