#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import configparser
import os
import subprocess
import sys
import time
from pathlib import Path


THUNDERBIRD_ROOT = Path.home() / ".thunderbird"
THUNDERBIRD_BIN = "/usr/bin/thunderbird"


def resolve_profile_dir() -> Path:
    explicit = os.environ.get("TUA_THUNDERBIRD_PROFILE_DIR")
    if explicit:
        return Path(explicit).expanduser()

    ini_path = THUNDERBIRD_ROOT / "profiles.ini"
    config = configparser.ConfigParser(interpolation=None)
    config.read(ini_path, encoding="utf-8")

    def resolve_section_path(section_name: str) -> Path | None:
        if section_name not in config:
            return None
        section = config[section_name]
        raw_path = section.get("Path")
        if not raw_path:
            return None
        if section.get("IsRelative", "1") == "1":
            return THUNDERBIRD_ROOT / raw_path
        return Path(raw_path).expanduser()

    for section_name in config.sections():
        if not section_name.startswith("Install"):
            continue
        default_path = config[section_name].get("Default")
        if default_path:
            return THUNDERBIRD_ROOT / default_path

    for section_name in config.sections():
        if section_name.startswith("Profile") and config[section_name].get("Default") == "1":
            path = resolve_section_path(section_name)
            if path is not None:
                return path

    for section_name in config.sections():
        if section_name.startswith("Profile"):
            path = resolve_section_path(section_name)
            if path is not None:
                return path

    raise RuntimeError(f"Could not resolve Thunderbird profile from {ini_path}")


def cleanup_profile_locks(profile_dir: Path) -> None:
    for filename in ("lock", ".parentlock"):
        try:
            (profile_dir / filename).unlink()
        except FileNotFoundError:
            pass


def thunderbird_running() -> bool:
    result = subprocess.run(
        ["pgrep", "-f", "thunderbird"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def wait_for_window(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for command in (
            ["xdotool", "search", "--onlyvisible", "--class", "thunderbird"],
            ["xdotool", "search", "--onlyvisible", "--name", "Thunderbird"],
        ):
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return
        time.sleep(0.5)
    raise RuntimeError("Timed out waiting for a Thunderbird window")


def compose_argument() -> str:
    fields: list[str] = []
    mapping = {
        "from": os.environ.get("THUNDERBIRD_COMPOSE_FROM", ""),
        "to": os.environ.get("THUNDERBIRD_COMPOSE_TO", ""),
        "subject": os.environ.get("THUNDERBIRD_COMPOSE_SUBJECT", ""),
        "body": os.environ.get("THUNDERBIRD_COMPOSE_BODY", ""),
        "attachment": os.environ.get("THUNDERBIRD_COMPOSE_ATTACHMENT", ""),
    }
    for key, value in mapping.items():
        if not value:
            continue
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        fields.append(f"{key}='{escaped}'")
    return ",".join(fields)


def launch_task_state() -> None:
    if thunderbird_running():
        return

    profile_dir = resolve_profile_dir()
    cleanup_profile_locks(profile_dir)

    command = [THUNDERBIRD_BIN, "-profile", str(profile_dir)]
    if os.environ.get("THUNDERBIRD_START_MODE") == "compose":
        command.extend(["-compose", compose_argument()])
    elif os.environ.get("THUNDERBIRD_START_MODE") == "contenttab":
        command.extend(["-contentTab", os.environ["THUNDERBIRD_CONTENTTAB_URL"]])

    with open("/tmp/thunderbird.log", "a", encoding="utf-8") as log_file:
        subprocess.Popen(command, stdout=log_file, stderr=log_file)

    wait_for_window()
    time.sleep(float(os.environ.get("THUNDERBIRD_STARTUP_DELAY", "5")))


def kill_thunderbird() -> None:
    subprocess.run(["pkill", "-f", "thunderbird"], check=False)
    deadline = time.time() + 15.0
    while time.time() < deadline:
        if not thunderbird_running():
            cleanup_profile_locks(resolve_profile_dir())
            return
        time.sleep(0.5)
    raise RuntimeError("Timed out waiting for Thunderbird to exit")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: thunderbird_state.py <task|kill|profile>", file=sys.stderr)
        return 1

    command = argv[1]
    if command == "task":
        launch_task_state()
        return 0
    if command == "kill":
        kill_thunderbird()
        return 0
    if command == "profile":
        print(resolve_profile_dir())
        return 0

    print(f"Unknown command: {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
