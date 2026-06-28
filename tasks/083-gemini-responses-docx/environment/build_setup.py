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
import sys
import tarfile
import zipfile
from pathlib import Path


SPEC_PATH = Path(__file__).with_name("task_spec.json")
if not SPEC_PATH.exists():
    SPEC_PATH = Path("/usr/local/share/tua/task_spec.json")
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
CACHE_DIR = Path("/tmp") / SPEC["slug"] / "build"
ROOT_OVERRIDE = os.environ.get("TUA_SANITY_ROOT")


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


def rewrite_root_path_text(text: str) -> str:
    if not ROOT_OVERRIDE:
        return text
    home_root = str(localize_path("/home/user"))
    app_root = str(localize_path("/app"))
    text = text.replace(home_root, "__TUA_HOME_REAL__").replace(app_root, "__TUA_APP_REAL__")
    text = text.replace("/home/user/", "__TUA_HOME__/").replace("/home/user", "__TUA_HOME__")
    text = text.replace("/app/", "__TUA_APP__/").replace("/app", "__TUA_APP__")
    return (
        text.replace("__TUA_HOME__", home_root)
        .replace("__TUA_APP__", app_root)
        .replace("__TUA_HOME_REAL__", home_root)
        .replace("__TUA_APP_REAL__", app_root)
    )


def prepare_subprocess_command(command, shell: bool):
    if not ROOT_OVERRIDE:
        return command
    if shell:
        text = command if isinstance(command, str) else " ".join(str(part) for part in command)
        return rewrite_root_path_text(text)
    if isinstance(command, str):
        return rewrite_root_path_text(command)
    return [rewrite_root_path_text(str(part)) for part in command]


def subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    if ROOT_OVERRIDE:
        env["HOME"] = str(localize_path("/home/user"))
        python_bin = str(Path(sys.executable).resolve().parent)
        existing_path = env.get("PATH")
        env["PATH"] = f"{python_bin}:{existing_path}" if existing_path else python_bin
    return env


def subprocess_cwd() -> str | None:
    if not ROOT_OVERRIDE:
        return None
    return str(localize_path("/home/user"))


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


def run_command(command, shell: bool = False) -> None:
    subprocess.run(
        prepare_subprocess_command(command, shell),
        shell=shell,
        check=False,
        env=subprocess_env(),
        cwd=subprocess_cwd(),
    )


def should_skip_command(command) -> bool:
    text = command if isinstance(command, str) else " ".join(command)
    payload = text.strip()
    if (
        isinstance(command, list)
        and len(command) >= 3
        and str(command[0]) in {"/bin/bash", "bash", "/bin/sh", "sh"}
        and str(command[1]) == "-c"
    ):
        payload = str(command[2]).strip()
    first_token = Path(payload.split()[0]).name if payload else ""
    blocked_launches = {
        "gnome-terminal",
        "nautilus",
        "google-chrome",
        "chromium",
        "libreoffice",
        "soffice",
        "socat",
        "vlc",
        "thunderbird",
        "sudo",
        "apt",
        "apt-get",
    }
    return "pyautogui" in text or first_token in blocked_launches or "pip install" in payload


def ensure_profile_files() -> None:
    chrome_root = localize_path("/home/user/.config/google-chrome/Default")
    chrome_root.mkdir(parents=True, exist_ok=True)
    bookmarks = chrome_root / "Bookmarks"
    if not bookmarks.exists():
        bookmarks.write_text(
            json.dumps(
                {
                    "checksum": "",
                    "roots": {
                        "bookmark_bar": {
                            "children": [],
                            "date_added": "0",
                            "date_modified": "0",
                            "id": "1",
                            "name": "Bookmarks bar",
                            "type": "folder",
                        }
                    },
                    "version": 1,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    preferences = chrome_root / "Preferences"
    if not preferences.exists():
        preferences.write_text("{}\n", encoding="utf-8")
    code_user = localize_path("/home/user/.config/Code/User")
    code_user.mkdir(parents=True, exist_ok=True)
    settings = code_user / "settings.json"
    if not settings.exists():
        settings.write_text("{}\n", encoding="utf-8")
    keybindings = code_user / "keybindings.json"
    if not keybindings.exists():
        keybindings.write_text("[]\n", encoding="utf-8")


def main() -> int:
    home = localize_path("/home/user")
    for dirname in ["Desktop", "Documents", "Downloads", "Music", "Projects", "Code", "Drive"]:
        (home / dirname).mkdir(parents=True, exist_ok=True)
    ensure_profile_files()

    for item in SPEC.get("downloads", []):
        destination = localize_path(item["path"])
        ensure_parent(destination)
        if destination.exists():
            continue
        shutil.copyfile(fetch(item["url"], item["dest_name"]), destination)

    for action in SPEC.get("build_setup", []):
        action_type = action["type"]
        params = action.get("parameters", {})
        if action_type == "download":
            for item in params.get("files", []):
                destination = localize_path(item["path"])
                ensure_parent(destination)
                shutil.copyfile(fetch(item["url"], Path(item["path"]).name), destination)
            continue
        if action_type not in {"command", "execute"}:
            continue
        command = params["command"]
        if should_skip_command(command):
            continue
        run_command(command, shell=str(params.get("shell", False)).lower() == "true" or params.get("shell", False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
