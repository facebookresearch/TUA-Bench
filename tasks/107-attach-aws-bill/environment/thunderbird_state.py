#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from __future__ import annotations

import configparser
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


THUNDERBIRD_ROOT = Path.home() / ".thunderbird"
THUNDERBIRD_BIN = os.environ.get("TUA_THUNDERBIRD_BIN") or shutil.which("thunderbird") or "/usr/bin/thunderbird"
THUNDERBIRD_EXECUTABLES = {"crashhelper", "thunderbird", "thunderbird-bin"}


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


def thunderbird_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/tua-dbus-session")
    env.setdefault("XDG_RUNTIME_DIR", f"/tmp/xdg-runtime-{os.getuid()}")
    env.setdefault("GNOME_ACCESSIBILITY", "1")
    env.setdefault("GTK_MODULES", "gail:atk-bridge")
    env.setdefault("MOZ_ENABLE_WAYLAND", "0")
    return env


def thunderbird_pids() -> list[int]:
    # Inspect /proc/<pid>/exe so this script doesn't mistake itself for Thunderbird.
    result = subprocess.run(
        ["ps", "-eo", "pid="],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    pids: list[int] = []
    current_pid = os.getpid()
    for raw_pid in result.stdout.split():
        try:
            pid = int(raw_pid)
        except ValueError:
            continue
        if pid == current_pid:
            continue
        try:
            exe_name = os.path.basename(os.readlink(f"/proc/{pid}/exe"))
        except OSError:
            continue
        if exe_name in THUNDERBIRD_EXECUTABLES:
            pids.append(pid)
    return pids


def thunderbird_running() -> bool:
    return bool(thunderbird_pids())


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


def resolve_compose_body() -> str:
    if os.environ.get("THUNDERBIRD_COMPOSE_BODY"):
        return os.environ["THUNDERBIRD_COMPOSE_BODY"]

    body_path = os.environ.get("THUNDERBIRD_COMPOSE_BODY_FILE")
    if not body_path:
        return ""

    body_file = Path(body_path).expanduser()
    if not body_file.exists():
        return ""
    return body_file.read_text(encoding="utf-8").rstrip("\n")


def compose_argument() -> str:
    fields: list[str] = []
    mapping = {
        "from": os.environ.get("THUNDERBIRD_COMPOSE_FROM", ""),
        "to": os.environ.get("THUNDERBIRD_COMPOSE_TO", ""),
        "subject": os.environ.get("THUNDERBIRD_COMPOSE_SUBJECT", ""),
        "body": resolve_compose_body(),
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
        subprocess.Popen(command, stdout=log_file, stderr=log_file, env=thunderbird_env())

    wait_for_window()
    time.sleep(float(os.environ.get("THUNDERBIRD_STARTUP_DELAY", "5")))


def kill_thunderbird() -> None:
    for pid in thunderbird_pids():
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.time() + 15.0
    while time.time() < deadline:
        if not thunderbird_running():
            cleanup_profile_locks(resolve_profile_dir())
            return
        time.sleep(0.5)
    for pid in thunderbird_pids():
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if not thunderbird_running():
        cleanup_profile_locks(resolve_profile_dir())
        return
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
