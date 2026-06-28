#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

STATE_PATH = Path("/var/lib/tua-state/vscode_state.json")
SETTINGS_PATH = Path.home() / ".config" / "Code" / "User" / "settings.json"
KEYBINDINGS_PATH = Path.home() / ".config" / "Code" / "User" / "keybindings.json"
EXTENSIONS_DIR = Path.home() / ".vscode" / "extensions"
OPEN_PROJECT_MARKER = Path("/home/user/OpenProject.txt")


def default_state() -> dict:
    return {"installed_extensions": [], "current_target": None}


def ensure_layout() -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEYBINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXTENSIONS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.write_text("{}\n", encoding="utf-8")
    if not KEYBINDINGS_PATH.exists():
        KEYBINDINGS_PATH.write_text("[]\n", encoding="utf-8")


def load_state() -> dict:
    ensure_layout()
    if not STATE_PATH.exists():
        return default_state()
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return default_state()


def save_state(state: dict) -> None:
    ensure_layout()
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_extension_id(raw: str) -> str:
    candidate = Path(raw).expanduser()
    if candidate.is_file() and candidate.suffix.lower() == ".vsix":
        try:
            with zipfile.ZipFile(candidate) as archive:
                for name in archive.namelist():
                    if name.endswith("/package.json") or name == "extension/package.json":
                        manifest = json.loads(archive.read(name).decode("utf-8"))
                        publisher = manifest.get("publisher")
                        ext_name = manifest.get("name")
                        if publisher and ext_name:
                            return f"{publisher}.{ext_name}"
        except Exception:
            pass
        if candidate.name == "test.vsix":
            return "undefined_publisher.test"
    return raw


def install_extension(state: dict, raw: str) -> int:
    ext_id = parse_extension_id(raw)
    installed = state.setdefault("installed_extensions", [])
    if ext_id not in installed:
        installed.append(ext_id)
        (EXTENSIONS_DIR / ext_id.replace("/", "_")).mkdir(parents=True, exist_ok=True)
    save_state(state)
    return 0


def list_extensions(state: dict) -> int:
    for ext_id in sorted(state.get("installed_extensions", [])):
        print(ext_id)
    return 0


def set_current_target(state: dict, raw: str | None) -> int:
    path = None if raw is None else str(Path(raw).expanduser().resolve())
    if path is None:
        state["current_target"] = None
    else:
        target_path = Path(path)
        if target_path.suffix == ".code-workspace":
            target_type = "workspace"
        elif target_path.is_dir():
            target_type = "folder"
        else:
            target_type = "file"
        state["current_target"] = {"path": path, "type": target_type}
        if target_type == "folder":
            OPEN_PROJECT_MARKER.parent.mkdir(parents=True, exist_ok=True)
            OPEN_PROJECT_MARKER.write_text(f"{target_path.name}\n", encoding="utf-8")
    save_state(state)
    return 0


def main(argv: list[str]) -> int:
    ensure_layout()
    state = load_state()
    args = argv[1:]
    if not args:
        return set_current_target(state, None)
    if args == ["--list-extensions"]:
        return list_extensions(state)
    if args[:2] == ["--install-extension", args[1]] if len(args) >= 2 else False:
        return install_extension(state, args[1])
    filtered = []
    for arg in args:
        if arg in {"--reuse-window", "--new-window", "--wait"}:
            continue
        if arg.startswith("-"):
            continue
        filtered.append(arg)
    if filtered:
        return set_current_target(state, filtered[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
